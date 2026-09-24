from django.conf import settings
from django.contrib.postgres.constraints import ExclusionConstraint
from django.contrib.postgres.fields import RangeBoundary, RangeOperators
from django.db import models
from django.db.models import F, Q

from apps.accounts.enums import Gender
from apps.common.db import DateRange
from apps.common.models import TimeStampedModel


class ShortTermRentalStatus(models.TextChoices):
    SCHEDULED = "SCHEDULED", "Scheduled"
    CHECKED_IN = "CHECKED_IN", "Members on site"
    COMPLETED = "COMPLETED", "Completed"
    CANCELLED = "CANCELLED", "Cancelled"


BLOCKING_SHORT_TERM_RENTAL_STATUSES = (
    ShortTermRentalStatus.SCHEDULED,
    ShortTermRentalStatus.CHECKED_IN,
)


class InitiatorCapacity(models.TextChoices):
    """The right under which the rental was declared (drives bounding rules)."""

    TENANT = "TENANT", "Tenant of the unit"
    OWNER = "OWNER", "Owner of the unit"
    MANAGEMENT = "MANAGEMENT", "Property management"


class ShortTermRental(TimeStampedModel):
    unit = models.ForeignKey(
        "properties.Unit", on_delete=models.CASCADE, related_name="short_term_rentals"
    )
    initiated_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.PROTECT,
        related_name="initiated_short_term_rentals",
    )
    initiator_capacity = models.CharField(max_length=12, choices=InitiatorCapacity.choices)
    lease = models.ForeignKey(
        "leasing.Lease",
        null=True,
        blank=True,
        on_delete=models.CASCADE,
        related_name="short_term_rentals",
        help_text="Lease bounding the rental when declared by a tenant.",
    )
    checkin_date = models.DateField()
    checkout_date = models.DateField()
    status = models.CharField(
        max_length=12,
        choices=ShortTermRentalStatus.choices,
        default=ShortTermRentalStatus.SCHEDULED,
    )
    primary_member = models.ForeignKey(
        "ShortTermRentalMember", null=True, blank=True, on_delete=models.SET_NULL, related_name="+"
    )
    notes = models.TextField(blank=True)
    checked_in_at = models.DateTimeField(null=True, blank=True)
    completed_at = models.DateTimeField(null=True, blank=True)
    cancelled_at = models.DateTimeField(null=True, blank=True)
    cancelled_by = models.ForeignKey(
        settings.AUTH_USER_MODEL, null=True, blank=True, on_delete=models.SET_NULL, related_name="+"
    )
    cancellation_reason = models.TextField(blank=True)

    class Meta:
        ordering = ["-checkin_date", "-id"]
        constraints = [
            models.CheckConstraint(
                condition=Q(checkout_date__gt=F("checkin_date")),
                name="short_term_rental_checkout_after_checkin",
            ),
            models.CheckConstraint(
                condition=~Q(initiator_capacity=InitiatorCapacity.TENANT) | Q(lease__isnull=False),
                name="short_term_rental_tenant_has_lease",
            ),
            # Checkout day may be the next check-in day: half-open range.
            ExclusionConstraint(
                name="short_term_rental_no_overlap_per_unit",
                expressions=[
                    (
                        DateRange("checkin_date", "checkout_date", RangeBoundary()),
                        RangeOperators.OVERLAPS,
                    ),
                    ("unit", RangeOperators.EQUAL),
                ],
                condition=Q(status__in=BLOCKING_SHORT_TERM_RENTAL_STATUSES),
            ),
        ]
        indexes = [
            models.Index(fields=["unit", "status"]),
            models.Index(fields=["initiated_by", "status"]),
        ]

    @property
    def property_id(self) -> int:
        """The property the rented unit belongs to."""
        return self.unit.building.property_id

    def __str__(self) -> str:
        return f"Short-term rental #{self.pk} unit={self.unit_id} {self.checkin_date}→{self.checkout_date}"


class ShortTermRentalMember(TimeStampedModel):
    """Member of a short rental. External person: never an application account."""

    short_term_rental = models.ForeignKey(
        ShortTermRental, on_delete=models.CASCADE, related_name="members"
    )
    first_name = models.CharField(max_length=120)
    last_name = models.CharField(max_length=120)
    gender = models.CharField(max_length=12, choices=Gender.choices, default=Gender.UNDISCLOSED)
    date_of_birth = models.DateField(null=True, blank=True)
    nationality = models.CharField(max_length=80, blank=True)
    id_document_number = models.CharField(max_length=64, blank=True)
    phone = models.CharField(max_length=32, blank=True)
    email = models.EmailField(blank=True)

    class Meta:
        ordering = ["short_term_rental_id", "id"]

    def __str__(self) -> str:
        return f"{self.first_name} {self.last_name}"
