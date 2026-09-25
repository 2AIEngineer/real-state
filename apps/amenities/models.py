from django.conf import settings
from django.contrib.postgres.constraints import ExclusionConstraint
from django.contrib.postgres.fields import RangeBoundary, RangeOperators
from django.db import models
from django.db.models import F, Q

from apps.common.db import DateTimeRange
from apps.common.models import TimeStampedModel


class BookingMode(models.TextChoices):
    EXCLUSIVE = "EXCLUSIVE", "Exclusive slot (one booking at a time)"
    SHARED = "SHARED", "Shared (concurrent bookings up to capacity)"


class Amenity(TimeStampedModel):
    property = models.ForeignKey(
        "properties.Property", on_delete=models.CASCADE, related_name="amenities"
    )
    building = models.ForeignKey(
        "properties.Building",
        null=True,
        blank=True,
        on_delete=models.CASCADE,
        related_name="amenities",
    )
    name = models.CharField(max_length=120)
    description = models.TextField(blank=True)
    location = models.CharField(max_length=200, blank=True)
    rules = models.TextField(blank=True)
    booking_mode = models.CharField(
        max_length=10, choices=BookingMode.choices, default=BookingMode.EXCLUSIVE
    )
    capacity = models.PositiveSmallIntegerField(default=1)
    requires_approval = models.BooleanField(default=True)
    opening_time = models.TimeField(null=True, blank=True)
    closing_time = models.TimeField(null=True, blank=True)
    min_duration_minutes = models.PositiveIntegerField(default=30)
    max_duration_minutes = models.PositiveIntegerField(default=240)
    max_advance_days = models.PositiveIntegerField(default=60)
    # Prices; 0 means nothing to pay (a free amenity has all three at 0).
    fee = models.DecimalField(
        max_digits=12, decimal_places=2, default=0, help_text="Flat fee per booking."
    )
    security_fee = models.DecimalField(
        max_digits=12, decimal_places=2, default=0, help_text="Security cost charged per booking."
    )
    hourly_price = models.DecimalField(
        max_digits=12,
        decimal_places=2,
        default=0,
        help_text="Price per hour of use; 0 for a free amenity.",
    )
    is_active = models.BooleanField(default=True)
    created_by = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True, blank=True, related_name="+"
    )

    class Meta:
        verbose_name_plural = "amenities"
        ordering = ["property_id", "name", "id"]
        constraints = [
            models.CheckConstraint(condition=Q(capacity__gte=1), name="amenity_capacity_positive"),
            models.CheckConstraint(
                condition=Q(max_duration_minutes__gte=F("min_duration_minutes")),
                name="amenity_duration_bounds",
            ),
            models.CheckConstraint(
                condition=(Q(opening_time__isnull=True) & Q(closing_time__isnull=True))
                | (
                    Q(opening_time__isnull=False)
                    & Q(closing_time__isnull=False)
                    & Q(closing_time__gt=F("opening_time"))
                ),
                name="amenity_opening_hours_consistent",
            ),
            models.UniqueConstraint(
                "property", models.functions.Lower("name"), name="amenity_name_per_property"
            ),
            models.CheckConstraint(
                condition=Q(fee__gte=0) & Q(security_fee__gte=0) & Q(hourly_price__gte=0),
                name="amenity_prices_non_negative",
            ),
        ]

    def __str__(self) -> str:
        return self.name


class BookingStatus(models.TextChoices):
    PENDING = "PENDING", "Pending approval"
    CONFIRMED = "CONFIRMED", "Confirmed"
    REJECTED = "REJECTED", "Rejected"
    CANCELLED = "CANCELLED", "Cancelled"
    COMPLETED = "COMPLETED", "Completed"


BLOCKING_BOOKING_STATUSES = (BookingStatus.PENDING, BookingStatus.CONFIRMED)


class Booking(TimeStampedModel):
    amenity = models.ForeignKey(Amenity, on_delete=models.CASCADE, related_name="bookings")
    booker = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="bookings"
    )
    start_datetime = models.DateTimeField()
    end_datetime = models.DateTimeField()
    status = models.CharField(
        max_length=10, choices=BookingStatus.choices, default=BookingStatus.PENDING
    )
    # Frozen copy of the amenity mode at booking time: the exclusion
    # constraint below needs it on the row itself.
    is_exclusive = models.BooleanField()
    party_size = models.PositiveSmallIntegerField(default=1)
    booker_note = models.TextField(blank=True)
    decision_note = models.TextField(blank=True)
    decided_by = models.ForeignKey(
        settings.AUTH_USER_MODEL, null=True, blank=True, on_delete=models.SET_NULL, related_name="+"
    )
    decided_at = models.DateTimeField(null=True, blank=True)
    cancelled_by = models.ForeignKey(
        settings.AUTH_USER_MODEL, null=True, blank=True, on_delete=models.SET_NULL, related_name="+"
    )
    cancelled_at = models.DateTimeField(null=True, blank=True)
    cancellation_reason = models.TextField(blank=True)
    completed_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        ordering = ["-start_datetime", "-id"]
        constraints = [
            models.CheckConstraint(
                condition=Q(end_datetime__gt=F("start_datetime")), name="booking_end_after_start"
            ),
            models.CheckConstraint(
                condition=Q(party_size__gte=1), name="booking_party_size_positive"
            ),
            ExclusionConstraint(
                name="booking_no_overlap_on_exclusive_amenity",
                expressions=[
                    (
                        DateTimeRange("start_datetime", "end_datetime", RangeBoundary()),
                        RangeOperators.OVERLAPS,
                    ),
                    ("amenity", RangeOperators.EQUAL),
                ],
                condition=Q(is_exclusive=True, status__in=BLOCKING_BOOKING_STATUSES),
            ),
        ]
        indexes = [
            models.Index(fields=["amenity", "status", "start_datetime"]),
            models.Index(fields=["booker", "status"]),
        ]

    def __str__(self) -> str:
        return f"Booking #{self.pk} {self.amenity_id} {self.start_datetime:%Y-%m-%d %H:%M}"
