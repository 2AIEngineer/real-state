"""Who may do what with the visitor log.

The gate staff of a unit (its management and the security assigned to its
building or property) log visitors, check them out and complete their
details. The unit's owners and tenants see their own visitors. Only
management deletes an entry, to correct a mistake.
"""

from django.db.models import Q

from apps.accounts.enums import StructuralRole
from apps.accounts.services.authorization import AccessService
from apps.properties.models import Unit
from apps.visitors.models import Visitor


def _is_gate_staff(user, unit: Unit) -> bool:
    """The management of the unit's property, or the security of its building."""
    return AccessService.manages_property(
        user, unit.building.property
    ) or AccessService.is_security_of(user, unit.building)


class VisitorPolicy:
    @staticmethod
    def visible_filter(user) -> Q:
        visible = Q(property_id__in=AccessService.managed_property_ids(user)) | Q(
            unit_id__in=list(AccessService.owned_or_rented_unit_ids(user))
        )
        if user.role == StructuralRole.SECURITY:
            visible |= Q(unit__building_id__in=AccessService.assigned_building_ids(user))
        return visible

    @staticmethod
    def can_view(user, visitor: Visitor) -> bool:
        return _is_gate_staff(user, visitor.unit) or AccessService.is_owner_or_tenant_of(
            user, visitor.unit
        )

    @staticmethod
    def can_register(user, unit: Unit) -> bool:
        return _is_gate_staff(user, unit)

    @staticmethod
    def can_update(user, visitor: Visitor) -> bool:
        """Check-out, details and identity document."""
        return _is_gate_staff(user, visitor.unit)

    @staticmethod
    def can_delete(user, visitor: Visitor) -> bool:
        return AccessService.manages_property(user, visitor.unit.building.property)
