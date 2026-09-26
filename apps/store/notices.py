"""What people are told about store orders."""

from __future__ import annotations

from decimal import Decimal

from apps.notifications.models import NotificationCategory, Severity
from apps.notifications.services import NotificationIntent, NotificationService
from apps.store.models import Order


def _tell_customer(
    order: Order,
    *,
    kind: str,
    title: str,
    body: str,
    actor,
    severity: str = Severity.INFO,
) -> None:
    NotificationService.notify(
        NotificationIntent(
            event_type=f"store.order_{kind}",
            category=NotificationCategory.STORE,
            title=title,
            body=body,
            to=[order.orderer],
            target=order,
            severity=severity,
            exclude=[actor] if actor else [],
            include_platform_admins=False,
            data={"order_id": order.pk},
            action_path=f"/store/orders/{order.pk}",
        )
    )


def order_placed(order: Order, *, total: Decimal, lines_count: int) -> None:
    """The store staff (platform admins) learn of the order; the customer gets a receipt."""
    actor = order.orderer
    NotificationService.notify(
        NotificationIntent(
            event_type="store.order_created",
            category=NotificationCategory.STORE,
            title=f"Nouvelle commande #{order.pk} — {order.property.name}",
            body=f"{actor.get_full_name()} a passé une commande de {total} ({lines_count} article(s)).",
            target=order,
            exclude=[actor],
            data={"order_id": order.pk, "property_id": order.property_id},
            action_path=f"/store/orders/{order.pk}",
        )
    )
    _tell_customer(
        order,
        kind="received",
        actor=None,
        title=f"Commande #{order.pk} enregistrée",
        body=f"Montant total : {total}.",
    )


def order_confirmed(order: Order, *, actor) -> None:
    _tell_customer(
        order,
        kind="confirmed",
        actor=actor,
        title=f"Commande #{order.pk} confirmée",
        body="Votre commande est en préparation.",
    )


def order_delivered(order: Order, *, actor) -> None:
    _tell_customer(
        order,
        kind="delivered",
        actor=actor,
        severity=Severity.SUCCESS,
        title=f"Commande #{order.pk} livrée",
        body="Votre commande a été livrée.",
    )


def order_cancelled_by_customer(order: Order, *, actor, reason: str) -> None:
    """The store staff (platform admins) are told the customer cancelled."""
    NotificationService.notify(
        NotificationIntent(
            event_type="store.order_cancelled",
            category=NotificationCategory.STORE,
            title=f"Commande #{order.pk} annulée par le client",
            body=reason or "Le client a annulé sa commande.",
            target=order,
            exclude=[actor],
            data={"order_id": order.pk},
        )
    )


def order_cancelled_by_staff(order: Order, *, actor, reason: str) -> None:
    _tell_customer(
        order,
        kind="cancelled",
        actor=actor,
        severity=Severity.WARNING,
        title=f"Commande #{order.pk} annulée",
        body=reason or "Votre commande a été annulée.",
    )
