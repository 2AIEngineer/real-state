"""Who may do what in the store.

The store is run by platform administrators: they manage the catalogue and
process orders. Owners and tenants of a property browse its active
products and order; an order is seen by its orderer and by administrators.
"""

from apps.accounts.services.authorization import AccessService
from apps.properties.models import Property, Unit
from apps.store.models import Order, Product


class ProductPolicy:
    @staticmethod
    def can_list(user, prop: Property) -> bool:
        return AccessService.is_platform_admin(
            user
        ) or AccessService.is_staff_or_resident_of_property(user, prop)

    @staticmethod
    def can_see_inactive(user) -> bool:
        return AccessService.is_platform_admin(user)

    @staticmethod
    def can_view(user, product: Product) -> bool:
        if AccessService.is_platform_admin(user):
            return True
        return product.is_active and AccessService.is_staff_or_resident_of_property(
            user, product.property
        )

    @staticmethod
    def can_manage(user) -> bool:
        """Create, edit, delete products and their images."""
        return AccessService.is_platform_admin(user)


class OrderPolicy:
    @staticmethod
    def can_see_all_orders(user) -> bool:
        return AccessService.is_platform_admin(user)

    @staticmethod
    def can_view(user, order: Order) -> bool:
        return order.orderer_id == user.pk or AccessService.is_platform_admin(user)

    @staticmethod
    def can_place(user, prop: Property) -> bool:
        return AccessService.is_resident_of_property(user, prop)

    @staticmethod
    def can_deliver_to(user, unit: Unit) -> bool:
        return AccessService.is_owner_or_tenant_of(user, unit)

    @staticmethod
    def can_process(user) -> bool:
        """Confirm and deliver orders."""
        return AccessService.is_platform_admin(user)

    @staticmethod
    def can_cancel(user, order: Order) -> bool:
        """Which statuses each of them may cancel is an order rule, see the service."""
        return order.orderer_id == user.pk or AccessService.is_platform_admin(user)

    @staticmethod
    def can_delete(user) -> bool:
        return AccessService.is_platform_admin(user)
