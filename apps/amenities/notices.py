"""What people are told about bookings."""

from __future__ import annotations

import datetime as dt

from apps.accounts.services.directory import UserDirectory
from apps.amenities.models import Booking, BookingStatus
from apps.notifications.models import NotificationCategory, Severity
from apps.notifications.services import NotificationIntent, NotificationService
from apps.properties import timezones


def _fmt(booking, value: dt.datetime) -> str:
    return timezones.local(booking.amenity.property, value).strftime("%d/%m/%Y %H:%M")


def _slot(booking: Booking) -> str:
    return f"{_fmt(booking, booking.start_datetime)} → {_fmt(booking, booking.end_datetime)}"


def _tell(
    booking: Booking,
    *,
    kind: str,
    title: str,
    body: str,
    actor,
    severity: str = Severity.INFO,
) -> None:
    """Tell the booker by name and the property management by BCC."""
    NotificationService.notify(
        NotificationIntent(
            event_type=f"booking.{kind}",
            category=NotificationCategory.BOOKING,
            title=title,
            body=body,
            to=[booking.booker],
            bcc=UserDirectory.management(booking.amenity.property),
            target=booking,
            severity=severity,
            exclude=[actor] if actor else [],
            data={"booking_id": booking.pk, "amenity_id": booking.amenity_id},
            action_path=f"/bookings/{booking.pk}",
        )
    )


def booked(booking: Booking) -> None:
    is_pending = booking.status == BookingStatus.PENDING
    _tell(
        booking,
        kind="created",
        actor=None,
        title=f"Réservation #{booking.pk} — {booking.amenity.name}",
        body=f"{_slot(booking)}. " + ("En attente de validation." if is_pending else "Confirmée."),
    )


def decided(booking: Booking, *, actor, approved: bool, note: str) -> None:
    verdict = "confirmée" if approved else "refusée"
    _tell(
        booking,
        kind="approved" if approved else "rejected",
        actor=actor,
        severity=Severity.SUCCESS if approved else Severity.WARNING,
        title=f"Réservation #{booking.pk} {verdict} — {booking.amenity.name}",
        body=note or _slot(booking),
    )


def cancelled(booking: Booking, *, actor, reason: str) -> None:
    _tell(
        booking,
        kind="cancelled",
        actor=actor,
        severity=Severity.WARNING,
        title=f"Réservation #{booking.pk} annulée — {booking.amenity.name}",
        body=reason or _slot(booking),
    )
