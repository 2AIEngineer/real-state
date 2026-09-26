"""Who may do what with short rentals.

A rental is declared on a unit by its management, one of its tenants or one
of its owners. It is followed by its initiator, the unit's management,
owners and tenants, and the on-site security, who records arrivals. The
initiator and management change it; only management deletes it.
"""

from django.db.models import Q

from apps.accounts.enums import StructuralRole
from apps.accounts.services.authorization import AccessService
from apps.properties.models import Unit
from apps.short_term_rental.models import ShortTermRental, ShortTermRentalMember


def _is_front_desk(user, unit: Unit) -> bool:
    """The management of the unit's property, or the security of its building."""
    return AccessService.manages_property(
        user, unit.building.property
    ) or AccessService.is_security_of(user, unit.building)


class ShortTermRentalPolicy:
    @staticmethod
    def visible_filter(user) -> Q:
        visible = (
            Q(initiated_by=user)
            | Q(
                unit__building__property_id__in=AccessService.managed_property_ids(user)
            )
            | Q(unit_id__in=list(AccessService.owned_or_rented_unit_ids(user)))
        )
        if user.role == StructuralRole.SECURITY:
            visible |= Q(
                unit__building_id__in=AccessService.assigned_building_ids(user)
            )
        return visible

    @staticmethod
    def can_view(user, rental: ShortTermRental) -> bool:
        """Also covers its members."""
        return (
            rental.initiated_by_id == user.pk
            or _is_front_desk(user, rental.unit)
            or AccessService.is_owner_or_tenant_of(user, rental.unit)
        )

    @staticmethod
    def can_view_member(user, member: ShortTermRentalMember) -> bool:
        return ShortTermRentalPolicy.can_view(user, member.short_term_rental)

    @staticmethod
    def can_declare(user, unit: Unit) -> bool:
        return (
            AccessService.manages_property(user, unit.building.property)
            or AccessService.is_tenant_of(user, unit)
            or AccessService.is_owner_of(user, unit)
        )

    @staticmethod
    def can_update(user, rental: ShortTermRental) -> bool:
        """Reschedule, cancel, manage members."""
        return rental.initiated_by_id == user.pk or AccessService.manages_property(
            user, rental.unit.building.property
        )

    @staticmethod
    def can_check_in(user, rental: ShortTermRental) -> bool:
        return _is_front_desk(user, rental.unit)

    @staticmethod
    def can_complete(user, rental: ShortTermRental) -> bool:
        return rental.initiated_by_id == user.pk or _is_front_desk(user, rental.unit)

    @staticmethod
    def can_delete(user, rental: ShortTermRental) -> bool:
        return AccessService.manages_property(user, rental.unit.building.property)
