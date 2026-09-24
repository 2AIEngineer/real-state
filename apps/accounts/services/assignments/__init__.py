"""Where a role is exercised: one service per assignment table.

- `SyndicatAssignmentService`: syndics, assigned to one or more syndicats.
- `PropertyAssignmentService`: managers and maintenance agents, assigned to
  properties of any number of syndicats.
- `BuildingAssignmentService`: security and cleaning agents, assigned to
  buildings. All the buildings of a security agent belong to one property.

A user is assigned to a syndicat, to a property or to buildings — never "an
account to everything at once": each table has its own service, and a caller
names the one it means.

Who may grant or revoke an assignment is decided by the `can_assign_*`
functions of `apps.accounts.policies`: one for the account being assigned, one
per place.
"""

from apps.accounts.services.assignments.buildings import BuildingAssignmentService
from apps.accounts.services.assignments.properties import PropertyAssignmentService
from apps.accounts.services.assignments.selected import (
    assign_according_to_role,
    assign_to_buildings_of_selected_property,
    assign_to_selected_property,
    assign_to_selected_syndicat,
    is_assignable_role,
)
from apps.accounts.services.assignments.syndicats import SyndicatAssignmentService

__all__ = [
    "BuildingAssignmentService",
    "PropertyAssignmentService",
    "SyndicatAssignmentService",
    "assign_according_to_role",
    "assign_to_buildings_of_selected_property",
    "assign_to_selected_property",
    "assign_to_selected_syndicat",
    "is_assignable_role",
]
