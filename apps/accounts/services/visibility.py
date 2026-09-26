"""Which role-addressed records a user may read.

Announcements, events, library documents and surveys all have the same shape:

* they belong to a property;
* they name the roles they are addressed to (`target_roles`);
* announcements and events may be narrowed to a single building of that
  property, library documents and surveys never are.

Two reasons, and two only, let a user read one of them, so the filter built
here is their OR:

1. **Management reads everything** published in the properties it manages,
   addressed to it or not.
2. **Everybody else reads what is addressed to a role they hold, where they
   hold it.** A role is exercised somewhere precise, and that is what
   `_places_of` lists: a maintenance agent covers whole properties, a security
   or cleaning agent their buildings, an owner or a tenant the buildings
   holding their unit.

The only difference between the two public functions is whether the records
being filtered carry a `building` column, which decides how "somewhere
precise" is written as a query (see `_Places.records`).
"""

from __future__ import annotations

from collections.abc import Iterator
from dataclasses import dataclass

from django.db.models import Q, QuerySet

from apps.accounts.enums import PropertyRole, StructuralRole
from apps.accounts.models import ROLES_ASSIGNED_TO_BUILDINGS, UserBuilding
from apps.accounts.services.authorization import (
    AccessService,
    active_lease_memberships,
    active_ownerships,
)


def readable_property_records(user) -> Q:
    """Records belonging to a property as a whole: library documents, surveys."""
    return _readable(user, records_may_name_a_building=False)


def readable_property_or_building_records(user) -> Q:
    """Records that may be narrowed to one building: announcements, events."""
    return _readable(user, records_may_name_a_building=True)


def _readable(user, *, records_may_name_a_building: bool) -> Q:
    readable = Q(property_id__in=AccessService.managed_property_ids(user))
    for role, places in _places_of(user):
        readable |= Q(target_roles__contains=[role]) & places.records(
            may_name_a_building=records_may_name_a_building
        )
    return readable


@dataclass(frozen=True)
class _Places:
    """Where one role of the reader is exercised, as id sub-queries.

    `building_ids` is `None` when the role covers the properties whole: the
    reader is then reached by every record of those properties, including the
    ones narrowed to one of their buildings.
    """

    property_ids: QuerySet
    building_ids: QuerySet | None = None

    def records(self, *, may_name_a_building: bool) -> Q:
        """The records these places hold."""
        if self.building_ids is None or not may_name_a_building:
            return Q(property_id__in=self.property_ids)
        return Q(property_id__in=self.property_ids, building__isnull=True) | Q(
            building_id__in=self.building_ids
        )


def _places_of(user) -> Iterator[tuple[str, _Places]]:
    """Each role the reader holds, with the places where they hold it.

    The staff role comes from the account (`User.role`) and is exercised where
    the account is assigned; owner and tenant are held unit by unit, so they
    are read from the ownerships and the leases and never from the account.
    """
    if user.role == StructuralRole.MAINTENANCE:
        yield user.role, _Places(AccessService.assigned_property_ids(user))

    if user.role in ROLES_ASSIGNED_TO_BUILDINGS:  # security, cleaning
        buildings = UserBuilding.objects.filter(user=user, is_active=True)
        yield (
            user.role,
            _Places(
                buildings.values("building__property_id"),
                buildings.values("building_id"),
            ),
        )

    owned = active_ownerships().filter(owner=user)
    yield (
        PropertyRole.OWNER,
        _Places(
            owned.values("unit__building__property_id"),
            owned.values("unit__building_id"),
        ),
    )

    rented = active_lease_memberships().filter(user=user)
    yield (
        PropertyRole.TENANT,
        _Places(
            rented.values("lease__unit__building__property_id"),
            rented.values("lease__unit__building_id"),
        ),
    )
