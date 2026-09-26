"""Shared facts about people: who they are, and where.

This module states facts, it takes no decision. "May this user edit this
booking?" is answered by the module that owns bookings, in its `policies.py`,
by combining the facts below.

Three links tie a person to a property, and they are never mixed:

1. **Management** — an admin, the syndic of its syndicat, the manager of the
   property. They have authority over its content; it does not mean they work
   there (`manages_property`).
2. **On-site work** — maintenance (assigned to properties), security and
   cleaning (assigned to buildings). These are the people physically on site
   (`works_on_site_in_property`).
3. **Living there** — owner or tenant of a unit. Never an account role: a user
   owns while an active `UnitOwnership` says so, and rents while they are an
   active member of an active lease (`is_resident_of_property`). It is the only
   link that differs from one property to another for the same account, and it
   exists with the plain `standard` role.

Every function answers one of those questions only. The two useful unions
(`is_staff_of_property`, `is_staff_or_resident_of_property`) do nothing but
enumerate the functions above, so a reader sees at once what they cover.
"""

from __future__ import annotations

from django.db.models import QuerySet

from apps.accounts.enums import StructuralRole
from apps.accounts.models import (
    ROLES_ASSIGNED_TO_BUILDINGS,
    ROLES_ASSIGNED_TO_PROPERTIES,
    ROLES_ASSIGNED_TO_SYNDICATS,
    UserBuilding,
    UserProperty,
    UserSyndicat,
)
from apps.leasing.models import LeaseMember, LeaseStatus
from apps.properties.models import (
    Building,
    OwnershipStatus,
    Property,
    Syndicat,
    Unit,
    UnitOwnership,
)


def active_ownerships() -> QuerySet[UnitOwnership]:
    return UnitOwnership.objects.filter(status=OwnershipStatus.ACTIVE)


def active_lease_memberships() -> QuerySet[LeaseMember]:
    """Members still living under a lease that is still running."""
    return LeaseMember.objects.filter(
        left_at__isnull=True, lease__status=LeaseStatus.ACTIVE
    )


def _no_ids(model) -> QuerySet:
    return model.objects.none().values("id")


class AccessService:
    # ------------------------------------------- 1. one role, one place at a time
    @staticmethod
    def is_platform_admin(user) -> bool:
        return bool(user and user.is_active and user.role == StructuralRole.ADMIN)

    @staticmethod
    def is_syndic_of(user, syndicat: Syndicat) -> bool:
        """A syndic assigned to this syndicat."""
        return (
            user.is_active
            and user.role == StructuralRole.SYNDIC
            and UserSyndicat.objects.filter(
                user=user, is_active=True, syndicat=syndicat
            ).exists()
        )

    @staticmethod
    def is_manager_of(user, prop: Property) -> bool:
        """A manager assigned to this property."""
        return (
            user.is_active
            and user.role == StructuralRole.MANAGER
            and UserProperty.objects.filter(
                user=user, is_active=True, property=prop
            ).exists()
        )

    @staticmethod
    def is_maintenance_of(user, prop: Property) -> bool:
        """A maintenance agent assigned to this property."""
        return (
            user.is_active
            and user.role == StructuralRole.MAINTENANCE
            and UserProperty.objects.filter(
                user=user, is_active=True, property=prop
            ).exists()
        )

    @staticmethod
    def is_security_of(user, building: Building) -> bool:
        """A security agent assigned to this building."""
        return (
            user.is_active
            and user.role == StructuralRole.SECURITY
            and UserBuilding.objects.filter(
                user=user, is_active=True, building=building
            ).exists()
        )

    @staticmethod
    def is_cleaning_of(user, building: Building) -> bool:
        """A cleaning agent assigned to this building."""
        return (
            user.is_active
            and user.role == StructuralRole.CLEANING
            and UserBuilding.objects.filter(
                user=user, is_active=True, building=building
            ).exists()
        )

    @staticmethod
    def is_security_in_property(user, prop: Property) -> bool:
        """A security agent assigned to a building of this property."""
        return (
            user.is_active
            and user.role == StructuralRole.SECURITY
            and UserBuilding.objects.filter(
                user=user, is_active=True, building__property=prop
            ).exists()
        )

    @staticmethod
    def is_cleaning_in_property(user, prop: Property) -> bool:
        """A cleaning agent assigned to a building of this property."""
        return (
            user.is_active
            and user.role == StructuralRole.CLEANING
            and UserBuilding.objects.filter(
                user=user, is_active=True, building__property=prop
            ).exists()
        )

    # ----------------------------------------- 2. managing is not working on site
    @staticmethod
    def manages_property(user, prop: Property) -> bool:
        """Has authority over the property: an admin, the syndic of its syndicat, its manager."""
        return (
            AccessService.is_platform_admin(user)
            or AccessService.is_syndic_of(user, prop.syndicat)
            or AccessService.is_manager_of(user, prop)
        )

    @staticmethod
    def manages_syndicat(user, syndicat: Syndicat) -> bool:
        """Has authority over the syndicat itself: an admin or its syndic (managers excluded)."""
        return AccessService.is_platform_admin(user) or AccessService.is_syndic_of(
            user, syndicat
        )

    @staticmethod
    def works_on_site_in_property(user, prop: Property) -> bool:
        """Is on the ground in this property: maintenance, security or cleaning.

        Management (admin, syndic, manager) is not part of it: it decides, it is
        not on site.
        """
        return (
            AccessService.is_maintenance_of(user, prop)
            or AccessService.is_security_in_property(user, prop)
            or AccessService.is_cleaning_in_property(user, prop)
        )

    @staticmethod
    def works_on_site_in_building(user, building: Building) -> bool:
        """Is on the ground in this building: the maintenance of its property, or
        the security and cleaning agents of the building itself."""
        return (
            AccessService.is_maintenance_of(user, building.property)
            or AccessService.is_security_of(user, building)
            or AccessService.is_cleaning_of(user, building)
        )

    @staticmethod
    def is_staff_of_property(user, prop: Property) -> bool:
        """Works for the property: its management, or its on-site staff."""
        return AccessService.manages_property(
            user, prop
        ) or AccessService.works_on_site_in_property(user, prop)

    @staticmethod
    def is_staff_of_building(user, building: Building) -> bool:
        """Works for the building: the management of its property, or its on-site staff."""
        return AccessService.manages_property(
            user, building.property
        ) or AccessService.works_on_site_in_building(user, building)

    # ------------------------------------------------- 3. owners and tenants
    @staticmethod
    def is_owner_of(user, unit: Unit) -> bool:
        return active_ownerships().filter(owner=user, unit=unit).exists()

    @staticmethod
    def is_tenant_of(user, unit: Unit) -> bool:
        return active_lease_memberships().filter(user=user, lease__unit=unit).exists()

    @staticmethod
    def is_owner_or_tenant_of(user, unit: Unit) -> bool:
        if not user or not user.is_active:
            return False
        return AccessService.is_owner_of(user, unit) or AccessService.is_tenant_of(
            user, unit
        )

    @staticmethod
    def active_lease_membership(user, unit: Unit) -> LeaseMember | None:
        """The user's row on the lease currently running on `unit`, if any."""
        return (
            active_lease_memberships()
            .filter(user=user, lease__unit=unit)
            .select_related("lease")
            .first()
        )

    @staticmethod
    def is_owner_in_property(user, prop: Property) -> bool:
        """Owns at least one unit of the property."""
        return (
            active_ownerships()
            .filter(owner=user, unit__building__property=prop)
            .exists()
        )

    @staticmethod
    def is_tenant_in_property(user, prop: Property) -> bool:
        """Rents at least one unit of the property."""
        return (
            active_lease_memberships()
            .filter(user=user, lease__unit__building__property=prop)
            .exists()
        )

    @staticmethod
    def is_resident_of_property(user, prop: Property) -> bool:
        """Owns or rents a unit there. True with the plain `standard` role too:
        owners and tenants hold no staff role."""
        return AccessService.is_owner_in_property(
            user, prop
        ) or AccessService.is_tenant_in_property(user, prop)

    # ------------------------------- 4. any link at all with a property
    @staticmethod
    def is_staff_or_resident_of_property(user, prop: Property) -> bool:
        """Has a reason to open this property: works there (management or on site), or lives there."""
        if not user or not user.is_active:
            return False
        return AccessService.is_staff_of_property(
            user, prop
        ) or AccessService.is_resident_of_property(user, prop)

    # ------------------------------------- 5. id lists, to filter querysets
    @staticmethod
    def assigned_syndicat_ids(user) -> QuerySet:
        """Syndicats a syndic is assigned to (empty for every other role)."""
        if not user.is_active or user.role not in ROLES_ASSIGNED_TO_SYNDICATS:
            return UserSyndicat.objects.none().values("syndicat_id")
        return UserSyndicat.objects.filter(user=user, is_active=True).values(
            "syndicat_id"
        )

    @staticmethod
    def assigned_property_ids(user) -> QuerySet:
        """Properties a manager or a maintenance agent is assigned to (empty for every other role)."""
        if not user.is_active or user.role not in ROLES_ASSIGNED_TO_PROPERTIES:
            return UserProperty.objects.none().values("property_id")
        return UserProperty.objects.filter(user=user, is_active=True).values(
            "property_id"
        )

    @staticmethod
    def assigned_building_ids(user) -> QuerySet:
        """Buildings a security or cleaning agent is assigned to (empty for every other role)."""
        if not user.is_active or user.role not in ROLES_ASSIGNED_TO_BUILDINGS:
            return UserBuilding.objects.none().values("building_id")
        return UserBuilding.objects.filter(user=user, is_active=True).values(
            "building_id"
        )

    @staticmethod
    def managed_property_ids(user) -> QuerySet:
        """Properties the user manages (`manages_property`).

        Admins: all. Syndics: the properties of their syndicats. Managers: their
        properties. Everyone else, maintenance and owners included: none.
        """
        if not user.is_active:
            return _no_ids(Property)
        if user.role == StructuralRole.ADMIN:
            return Property.objects.values("id")
        if user.role == StructuralRole.SYNDIC:
            return Property.objects.filter(
                syndicat_id__in=AccessService.assigned_syndicat_ids(user)
            ).values("id")
        if user.role == StructuralRole.MANAGER:
            return Property.objects.filter(
                id__in=AccessService.assigned_property_ids(user)
            ).values("id")
        return _no_ids(Property)

    @staticmethod
    def property_ids_worked_on_site(user) -> QuerySet:
        """Properties the user is on the ground in (`works_on_site_in_property`).

        Maintenance: their properties. Security, cleaning: the properties of
        their buildings. Everyone else, management included: none.
        """
        if not user.is_active:
            return _no_ids(Property)
        if user.role == StructuralRole.MAINTENANCE:
            return Property.objects.filter(
                id__in=AccessService.assigned_property_ids(user)
            ).values("id")
        if user.role in ROLES_ASSIGNED_TO_BUILDINGS:
            return Property.objects.filter(
                buildings__id__in=AccessService.assigned_building_ids(user)
            ).values("id")
        return _no_ids(Property)

    @staticmethod
    def staff_property_ids(user) -> set[int]:
        """Properties the user works for (`is_staff_of_property`): management and on-site."""
        managed = AccessService.managed_property_ids(user).values_list("id", flat=True)
        on_site = AccessService.property_ids_worked_on_site(user).values_list(
            "id", flat=True
        )
        return set(managed) | set(on_site)

    @staticmethod
    def owned_unit_ids(user) -> QuerySet:
        return active_ownerships().filter(owner=user).values("unit_id")

    @staticmethod
    def rented_unit_ids(user) -> QuerySet:
        return active_lease_memberships().filter(user=user).values("lease__unit_id")

    @staticmethod
    def owned_or_rented_unit_ids(user) -> set[int]:
        owned = set(
            AccessService.owned_unit_ids(user).values_list("unit_id", flat=True)
        )
        rented = set(
            AccessService.rented_unit_ids(user).values_list("lease__unit_id", flat=True)
        )
        return owned | rented

    @staticmethod
    def resident_property_ids(user) -> set[int]:
        """Properties where the user owns or rents a unit (`is_resident_of_property`)."""
        return set(
            Unit.objects.filter(
                id__in=AccessService.owned_or_rented_unit_ids(user)
            ).values_list("building__property_id", flat=True)
        )

    @staticmethod
    def accessible_property_ids(user) -> set[int]:
        """Properties the user may open (`is_staff_or_resident_of_property`)."""
        return AccessService.staff_property_ids(
            user
        ) | AccessService.resident_property_ids(user)

    @staticmethod
    def accessible_syndicat_ids(user) -> set[int] | None:
        """Syndicats the user may open; `None` means every one of them (admins).

        A syndic sees the syndicats they run before those hold any property,
        because their assignment says so.
        """
        if not user.is_active:
            return set()
        if user.role == StructuralRole.ADMIN:
            return None
        assigned = AccessService.assigned_syndicat_ids(user).values_list(
            "syndicat_id", flat=True
        )
        through_properties = Property.objects.filter(
            id__in=AccessService.accessible_property_ids(user)
        ).values_list("syndicat_id", flat=True)
        return set(assigned) | set(through_properties)
