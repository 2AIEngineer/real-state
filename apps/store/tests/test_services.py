from decimal import Decimal

import pytest

from apps.common.exceptions import BusinessRuleViolation, InvalidTransition, PermissionDenied
from apps.store.models import OrderStatus, Product
from apps.store.services import OrderLine, OrderService, ProductService

pytestmark = pytest.mark.django_db


def product(world, **data):
    return ProductService.create(
        actor=world.admin,
        prop=world.prop,
        data={"name": "Water pack", "price": Decimal("4.50"), "stock_quantity": 10, **data},
    )


def test_catalogue_is_admin_only(world):
    with pytest.raises(PermissionDenied):
        ProductService.create(
            actor=world.manager, prop=world.prop, data={"name": "X", "price": Decimal("1")}
        )


def test_totals_are_computed_server_side_and_prices_frozen(world):
    water, bread = product(world), product(world, name="Bread", price=Decimal("1.20"))
    order = OrderService.place(
        actor=world.tenant, prop=world.prop, lines=[OrderLine(water.pk, 2), OrderLine(bread.pk, 3)]
    )
    assert order.total_amount == Decimal("12.60")
    ProductService.update(actor=world.admin, product=water, changes={"price": Decimal("99")})
    assert order.items.get(product=water).unit_price == Decimal("4.50")


def test_stock_is_reserved_and_restored_on_cancellation(world):
    water = product(world)
    order = OrderService.place(actor=world.tenant, prop=world.prop, lines=[OrderLine(water.pk, 4)])
    assert Product.objects.get(pk=water.pk).stock_quantity == 6
    OrderService.cancel(actor=world.tenant, order=order)
    assert Product.objects.get(pk=water.pk).stock_quantity == 10


def test_insufficient_stock(world):
    water = product(world, stock_quantity=1)
    with pytest.raises(BusinessRuleViolation) as exc:
        OrderService.place(actor=world.tenant, prop=world.prop, lines=[OrderLine(water.pk, 2)])
    assert exc.value.code == "insufficient_stock"


def test_only_owners_and_tenants_order(world):
    with pytest.raises(PermissionDenied):
        OrderService.place(
            actor=world.security, prop=world.prop, lines=[OrderLine(product(world).pk, 1)]
        )


def test_customer_can_only_cancel_pending_orders(world):
    order = OrderService.place(
        actor=world.tenant, prop=world.prop, lines=[OrderLine(product(world).pk, 1)]
    )
    OrderService.confirm(actor=world.admin, order=order)
    with pytest.raises(InvalidTransition):
        OrderService.cancel(actor=world.tenant, order=order)
    order = OrderService.cancel(actor=world.admin, order=order, reason="Out of delivery slots")
    assert order.status == OrderStatus.CANCELLED


def test_orders_are_private(world):
    OrderService.place(actor=world.tenant, prop=world.prop, lines=[OrderLine(product(world).pk, 1)])
    assert list(OrderService.list_visible(actor=world.co_tenant, property_id=world.prop.pk)) == []
    assert OrderService.list_visible(actor=world.admin, property_id=world.prop.pk).count() == 1
