"""Units (lots) of a building."""

from __future__ import annotations

from django.db import transaction
from django.db.models import QuerySet
from django.utils import timezone

from apps.accounts.services.authorization import AccessService
from apps.common.db import apply_changes, deleting, translate_integrity_errors
from apps.common.exceptions import BusinessRuleViolation, NotFound, PermissionDenied
from apps.common.services.audit import AuditService
from apps.notifications.services import delete_notification_traces
from apps.properties import errors
from apps.properties.audit import UnitAudit
from apps.properties.models import Building, Unit, UnitOwnership
from apps.properties.policies import UnitPolicy
from apps.properties.services.ownership import open_promoter_default

UNIT_FIELDS = (
    "number",
    "label",
    "floor",
    "unit_type",
    "area_sqm",
    "rooms_count",
    "notes",
)
UNIT_CONSTRAINTS = {"unique_unit_number_per_building": errors.unit_number_taken}


class UnitService:
    @staticmethod
    def _base() -> QuerySet[Unit]:
        return Unit.objects.select_related("building__property__syndicat")

    @staticmethod
    def list_for_building(*, actor, building: Building) -> QuerySet[Unit]:
        """Staff with a role on the building see every unit; owners and tenants only theirs."""
        qs = UnitService._base().filter(building=building)
        if UnitPolicy.can_see_all_units(actor, building):
            return qs
        return qs.filter(pk__in=AccessService.owned_or_rented_unit_ids(actor))

    @staticmethod
    def list_mine(*, actor) -> QuerySet[Unit]:
        return UnitService._base().filter(pk__in=AccessService.owned_or_rented_unit_ids(actor))

    @staticmethod
    def get_visible(*, actor, unit_id: int) -> Unit:
        unit = UnitService._base().filter(pk=unit_id).first()
        if unit is None or not UnitPolicy.can_view(actor, unit):
            raise NotFound("Unit not found.")
        return unit

    @staticmethod
    def get(*, unit_id: int) -> Unit:
        unit = UnitService._base().filter(pk=unit_id).first()
        if unit is None:
            raise NotFound("Unit not found.")
        return unit

    @staticmethod
    @transaction.atomic
    def create(*, actor, building: Building, data: dict) -> Unit:
        if not UnitPolicy.can_create(actor, building):
            raise PermissionDenied("Only the property management can create units.")
        unit = Unit(building=building)
        apply_changes(unit, data, UNIT_FIELDS)
        with translate_integrity_errors(UNIT_CONSTRAINTS):
            unit.save()
        # A unit always has an owner: the promoter holds it until it is sold.
        open_promoter_default(
            unit, prop=building.property, start_date=timezone.localdate(), actor=actor
        )
        AuditService.record(
            actor=actor, action=UnitAudit.CREATED, target=unit, property_id=building.property_id
        )
        return unit

    @staticmethod
    @transaction.atomic
    def update(*, actor, unit: Unit, changes: dict) -> Unit:
        if not UnitPolicy.can_update(actor, unit):
            raise PermissionDenied("Only the property management can edit units.")
        fields = apply_changes(unit, changes, UNIT_FIELDS)
        if fields:
            with translate_integrity_errors(UNIT_CONSTRAINTS):
                unit.save(update_fields=[*fields, "updated_at"])
            AuditService.record(
                actor=actor,
                action=UnitAudit.UPDATED,
                target=unit,
                property_id=unit.building.property_id,
                metadata={"fields": fields},
            )
        return unit

    @staticmethod
    @transaction.atomic
    def delete(*, actor, unit: Unit) -> None:
        """Removable while the unit was never lived in nor sold.

        The promoter's default ownership is removed with it; any other
        ownership means the ledger must be kept, and deletion is refused.
        """
        from apps.leasing.models import Lease  # leasing depends on properties

        if not UnitPolicy.can_delete(actor, unit):
            raise PermissionDenied("Only the property management can delete units.")
        ownerships = UnitOwnership.objects.filter(unit=unit)
        if ownerships.exclude(is_promoter_default=True).exists():
            raise BusinessRuleViolation(
                "This unit has an ownership history: it cannot be deleted.",
                code="unit_has_ownership_history",
            )
        if Lease.objects.filter(unit=unit).exists():
            raise BusinessRuleViolation(
                "This unit has leases: it cannot be deleted.", code="unit_has_leases"
            )
        AuditService.record(
            actor=actor,
            action=UnitAudit.DELETED,
            target=unit,
            property_id=unit.building.property_id,
        )
        with deleting("unit"):
            ownerships.delete()
            delete_notification_traces(unit)
            unit.delete()
