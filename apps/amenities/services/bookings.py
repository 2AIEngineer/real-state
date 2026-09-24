"""Amenities and bookings.

Overlap rules
- EXCLUSIVE amenities: one blocking booking per time slot, guaranteed by a
  PostgreSQL exclusion constraint (race-proof).
- SHARED amenities: concurrent bookings allowed while the summed party size
  stays within capacity; checked under a row lock on the amenity.

    PENDING ──approve──▶ CONFIRMED        (auto-confirmed when no approval is required)
    PENDING ──reject───▶ REJECTED
    PENDING | CONFIRMED ──cancel──▶ CANCELLED
"""

from __future__ import annotations

import datetime as dt

from django.db import transaction
from django.db.models import QuerySet, Sum
from django.utils import timezone

from apps.amenities import errors, notices
from apps.amenities.audit import BookingAudit
from apps.amenities.models import (
    BLOCKING_BOOKING_STATUSES,
    Amenity,
    Booking,
    BookingMode,
    BookingStatus,
)
from apps.amenities.policies import BookingPolicy
from apps.common.db import translate_integrity_errors
from apps.common.deletion import destroy
from apps.common.exceptions import (
    BusinessRuleViolation,
    InvalidInput,
    InvalidTransition,
    NotFound,
    PermissionDenied,
)
from apps.common.services.audit import AuditService
from apps.properties import timezones
from apps.properties.enums import Feature
from apps.properties.models import Property
from apps.properties.services import FeatureGate

BOOKING_CONSTRAINTS = {"booking_no_overlap_on_exclusive_amenity": errors.slot_taken}


class BookingService:
    @staticmethod
    def list_visible(
        *,
        actor,
        property_id: int,
        amenity_id: int | None = None,
        status: str | None = None,
        mine: bool = False,
    ) -> QuerySet[Booking]:
        qs = Booking.objects.filter(BookingPolicy.visible_filter(actor)).select_related(
            "amenity__property", "booker"
        )
        if mine:
            qs = qs.filter(booker=actor)
        qs = qs.filter(amenity__property_id=property_id)
        if amenity_id:
            qs = qs.filter(amenity_id=amenity_id)
        if status:
            qs = qs.filter(status=status)
        return qs

    @staticmethod
    def get_visible(*, actor, prop: Property, booking_id: int) -> Booking:
        booking = (
            Booking.objects.select_related("amenity__property", "booker")
            .filter(pk=booking_id, amenity__property=prop)
            .first()
        )
        if booking is None or not BookingPolicy.can_view(actor, booking):
            raise NotFound("Booking not found.")
        return booking

    @staticmethod
    def _check_window(
        amenity: Amenity, start: dt.datetime, end: dt.datetime, now: dt.datetime
    ) -> None:
        if end <= start:
            raise InvalidInput("The booking must end after it starts.", field="end_datetime")
        if start < now:
            raise InvalidInput("A booking cannot start in the past.", field="start_datetime")
        minutes = (end - start).total_seconds() / 60
        if minutes < amenity.min_duration_minutes or minutes > amenity.max_duration_minutes:
            raise InvalidInput(
                f"Duration must be between {amenity.min_duration_minutes} and {amenity.max_duration_minutes} minutes.",
                field="end_datetime",
            )
        if start > now + dt.timedelta(days=amenity.max_advance_days):
            raise InvalidInput(
                f"Bookings open {amenity.max_advance_days} days in advance at most.",
                field="start_datetime",
            )
        if amenity.opening_time:
            local_start = timezones.local(amenity.property, start)
            local_end = timezones.local(amenity.property, end)
            if (
                local_start.date() != local_end.date()
                or local_start.time() < amenity.opening_time
                or local_end.time() > amenity.closing_time
            ):
                raise InvalidInput(
                    f"Open from {amenity.opening_time:%H:%M} to {amenity.closing_time:%H:%M}.",
                    field="start_datetime",
                )

    @staticmethod
    @transaction.atomic
    def book(
        *,
        actor,
        amenity: Amenity,
        start: dt.datetime,
        end: dt.datetime,
        party_size: int = 1,
        note: str = "",
    ) -> Booking:
        prop = amenity.property
        FeatureGate.require(prop, Feature.AMENITIES)
        if not BookingPolicy.can_book(actor, prop):
            raise PermissionDenied("Only owners, tenants and management can book amenities.")
        # Serialise bookings of one amenity; also freezes its rules for this check.
        amenity = (
            Amenity.objects.select_for_update(of=("self",))
            .select_related("property")
            .get(pk=amenity.pk)
        )
        if not amenity.is_active:
            raise BusinessRuleViolation(
                "This amenity is not available for booking.", code="amenity_inactive"
            )
        BookingService._check_window(amenity, start, end, timezone.now())
        if party_size < 1 or party_size > amenity.capacity:
            raise InvalidInput(
                f"Party size must be between 1 and {amenity.capacity}.",
                field="party_size",
            )
        exclusive = amenity.booking_mode == BookingMode.EXCLUSIVE
        if not exclusive:
            used = (
                Booking.objects.filter(
                    amenity=amenity,
                    status__in=BLOCKING_BOOKING_STATUSES,
                    start_datetime__lt=end,
                    end_datetime__gt=start,
                ).aggregate(total=Sum("party_size"))["total"]
                or 0
            )
            if used + party_size > amenity.capacity:
                raise BusinessRuleViolation(
                    f"Only {max(amenity.capacity - used, 0)} place(s) left on this slot.",
                    code="capacity_exceeded",
                )
        status = BookingStatus.PENDING if amenity.requires_approval else BookingStatus.CONFIRMED
        with translate_integrity_errors(BOOKING_CONSTRAINTS):
            booking = Booking.objects.create(
                amenity=amenity,
                booker=actor,
                start_datetime=start,
                end_datetime=end,
                status=status,
                is_exclusive=exclusive,
                party_size=party_size,
                booker_note=note,
            )
        AuditService.record(
            actor=actor,
            action=BookingAudit.CREATED,
            target=booking,
            property_id=prop.pk,
        )
        notices.booked(booking)
        return booking

    @staticmethod
    @transaction.atomic
    def delete(*, actor, booking: Booking) -> None:
        """Permanent removal of a booking and its conversation."""
        if not BookingPolicy.can_delete(actor, booking):
            raise PermissionDenied("Only the property management can delete bookings.")
        AuditService.record(
            actor=actor,
            action=BookingAudit.DELETED,
            target=booking,
            property_id=booking.amenity.property_id,
            metadata={"status": booking.status},
        )
        destroy(booking)

    @staticmethod
    def _lock(booking: Booking) -> Booking:
        return (
            Booking.objects.select_for_update(of=("self",))
            .select_related("amenity__property", "booker")
            .get(pk=booking.pk)
        )

    @staticmethod
    @transaction.atomic
    def decide(*, actor, booking: Booking, approve: bool, note: str = "") -> Booking:
        if not BookingPolicy.can_decide(actor, booking):
            raise PermissionDenied("Only the property management can approve or reject bookings.")
        booking = BookingService._lock(booking)
        if booking.status != BookingStatus.PENDING:
            raise InvalidTransition("Only pending bookings can be approved or rejected.")
        if approve and booking.end_datetime <= timezone.now():
            raise InvalidTransition("This booking slot is already over.")
        booking.status = BookingStatus.CONFIRMED if approve else BookingStatus.REJECTED
        booking.decision_note = note
        booking.decided_by = actor
        booking.decided_at = timezone.now()
        booking.save(
            update_fields=[
                "status",
                "decision_note",
                "decided_by",
                "decided_at",
                "updated_at",
            ]
        )
        verb = "approved" if approve else "rejected"
        AuditService.record(
            actor=actor,
            action=BookingAudit(f"booking.{verb}"),
            target=booking,
            property_id=booking.amenity.property_id,
        )
        notices.decided(booking, actor=actor, approved=approve, note=note)
        return booking

    @staticmethod
    @transaction.atomic
    def cancel(*, actor, booking: Booking, reason: str = "") -> Booking:
        booking = BookingService._lock(booking)
        if not BookingPolicy.can_cancel(actor, booking):
            raise NotFound("Booking not found.")
        if booking.status not in BLOCKING_BOOKING_STATUSES:
            raise InvalidTransition("This booking is no longer active.")
        now = timezone.now()
        is_booker = booking.booker_id == actor.pk
        if is_booker and booking.start_datetime <= now:
            raise InvalidTransition(
                "A booking that has started can no longer be cancelled by the booker."
            )
        if not is_booker and booking.end_datetime <= now:
            raise InvalidTransition("This booking is already over.")
        booking.status = BookingStatus.CANCELLED
        booking.cancelled_by = actor
        booking.cancelled_at = now
        booking.cancellation_reason = reason
        booking.save(
            update_fields=[
                "status",
                "cancelled_by",
                "cancelled_at",
                "cancellation_reason",
                "updated_at",
            ]
        )
        AuditService.record(
            actor=actor,
            action=BookingAudit.CANCELLED,
            target=booking,
            property_id=booking.amenity.property_id,
        )
        notices.cancelled(booking, actor=actor, reason=reason)
        return booking
