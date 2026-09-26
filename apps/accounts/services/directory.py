"""Finding people: who works in a property, who owns or rents a unit.

The reverse of `AccessService`: instead of "is this user the manager of this
property?", it answers "who are the managers of this property?". Used to
address notifications and to freeze the recipients of a broadcast. Technical
accounts and deactivated accounts are never returned.
"""

from __future__ import annotations

from collections import defaultdict
from collections.abc import Iterable

from django.contrib.auth import get_user_model
from django.db.models import QuerySet

from apps.accounts.enums import PropertyRole, StructuralRole
from apps.accounts.models import UserBuilding, UserProperty, UserSyndicat
from apps.leasing.models import LeaseMember, LeaseStatus
from apps.properties.models import (
    Building,
    OwnershipStatus,
    Property,
    Syndicat,
    Unit,
    UnitOwnership,
)

User = get_user_model()


def _reachable_users() -> QuerySet:
    """Humans who can receive something: active, not technical accounts."""
    return User.objects.filter(is_active=True, is_technical_account=False)


def _agents_of(role: str, prop: Property, building: Building | None) -> QuerySet:
    """The agents of `role` assigned to that building, or to any building of the property."""
    assignments = UserBuilding.objects.filter(is_active=True)
    assignments = (
        assignments.filter(building=building)
        if building
        else assignments.filter(building__property=prop)
    )
    return _reachable_users().filter(role=role, pk__in=assignments.values("user_id"))


class UserDirectory:
    # ------------------------------------------------------------- staff
    @staticmethod
    def platform_admins() -> QuerySet:
        return _reachable_users().filter(role=StructuralRole.ADMIN)

    @staticmethod
    def syndics_of(syndicat: Syndicat) -> QuerySet:
        assigned = UserSyndicat.objects.filter(
            is_active=True, syndicat=syndicat
        ).values("user_id")
        return _reachable_users().filter(role=StructuralRole.SYNDIC, pk__in=assigned)

    @staticmethod
    def managers_of(prop: Property) -> QuerySet:
        assigned = UserProperty.objects.filter(is_active=True, property=prop).values(
            "user_id"
        )
        return _reachable_users().filter(role=StructuralRole.MANAGER, pk__in=assigned)

    @staticmethod
    def maintenance_of(prop: Property) -> QuerySet:
        assigned = UserProperty.objects.filter(is_active=True, property=prop).values(
            "user_id"
        )
        return _reachable_users().filter(
            role=StructuralRole.MAINTENANCE, pk__in=assigned
        )

    @staticmethod
    def security_agents_of(
        prop: Property, building: Building | None = None
    ) -> QuerySet:
        """Security agents of one building, or of any building of the property."""
        return _agents_of(StructuralRole.SECURITY, prop, building)

    @staticmethod
    def cleaning_agents_of(
        prop: Property, building: Building | None = None
    ) -> QuerySet:
        """Cleaning agents of one building, or of any building of the property."""
        return _agents_of(StructuralRole.CLEANING, prop, building)

    @staticmethod
    def management(prop: Property) -> QuerySet:
        """The people running the property: the syndics of its syndicat and its managers (admins excluded)."""
        return UserDirectory.syndics_of(prop.syndicat) | UserDirectory.managers_of(prop)

    @staticmethod
    def management_and_admins(prop: Property) -> QuerySet:
        return UserDirectory.management(prop) | UserDirectory.platform_admins()

    # --------------------------------------------------- owners and tenants
    @staticmethod
    def unit_owners(unit: Unit) -> QuerySet:
        owner_ids = UnitOwnership.objects.filter(
            unit=unit, status=OwnershipStatus.ACTIVE
        ).values("owner_id")
        return _reachable_users().filter(id__in=owner_ids)

    @staticmethod
    def unit_tenants(unit: Unit) -> QuerySet:
        """All active members of the unit's active lease(s)."""
        member_ids = LeaseMember.objects.filter(
            lease__unit=unit, lease__status=LeaseStatus.ACTIVE, left_at__isnull=True
        ).values("user_id")
        return _reachable_users().filter(id__in=member_ids)

    @staticmethod
    def unit_owners_and_tenants(unit: Unit) -> QuerySet:
        """Everyone with a right on the unit: its owners and its active tenants."""
        return UserDirectory.unit_owners(unit) | UserDirectory.unit_tenants(unit)

    @staticmethod
    def owners_in(prop: Property, building: Building | None = None) -> QuerySet:
        units = (
            Unit.objects.filter(building=building)
            if building
            else Unit.objects.filter(building__property=prop)
        )
        owner_ids = UnitOwnership.objects.filter(
            unit__in=units, status=OwnershipStatus.ACTIVE
        ).values("owner_id")
        return _reachable_users().filter(id__in=owner_ids)

    @staticmethod
    def tenants_in(prop: Property, building: Building | None = None) -> QuerySet:
        units = (
            Unit.objects.filter(building=building)
            if building
            else Unit.objects.filter(building__property=prop)
        )
        member_ids = LeaseMember.objects.filter(
            lease__unit__in=units,
            lease__status=LeaseStatus.ACTIVE,
            left_at__isnull=True,
        ).values("user_id")
        return _reachable_users().filter(id__in=member_ids)

    # ------------------------------------------------------ target roles
    @staticmethod
    def users_by_property_role(
        prop: Property, roles: Iterable[str], building: Building | None = None
    ) -> dict[int, set[str]]:
        """Who holds each of `roles` in the property (or in one building of it).

        Returns {user_id: {the roles through which they were found}}. Used to
        resolve the `target_roles` of an announcement, event, document or survey.
        """
        found: dict[int, set[str]] = defaultdict(set)

        def add(users: QuerySet, role: str) -> None:
            for user_id in users.values_list("id", flat=True):
                found[user_id].add(role)

        for role in set(roles):
            if role == StructuralRole.ADMIN:
                add(UserDirectory.platform_admins(), role)
            elif role == StructuralRole.SYNDIC:
                add(UserDirectory.syndics_of(prop.syndicat), role)
            elif role == StructuralRole.MANAGER:
                add(UserDirectory.managers_of(prop), role)
            elif role == StructuralRole.MAINTENANCE:
                add(UserDirectory.maintenance_of(prop), role)
            elif role == StructuralRole.SECURITY:
                add(UserDirectory.security_agents_of(prop, building), role)
            elif role == StructuralRole.CLEANING:
                add(UserDirectory.cleaning_agents_of(prop, building), role)
            elif role == PropertyRole.OWNER:
                add(UserDirectory.owners_in(prop, building), role)
            elif role == PropertyRole.TENANT:
                add(UserDirectory.tenants_in(prop, building), role)
        return dict(found)
