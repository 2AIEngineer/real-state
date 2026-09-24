"""Who may do what with syndicats, promoters, properties, buildings, units
and ownerships.

- Platform administrators create and delete syndicats, promoters and
  properties, switch them on or off, and set a property's plan.
- Syndics (and admins) govern the records themselves: the syndicat and
  property details, their images, and erasing ownership lines.
- Management (admins, syndics, managers) runs what is inside a property:
  buildings, units, ownership changes, statistics.
- Everyone linked to a property sees it and its buildings; units are seen
  in full by the staff in charge, and by their own owners and tenants.
"""

from django.db.models import Q

from apps.accounts.services.authorization import AccessService
from apps.properties.models import Building, Property, Syndicat, Unit, UnitOwnership


class SyndicatPolicy:
    @staticmethod
    def visible_filter(user) -> Q:
        """Syndicats the user is assigned to or holds a property in (all for admins)."""
        if AccessService.is_platform_admin(user):
            return Q()
        return Q(properties__id__in=AccessService.accessible_property_ids(user)) | Q(
            user_assignments__user=user, user_assignments__is_active=True
        )

    @staticmethod
    def can_create(user) -> bool:
        return AccessService.is_platform_admin(user)

    @staticmethod
    def can_update(user, syndicat: Syndicat) -> bool:
        """Its details and images. Managers never modify the syndicat record."""
        return AccessService.manages_syndicat(user, syndicat)

    @staticmethod
    def can_change_status(user) -> bool:
        """Activate or deactivate."""
        return AccessService.is_platform_admin(user)

    @staticmethod
    def can_delete(user) -> bool:
        return AccessService.is_platform_admin(user)


class PromoterPolicy:
    @staticmethod
    def visible_filter(user) -> Q:
        """Promoters of the properties the user manages (all for admins)."""
        if AccessService.is_platform_admin(user):
            return Q()
        return Q(properties__id__in=AccessService.managed_property_ids(user))

    @staticmethod
    def can_manage(user) -> bool:
        """Create, edit and delete promoters."""
        return AccessService.is_platform_admin(user)


class PropertyPolicy:
    @staticmethod
    def visible_filter(user) -> Q:
        """Properties the user is linked to (all for admins)."""
        if AccessService.is_platform_admin(user):
            return Q()
        return Q(pk__in=AccessService.accessible_property_ids(user))

    @staticmethod
    def can_view(user, prop: Property) -> bool:
        return AccessService.is_platform_admin(
            user
        ) or AccessService.is_staff_or_resident_of_property(user, prop)

    @staticmethod
    def can_see_inactive(user) -> bool:
        return AccessService.is_platform_admin(user)

    @staticmethod
    def can_create(user, syndicat: Syndicat) -> bool:
        """Admins, and syndics covering the whole syndicat."""
        return AccessService.manages_syndicat(user, syndicat)

    @staticmethod
    def can_update(user, prop: Property) -> bool:
        """Its details and images. Managers run the content, never the record."""
        return AccessService.manages_syndicat(user, prop.syndicat)

    @staticmethod
    def can_change_status(user) -> bool:
        return AccessService.is_platform_admin(user)

    @staticmethod
    def can_set_plan(user) -> bool:
        """Enable or disable modules: a commercial decision."""
        return AccessService.is_platform_admin(user)

    @staticmethod
    def can_change_promoter(user) -> bool:
        return AccessService.is_platform_admin(user)

    @staticmethod
    def can_delete(user) -> bool:
        return AccessService.is_platform_admin(user)

    @staticmethod
    def can_view_statistics(user, prop: Property) -> bool:
        return AccessService.manages_property(user, prop)


class BuildingPolicy:
    @staticmethod
    def can_list(user, prop: Property) -> bool:
        return AccessService.is_staff_or_resident_of_property(user, prop)

    @staticmethod
    def can_view(user, building: Building) -> bool:
        return AccessService.is_staff_or_resident_of_property(user, building.property)

    @staticmethod
    def can_create(user, prop: Property) -> bool:
        return AccessService.manages_property(user, prop)

    @staticmethod
    def can_update(user, building: Building) -> bool:
        return AccessService.manages_property(user, building.property)

    @staticmethod
    def can_delete(user, building: Building) -> bool:
        return AccessService.manages_property(user, building.property)


class UnitPolicy:
    @staticmethod
    def can_see_all_units(user, building: Building) -> bool:
        """Staff working in the building; others only see their own units."""
        return AccessService.is_staff_of_building(user, building)

    @staticmethod
    def can_view(user, unit: Unit) -> bool:
        return AccessService.is_staff_of_building(
            user, unit.building
        ) or AccessService.is_owner_or_tenant_of(user, unit)

    @staticmethod
    def can_create(user, building: Building) -> bool:
        return AccessService.manages_property(user, building.property)

    @staticmethod
    def can_update(user, unit: Unit) -> bool:
        return AccessService.manages_property(user, unit.building.property)

    @staticmethod
    def can_delete(user, unit: Unit) -> bool:
        return AccessService.manages_property(user, unit.building.property)


class OwnershipPolicy:
    @staticmethod
    def can_view_history(user, unit: Unit) -> bool:
        return AccessService.manages_property(
            user, unit.building.property
        ) or AccessService.is_owner_of(user, unit)

    @staticmethod
    def can_change(user, unit: Unit) -> bool:
        """Transfer the unit, add a co-owner, end an ownership."""
        return AccessService.manages_property(user, unit.building.property)

    @staticmethod
    def can_delete(user, ownership: UnitOwnership) -> bool:
        """Erase a line recorded by mistake."""
        return AccessService.manages_syndicat(user, ownership.unit.building.property.syndicat)
