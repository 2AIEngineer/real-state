"""Assigning to the place the author has selected.

The place is never chosen freely by the client: it is the syndicat and the
property the author has selected, which the request carries in `X-Syndicat-Id`
and `X-Property-Id`. The three `assign_to_*` functions read the place from
there, one per table; `assign_according_to_role` picks between them for the two
callers that learn the role at run time (creating an account, changing a role).
Admins, standard accounts and providers are never assigned.
"""

from __future__ import annotations

from apps.accounts.enums import StructuralRole
from apps.accounts.models import (
    ROLES_ASSIGNED_TO_BUILDINGS,
    ROLES_ASSIGNED_TO_PROPERTIES,
    ROLES_ASSIGNED_TO_SYNDICATS,
    UserBuilding,
    UserProperty,
    UserSyndicat,
)
from apps.accounts.services.assignments.buildings import BuildingAssignmentService
from apps.accounts.services.assignments.properties import PropertyAssignmentService
from apps.accounts.services.assignments.syndicats import SyndicatAssignmentService
from apps.common.exceptions import BusinessRuleViolation, InvalidInput
from apps.properties.models import Building, Property


def is_assignable_role(role: str) -> bool:
    """Whether a role is exercised somewhere, and therefore needs an assignment."""
    return role in (
        *ROLES_ASSIGNED_TO_SYNDICATS,
        *ROLES_ASSIGNED_TO_PROPERTIES,
        *ROLES_ASSIGNED_TO_BUILDINGS,
    )


def assign_to_selected_syndicat(*, actor, user, syndicat_id: int) -> list[UserSyndicat]:
    """Assign a syndic to the selected syndicat."""
    return SyndicatAssignmentService.assign(
        actor=actor, user=user, syndicat_ids=(syndicat_id,)
    )


def assign_to_selected_property(
    *, actor, user, syndicat_id: int, property_id: int | None
) -> list[UserProperty]:
    """Assign a manager or a maintenance agent to the selected property."""
    prop = _selected_property(syndicat_id, property_id)
    return PropertyAssignmentService.assign(
        actor=actor, user=user, property_ids=(prop.pk,)
    )


def assign_to_buildings_of_selected_property(
    *, actor, user, syndicat_id: int, property_id: int | None, building_ids
) -> list[UserBuilding]:
    """Assign a security or cleaning agent to buildings, all inside the selected property."""
    prop = _selected_property(syndicat_id, property_id)
    return BuildingAssignmentService.assign(
        actor=actor,
        user=user,
        building_ids=_buildings_of(prop, building_ids, role=user.role),
    )


def assign_according_to_role(
    *, actor, user, syndicat_id: int, property_id: int | None = None, building_ids=()
) -> list:
    """Assign `user` where their role is exercised, reading the table from the role.

    Every endpoint that grants an assignment names its table instead, by calling
    one of the three functions above.
    """
    if user.role == StructuralRole.SYNDIC:
        return assign_to_selected_syndicat(
            actor=actor, user=user, syndicat_id=syndicat_id
        )
    if user.role in (StructuralRole.MANAGER, StructuralRole.MAINTENANCE):
        return assign_to_selected_property(
            actor=actor, user=user, syndicat_id=syndicat_id, property_id=property_id
        )
    if user.role in (StructuralRole.SECURITY, StructuralRole.CLEANING):
        return assign_to_buildings_of_selected_property(
            actor=actor,
            user=user,
            syndicat_id=syndicat_id,
            property_id=property_id,
            building_ids=building_ids,
        )
    raise BusinessRuleViolation(
        f"A {user.role} account takes no assignment.", code="role_takes_no_assignment"
    )


def _selected_property(syndicat_id: int, property_id: int | None) -> Property:
    """The selected property, which must be one of the selected syndicat."""
    if property_id is None:
        raise InvalidInput(
            "Select a property first: assigning this role requires the X-Property-Id header.",
            field="X-Property-Id",
            code="selection_required",
        )
    prop = Property.objects.filter(pk=property_id, syndicat_id=syndicat_id).first()
    if prop is None:
        raise InvalidInput(
            "The selected property does not belong to the selected syndicat.",
            field="X-Property-Id",
            code="property_outside_syndicat",
        )
    return prop


def _buildings_of(prop: Property, building_ids, *, role: str) -> tuple[int, ...]:
    """The buildings given for a security or cleaning agent, all inside the selected property."""
    building_ids = tuple(dict.fromkeys(building_ids))
    if not building_ids:
        raise InvalidInput(
            f"A {role} account must be assigned to at least one building.",
            field="building_ids",
            code="assignment_required",
        )
    inside = set(
        Building.objects.filter(pk__in=building_ids, property=prop).values_list(
            "id", flat=True
        )
    )
    outside = [i for i in building_ids if i not in inside]
    if outside:
        raise InvalidInput(
            f"Building(s) {outside} are not in the selected property.",
            field="building_ids",
            code="building_outside_property",
        )
    return building_ids
