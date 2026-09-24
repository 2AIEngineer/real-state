"""A service request: submitting it, its files, closing, cancelling, deleting.

Lifecycle (the rounds are in `rounds.py`)
    OPEN ──assign──▶ IN_PROGRESS ──(all resolvers resolved)──▶ RESOLVED
    RESOLVED ──requester DONE / management close──▶ CLOSED
    RESOLVED ──requester NOT_DONE──▶ OPEN (round + 1, awaiting reassignment)
    OPEN | IN_PROGRESS ──cancel──▶ CANCELLED
"""

from __future__ import annotations

from django.db import transaction
from django.db.models import QuerySet
from django.utils import timezone

from apps.common.deletion import destroy
from apps.common.exceptions import InvalidInput, InvalidTransition, NotFound, PermissionDenied
from apps.common.files.rules import EntityType
from apps.common.files.service import AttachmentService
from apps.common.services.audit import AuditService
from apps.properties.enums import Feature
from apps.properties.models import Property, Unit
from apps.properties.services import FeatureGate
from apps.service_requests import notices
from apps.service_requests.audit import ServiceRequestAudit
from apps.service_requests.models import (
    ServiceRequest,
    ServiceRequestPriority,
    ServiceRequestStatus,
)
from apps.service_requests.policies import ServiceRequestPolicy
from apps.service_requests.services._state import OPEN_STATES, current_resolvers, lock


class ServiceRequestService:
    @staticmethod
    def list_visible(
        *, actor, property_id: int, status: str | None = None, mine: bool = False
    ) -> QuerySet[ServiceRequest]:
        qs = (
            ServiceRequest.objects.filter(ServiceRequestPolicy.visible_filter(actor))
            .distinct()
            .select_related("property", "unit", "requester")
        )
        if mine:
            qs = qs.filter(requester=actor)
        qs = qs.filter(property_id=property_id)
        if status:
            qs = qs.filter(status=status)
        return qs

    @staticmethod
    def get_visible(*, actor, prop: Property, request_id: int) -> ServiceRequest:
        sr = (
            ServiceRequest.objects.select_related("property", "unit__building", "requester")
            .filter(pk=request_id, property=prop)
            .first()
        )
        if sr is None or not ServiceRequestPolicy.can_view(actor, sr):
            raise NotFound("Service request not found.")
        return sr

    # --------------------------------------------------------------- creation
    @staticmethod
    @transaction.atomic
    def submit(
        *,
        actor,
        prop: Property,
        title: str,
        description: str,
        category: str,
        priority: str = ServiceRequestPriority.MEDIUM,
        unit: Unit | None = None,
        files=(),
    ) -> ServiceRequest:
        FeatureGate.require(prop, Feature.SERVICE_REQUEST)
        if unit is not None:
            if unit.building.property_id != prop.pk:
                raise InvalidInput("The unit belongs to another property.", field="unit_id")
        if not ServiceRequestPolicy.can_submit(actor, prop, unit):
            raise PermissionDenied("You can only submit requests for your own units or property.")
        sr = ServiceRequest.objects.create(
            property=prop,
            unit=unit,
            requester=actor,
            title=title.strip(),
            description=description,
            category=category,
            priority=priority,
        )
        AttachmentService.attach(
            entity_type=EntityType.SERVICE_REQUEST,
            entity_id=sr.pk,
            files=list(files),
            uploaded_by=actor,
        )
        AuditService.record(
            actor=actor, action=ServiceRequestAudit.SUBMITTED, target=sr, property_id=prop.pk
        )
        notices.submitted(sr)
        return sr

    @staticmethod
    @transaction.atomic
    def add_files(*, actor, sr: ServiceRequest, files) -> list:
        if not ServiceRequestPolicy.can_add_files(actor, sr):
            raise NotFound("Service request not found.")
        if sr.status not in OPEN_STATES:
            raise InvalidTransition("Files can only be added while the request is open.")
        return AttachmentService.attach(
            entity_type=EntityType.SERVICE_REQUEST,
            entity_id=sr.pk,
            files=list(files),
            uploaded_by=actor,
        )

    @staticmethod
    @transaction.atomic
    def remove_file(*, actor, sr: ServiceRequest, attachment_id: int) -> None:
        """The uploader takes back a file, management may remove any."""
        if not ServiceRequestPolicy.can_view(actor, sr):
            raise NotFound("Service request not found.")
        attachment = AttachmentService.get(
            entity_type=EntityType.SERVICE_REQUEST, entity_id=sr.pk, attachment_id=attachment_id
        )
        if not ServiceRequestPolicy.can_remove_file(actor, sr, attachment.uploaded_by_id):
            raise PermissionDenied(
                "Only the uploader or the property management can remove this file."
            )
        AttachmentService.delete(attachment=attachment)

    # -------------------------------------------------------------- lifecycle
    @staticmethod
    @transaction.atomic
    def close(*, actor, sr: ServiceRequest) -> ServiceRequest:
        """Management closes a resolved request (e.g. requester never answered)."""
        if not ServiceRequestPolicy.can_close(actor, sr):
            raise PermissionDenied("Only the property management can close service requests.")
        sr = lock(sr)
        if sr.status != ServiceRequestStatus.RESOLVED:
            raise InvalidTransition("Only resolved requests can be closed.")
        sr.status = ServiceRequestStatus.CLOSED
        sr.closed_at = timezone.now()
        sr.closed_by = actor
        sr.save(update_fields=["status", "closed_at", "closed_by", "updated_at"])
        AuditService.record(
            actor=actor, action=ServiceRequestAudit.CLOSED, target=sr, property_id=sr.property_id
        )
        notices.closed_by_management(sr, actor=actor)
        return sr

    @staticmethod
    @transaction.atomic
    def cancel(*, actor, sr: ServiceRequest, reason: str = "") -> ServiceRequest:
        sr = lock(sr)
        if not ServiceRequestPolicy.can_cancel(actor, sr):
            raise PermissionDenied(
                "Only the requester or the property management can cancel this request."
            )
        if sr.status not in OPEN_STATES:
            raise InvalidTransition("Only open requests can be cancelled.")
        sr.status = ServiceRequestStatus.CANCELLED
        sr.cancelled_at = timezone.now()
        sr.cancellation_reason = reason
        sr.save(update_fields=["status", "cancelled_at", "cancellation_reason", "updated_at"])
        AuditService.record(
            actor=actor, action=ServiceRequestAudit.CANCELLED, target=sr, property_id=sr.property_id
        )
        notices.cancelled(sr, actor=actor, resolvers=current_resolvers(sr), reason=reason)
        return sr

    @staticmethod
    @transaction.atomic
    def delete(*, actor, sr: ServiceRequest) -> None:
        """Permanent removal of a request, its rounds and its conversation."""
        if not ServiceRequestPolicy.can_delete(actor, sr):
            raise PermissionDenied("Only the property management can delete service requests.")
        AuditService.record(
            actor=actor,
            action=ServiceRequestAudit.DELETED,
            target=sr,
            property_id=sr.property_id,
            metadata={"status": sr.status, "title": sr.title},
        )
        destroy(sr)
