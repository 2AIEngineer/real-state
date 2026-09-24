"""Security and cleaning agents, and the buildings they work in."""

from __future__ import annotations

from apps.accounts.enums import StructuralRole
from apps.accounts.models import ROLES_ASSIGNED_TO_BUILDINGS, UserBuilding
from apps.accounts.policies import can_assign_building
from apps.accounts.services.assignments.base import AssignmentService
from apps.accounts.services.authorization import AccessService
from apps.common.exceptions import BusinessRuleViolation
from apps.properties.models import Building


class BuildingAssignmentService(AssignmentService):
    model = UserBuilding
    place_model = Building
    place_field = "building"
    places_label = "buildings"
    ids_field = "building_ids"
    roles = ROLES_ASSIGNED_TO_BUILDINGS
    unique_constraint = "unique_active_user_building"

    @staticmethod
    def can_assign_place(actor, building) -> bool:
        return can_assign_building(actor, building)

    @staticmethod
    def property_id_of(building) -> int:
        return building.property_id

    @classmethod
    def restrict_to_managed(cls, rows, actor):
        """Someone else only sees the buildings of the properties they manage."""
        return rows.filter(building__property_id__in=AccessService.managed_property_ids(actor))

    @classmethod
    def validate_places(cls, user, buildings: list) -> None:
        if user.role != StructuralRole.SECURITY:
            return
        # A security agent guards buildings of one property only.
        property_ids = {building.property_id for building in buildings}
        property_ids |= set(
            UserBuilding.objects.filter(user=user, is_active=True).values_list(
                "building__property_id", flat=True
            )
        )
        if len(property_ids) > 1:
            raise BusinessRuleViolation(
                "All buildings guarded by one security account must belong to the same property.",
                code="security_single_property",
            )

    @classmethod
    def assign(cls, *, actor, user, building_ids) -> list[UserBuilding]:
        return cls._assign(actor=actor, user=user, ids=building_ids)
