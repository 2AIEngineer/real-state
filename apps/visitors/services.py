"""Visitor log kept by management and on-site security.

(entry) ──▶ ARRIVED ──mark_left──▶ LEFT
(entry) ──▶ DENIED
"""

from __future__ import annotations

import datetime as dt

from django.db import transaction
from django.db.models import QuerySet
from django.utils import timezone

from apps.common.attachments.rules import EntityType
from apps.common.attachments.service import AttachmentService
from apps.common.db import apply_changes
from apps.common.deletion import destroy
from apps.common.exceptions import (
    InvalidInput,
    InvalidTransition,
    NotFound,
    PermissionDenied,
)
from apps.common.services.audit import AuditService
from apps.properties.enums import Feature
from apps.properties.models import Property, Unit
from apps.properties.services import FeatureGate
from apps.visitors import notices
from apps.visitors.audit import VisitorAudit
from apps.visitors.models import Visitor, VisitStatus
from apps.visitors.policies import VisitorPolicy

DETAIL_FIELDS = ("phone", "visit_reason", "vehicle_plate", "notes")


class VisitorService:
    @staticmethod
    def list_visible(
        *,
        actor,
        property_id: int,
        unit_id: int | None = None,
        status: str | None = None,
        since: dt.datetime | None = None,
    ) -> QuerySet[Visitor]:
        qs = Visitor.objects.filter(VisitorPolicy.visible_filter(actor)).select_related(
            "unit__building", "registered_by"
        )
        qs = qs.filter(property_id=property_id)
        if unit_id:
            qs = qs.filter(unit_id=unit_id)
        if status:
            qs = qs.filter(status=status)
        if since:
            qs = qs.filter(created_at__gte=since)
        return qs

    @staticmethod
    def get_visible(*, actor, prop: Property, visitor_id: int) -> Visitor:
        visitor = (
            Visitor.objects.select_related("unit__building__property", "registered_by")
            .filter(pk=visitor_id, property=prop)
            .first()
        )
        if visitor is None or not VisitorPolicy.can_view(actor, visitor):
            raise NotFound("Visitor not found.")
        return visitor

    @staticmethod
    @transaction.atomic
    def register(
        *,
        actor,
        unit: Unit,
        first_name: str,
        last_name: str,
        admitted: bool = True,
        denial_reason: str = "",
        details: dict | None = None,
        id_card=None,
    ) -> Visitor:
        prop = unit.building.property
        FeatureGate.require(prop, Feature.VISITOR)
        if not VisitorPolicy.can_register(actor, unit):
            raise PermissionDenied("Only management and security can log visitors for this unit.")
        if not admitted and not denial_reason.strip():
            raise InvalidInput("A reason is required when entry is denied.", field="denial_reason")
        now = timezone.now()
        visitor = Visitor(
            unit=unit,
            property=prop,
            first_name=first_name.strip(),
            last_name=last_name.strip(),
            status=VisitStatus.ARRIVED if admitted else VisitStatus.DENIED,
            arrived_at=now if admitted else None,
            denial_reason="" if admitted else denial_reason,
            registered_by=actor,
        )
        apply_changes(visitor, details or {}, DETAIL_FIELDS)
        visitor.save()
        if id_card is not None:
            AttachmentService.attach(
                entity_type=EntityType.VISITOR_ID_CARD,
                entity_id=visitor.pk,
                files=[id_card],
                uploaded_by=actor,
                field="id_card",
            )
        AuditService.record(
            actor=actor,
            action=VisitorAudit(f"visitor.{visitor.status.lower()}"),
            target=visitor,
            property_id=prop.pk,
        )
        notices.visitor_logged(visitor, actor=actor)
        return visitor

    @staticmethod
    @transaction.atomic
    def mark_left(*, actor, visitor: Visitor, left_at: dt.datetime | None = None) -> Visitor:
        if not VisitorPolicy.can_update(actor, visitor):
            raise PermissionDenied()
        visitor = Visitor.objects.select_for_update(of=("self",)).get(pk=visitor.pk)
        if visitor.status != VisitStatus.ARRIVED:
            raise InvalidTransition("Only visitors on site can be checked out.")
        left_at = left_at or timezone.now()
        if left_at < visitor.arrived_at:
            raise InvalidInput("Departure cannot precede arrival.", field="left_at")
        if left_at > timezone.now() + dt.timedelta(minutes=5):
            raise InvalidInput("Departure cannot be in the future.", field="left_at")
        visitor.status = VisitStatus.LEFT
        visitor.left_at = left_at
        visitor.checked_out_by = actor
        visitor.save(update_fields=["status", "left_at", "checked_out_by", "updated_at"])
        AuditService.record(
            actor=actor,
            action=VisitorAudit.LEFT,
            target=visitor,
            property_id=visitor.property_id,
        )
        return visitor

    @staticmethod
    @transaction.atomic
    def update_details(*, actor, visitor: Visitor, changes: dict) -> Visitor:
        if not VisitorPolicy.can_update(actor, visitor):
            raise PermissionDenied()
        fields = apply_changes(visitor, changes, DETAIL_FIELDS)
        if fields:
            visitor.save(update_fields=[*fields, "updated_at"])
            AuditService.record(
                actor=actor,
                action=VisitorAudit.UPDATED,
                target=visitor,
                property_id=visitor.property_id,
            )
        return visitor

    @staticmethod
    @transaction.atomic
    def delete(*, actor, visitor: Visitor) -> None:
        """Correction of a wrongly logged entry: management only, and audited."""
        if not VisitorPolicy.can_delete(actor, visitor):
            raise PermissionDenied("Only management can delete a visitor entry.")
        AuditService.record(
            actor=actor,
            action=VisitorAudit.DELETED,
            target=visitor,
            property_id=visitor.property_id,
            metadata={
                "name": f"{visitor.first_name} {visitor.last_name}",
                "status": visitor.status,
            },
        )
        destroy(visitor)

    @staticmethod
    @transaction.atomic
    def set_id_card(*, actor, visitor: Visitor, upload) -> None:
        if not VisitorPolicy.can_update(actor, visitor):
            raise PermissionDenied()
        AttachmentService.attach_one(
            entity_type=EntityType.VISITOR_ID_CARD,
            entity_id=visitor.pk,
            upload=upload,
            uploaded_by=actor,
        )
