"""Buildings of a property."""

from __future__ import annotations

from django.db import transaction
from django.db.models import Count, QuerySet

from apps.common.db import apply_changes, deleting, translate_integrity_errors
from apps.common.exceptions import NotFound, PermissionDenied
from apps.common.services.audit import AuditService
from apps.notifications.services import delete_notification_traces
from apps.properties import errors
from apps.properties.audit import BuildingAudit
from apps.properties.models import Building, Property
from apps.properties.policies import BuildingPolicy

BUILDING_FIELDS = ("name", "address", "floors_count", "description")
BUILDING_CONSTRAINTS = {"building_name_per_property": errors.building_name_taken}


class BuildingService:
    @staticmethod
    def list_for_property(*, actor, prop: Property) -> QuerySet[Building]:
        if not BuildingPolicy.can_list(actor, prop):
            raise errors.no_link_with_property()
        # An aggregate drops `Meta.ordering`: say it again, or pages are not stable.
        return (
            Building.objects.filter(property=prop)
            .annotate(units_count=Count("units"))
            .order_by(*Building._meta.ordering)
        )

    @staticmethod
    def get_visible(*, actor, prop: Property, building_id: int) -> Building:
        building = (
            Building.objects.select_related("property__syndicat")
            .filter(pk=building_id, property=prop)
            .first()
        )
        if building is None or not BuildingPolicy.can_view(actor, building):
            raise NotFound("Building not found.")
        return building

    @staticmethod
    @transaction.atomic
    def create(*, actor, prop: Property, data: dict) -> Building:
        if not BuildingPolicy.can_create(actor, prop):
            raise PermissionDenied("Only the property management can create buildings.")
        building = Building(property=prop)
        apply_changes(building, data, BUILDING_FIELDS)
        with translate_integrity_errors(BUILDING_CONSTRAINTS):
            building.save()
        AuditService.record(
            actor=actor, action=BuildingAudit.CREATED, target=building, property_id=prop.pk
        )
        return building

    @staticmethod
    @transaction.atomic
    def update(*, actor, building: Building, changes: dict) -> Building:
        if not BuildingPolicy.can_update(actor, building):
            raise PermissionDenied("Only the property management can edit buildings.")
        fields = apply_changes(building, changes, BUILDING_FIELDS)
        if fields:
            with translate_integrity_errors(BUILDING_CONSTRAINTS):
                building.save(update_fields=[*fields, "updated_at"])
            AuditService.record(
                actor=actor,
                action=BuildingAudit.UPDATED,
                target=building,
                property_id=building.property_id,
            )
        return building

    @staticmethod
    @transaction.atomic
    def delete(*, actor, building: Building) -> None:
        """Removable while it holds no unit and nothing points at it."""
        if not BuildingPolicy.can_delete(actor, building):
            raise PermissionDenied("Only the property management can delete buildings.")
        AuditService.record(
            actor=actor,
            action=BuildingAudit.DELETED,
            target=building,
            property_id=building.property_id,
        )
        with deleting("building"):
            delete_notification_traces(building)
            building.delete()
