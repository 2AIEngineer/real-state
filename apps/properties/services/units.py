"""Units (lots) of a building."""

from __future__ import annotations

from django.db import transaction
from django.db.models import QuerySet

from apps.accounts.services.authorization import AccessService
from apps.common.db import apply_changes, translate_integrity_errors
from apps.common.deletion import destroy
from apps.common.exceptions import NotFound, PermissionDenied
from apps.common.services.audit import AuditService
from apps.properties import errors, timezones
from apps.properties.audit import UnitAudit
from apps.properties.models import Building, Property, Unit
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
    def get_visible(*, actor, prop: Property | None, unit_id: int) -> Unit:
        """The unit, inside `prop` when given.

        `prop` is the selected property on every dashboard route; only the
        account console, which works across properties, passes `None`.
        """
        units = UnitService._base().filter(pk=unit_id)
        if prop is not None:
            units = units.filter(building__property=prop)
        unit = units.first()
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
            unit, prop=building.property, start_date=timezones.today(building.property), actor=actor
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
        """Permanent removal of a unit and everything recorded on it: ownership
        ledger, leases, short rentals, requests, orders, visitors, files."""
        if not UnitPolicy.can_delete(actor, unit):
            raise PermissionDenied("Only the property management can delete units.")
        AuditService.record(
            actor=actor,
            action=UnitAudit.DELETED,
            target=unit,
            property_id=unit.building.property_id,
        )
        destroy(unit)
