"""Residential store: catalogue (platform admins only) and orders from owners and tenants.

Prices and totals are always computed server-side from the catalogue, frozen
on the order lines, and stock is reserved atomically when ordering.

    PENDING ──confirm──▶ CONFIRMED ──deliver──▶ DELIVERED
    PENDING ──deliver──▶ DELIVERED
    PENDING | CONFIRMED ──cancel──▶ CANCELLED (stock restored)
"""

from __future__ import annotations

from dataclasses import dataclass
from decimal import Decimal

from django.db import transaction
from django.db.models import F, QuerySet
from django.utils import timezone

from apps.common.db import deleting
from apps.common.exceptions import (
    BusinessRuleViolation,
    InvalidInput,
    InvalidTransition,
    NotFound,
    PermissionDenied,
)
from apps.common.services.audit import AuditService
from apps.notifications.services import delete_notification_traces
from apps.properties.enums import Feature
from apps.properties.models import Property, Unit
from apps.properties.services import FeatureGate
from apps.store import errors, notices
from apps.store.audit import StoreAudit
from apps.store.models import Order, OrderItem, OrderStatus, Product
from apps.store.policies import OrderPolicy

MAX_LINES = 50


@dataclass(frozen=True)
class OrderLine:
    product_id: int
    quantity: int


class OrderService:
    @staticmethod
    def list_visible(
        *, actor, property_id: int, status: str | None = None, mine: bool = False
    ) -> QuerySet[Order]:
        qs = Order.objects.select_related("property", "orderer", "unit").prefetch_related("items")
        if mine or not OrderPolicy.can_see_all_orders(actor):
            qs = qs.filter(orderer=actor)
        qs = qs.filter(property_id=property_id)
        if status:
            qs = qs.filter(status=status)
        return qs

    @staticmethod
    def get_visible(*, actor, prop: Property, order_id: int) -> Order:
        order = (
            Order.objects.select_related("property", "orderer", "unit")
            .prefetch_related("items")
            .filter(pk=order_id, property=prop)
            .first()
        )
        if order is None or not OrderPolicy.can_view(actor, order):
            raise NotFound("Order not found.")
        return order

    @staticmethod
    @transaction.atomic
    def place(
        *,
        actor,
        prop: Property,
        lines: list[OrderLine],
        unit: Unit | None = None,
        delivery_instructions: str = "",
        customer_note: str = "",
    ) -> Order:
        FeatureGate.require(prop, Feature.STORE)
        if not OrderPolicy.can_place(actor, prop):
            raise PermissionDenied(
                "Only owners and tenants of this property can order from its store."
            )
        if unit is not None and not OrderPolicy.can_deliver_to(actor, unit):
            raise InvalidInput("You can only deliver to one of your units.", field="unit_id")
        if not lines:
            raise InvalidInput("An order needs at least one item.", field="items")
        if len(lines) > MAX_LINES:
            raise InvalidInput(f"At most {MAX_LINES} lines per order.", field="items")
        quantities: dict[int, int] = {}
        for line in lines:
            if line.quantity < 1:
                raise InvalidInput("Quantities must be positive.", field="items")
            quantities[line.product_id] = quantities.get(line.product_id, 0) + line.quantity

        # Lock in primary-key order: concurrent orders never deadlock.
        products = {
            p.pk: p
            for p in Product.objects.select_for_update(of=("self",))
            .filter(pk__in=quantities)
            .order_by("pk")
        }
        missing = set(quantities) - products.keys()
        if missing:
            raise InvalidInput(f"Unknown product(s): {sorted(missing)}.", field="items")
        for product_id, quantity in quantities.items():
            product = products[product_id]
            if product.property_id != prop.pk or not product.is_active:
                raise BusinessRuleViolation(
                    f"'{product.name}' is not available in this store.", code="product_unavailable"
                )
            if product.stock_quantity < quantity:
                raise BusinessRuleViolation(
                    f"Only {product.stock_quantity} '{product.name}' left in stock.",
                    code="insufficient_stock",
                )

        total = sum((products[pid].price * qty for pid, qty in quantities.items()), Decimal("0"))
        order = Order.objects.create(
            property=prop,
            orderer=actor,
            unit=unit,
            total_amount=total,
            delivery_instructions=delivery_instructions,
            customer_note=customer_note,
        )
        OrderItem.objects.bulk_create(
            [
                OrderItem(
                    order=order,
                    product=products[pid],
                    product_name=products[pid].name,
                    unit_price=products[pid].price,
                    quantity=qty,
                    line_total=products[pid].price * qty,
                )
                for pid, qty in quantities.items()
            ]
        )
        for pid, qty in quantities.items():
            Product.objects.filter(pk=pid).update(
                stock_quantity=F("stock_quantity") - qty, updated_at=timezone.now()
            )
        AuditService.record(
            actor=actor,
            action=StoreAudit.ORDER_PLACED,
            target=order,
            property_id=prop.pk,
            metadata={"total": str(total)},
        )
        notices.order_placed(order, total=total, lines_count=len(quantities))
        return order

    @staticmethod
    @transaction.atomic
    def delete(*, actor, order: Order) -> None:
        """Permanent removal of an order; reserved stock goes back to the shelf."""
        if not OrderPolicy.can_delete(actor):
            raise errors.store_admins_only()
        order = OrderService._lock(order)
        if order.status in (OrderStatus.PENDING, OrderStatus.CONFIRMED):
            OrderService._restore_stock(order)
        AuditService.record(
            actor=actor,
            action=StoreAudit.ORDER_DELETED,
            target=order,
            property_id=order.property_id,
            metadata={"status": order.status, "total": str(order.total_amount)},
        )
        from apps.chat.services import ChatService

        with deleting("order"):
            ChatService.delete_conversation_of(order)
            delete_notification_traces(order)
            order.delete()

    @staticmethod
    def _lock(order: Order) -> Order:
        return (
            Order.objects.select_for_update(of=("self",))
            .select_related("property", "orderer")
            .get(pk=order.pk)
        )

    @staticmethod
    @transaction.atomic
    def confirm(*, actor, order: Order, note: str = "") -> Order:
        if not OrderPolicy.can_process(actor):
            raise errors.store_admins_only()
        order = OrderService._lock(order)
        if order.status != OrderStatus.PENDING:
            raise InvalidTransition("Only pending orders can be confirmed.")
        order.status = OrderStatus.CONFIRMED
        order.confirmed_at = timezone.now()
        order.staff_note = note or order.staff_note
        order.save(update_fields=["status", "confirmed_at", "staff_note", "updated_at"])
        AuditService.record(
            actor=actor,
            action=StoreAudit.ORDER_CONFIRMED,
            target=order,
            property_id=order.property_id,
        )
        notices.order_confirmed(order, actor=actor)
        return order

    @staticmethod
    @transaction.atomic
    def deliver(*, actor, order: Order, note: str = "") -> Order:
        if not OrderPolicy.can_process(actor):
            raise errors.store_admins_only()
        order = OrderService._lock(order)
        if order.status not in (OrderStatus.PENDING, OrderStatus.CONFIRMED):
            raise InvalidTransition("Only open orders can be delivered.")
        order.status = OrderStatus.DELIVERED
        order.delivered_at = timezone.now()
        order.staff_note = note or order.staff_note
        order.save(update_fields=["status", "delivered_at", "staff_note", "updated_at"])
        AuditService.record(
            actor=actor,
            action=StoreAudit.ORDER_DELIVERED,
            target=order,
            property_id=order.property_id,
        )
        notices.order_delivered(order, actor=actor)
        return order

    @staticmethod
    def _restore_stock(order: Order) -> None:
        items = list(order.items.all())
        for product in (
            Product.objects.select_for_update(of=("self",))
            .filter(pk__in=[i.product_id for i in items])
            .order_by("pk")
        ):
            restored = sum(i.quantity for i in items if i.product_id == product.pk)
            Product.objects.filter(pk=product.pk).update(
                stock_quantity=F("stock_quantity") + restored, updated_at=timezone.now()
            )

    @staticmethod
    @transaction.atomic
    def cancel(*, actor, order: Order, reason: str = "") -> Order:
        order = OrderService._lock(order)
        if not OrderPolicy.can_cancel(actor, order):
            raise NotFound("Order not found.")
        by_orderer = order.orderer_id == actor.pk
        allowed = (
            (OrderStatus.PENDING,) if by_orderer else (OrderStatus.PENDING, OrderStatus.CONFIRMED)
        )
        if order.status not in allowed:
            raise InvalidTransition("This order can no longer be cancelled.")
        OrderService._restore_stock(order)
        order.status = OrderStatus.CANCELLED
        order.cancelled_at = timezone.now()
        order.cancelled_by = actor
        order.cancellation_reason = reason
        order.save(
            update_fields=[
                "status",
                "cancelled_at",
                "cancelled_by",
                "cancellation_reason",
                "updated_at",
            ]
        )
        AuditService.record(
            actor=actor,
            action=StoreAudit.ORDER_CANCELLED,
            target=order,
            property_id=order.property_id,
        )
        if by_orderer:
            notices.order_cancelled_by_customer(order, actor=actor, reason=reason)
        else:
            notices.order_cancelled_by_staff(order, actor=actor, reason=reason)
        return order
