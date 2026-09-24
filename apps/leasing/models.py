from django.conf import settings
from django.contrib.postgres.constraints import ExclusionConstraint
from django.contrib.postgres.fields import RangeBoundary, RangeOperators
from django.db import models
from django.db.models import F, Q

from apps.common.db import DateRange
from apps.common.models import TimeStampedModel


class LeaseStatus(models.TextChoices):
    ACTIVE = "ACTIVE", "Active"
    TERMINATED = "TERMINATED", "Terminated"
    CANCELLED = "CANCELLED", "Cancelled"


class LeaseTerminationReason(models.TextChoices):
    TERM_REACHED = "TERM_REACHED", "Contract term reached"
    TENANT_NOTICE = "TENANT_NOTICE", "Notice given by tenant"
    LANDLORD_NOTICE = "LANDLORD_NOTICE", "Notice given by landlord"
    MUTUAL_AGREEMENT = "MUTUAL_AGREEMENT", "Mutual agreement"
    BREACH = "BREACH", "Breach of contract"
    OTHER = "OTHER", "Other"


class Lease(TimeStampedModel):
    unit = models.ForeignKey("properties.Unit", on_delete=models.CASCADE, related_name="leases")
    start_date = models.DateField()
    end_date = models.DateField(
        null=True, blank=True, help_text="NULL = open-ended / tacit renewal."
    )
    status = models.CharField(
        max_length=16, choices=LeaseStatus.choices, default=LeaseStatus.ACTIVE
    )
    contract_reference = models.CharField(max_length=120, blank=True, null=True)
    notes = models.TextField(blank=True)

    terminated_on = models.DateField(null=True, blank=True)
    termination_reason = models.CharField(
        max_length=24, choices=LeaseTerminationReason.choices, blank=True
    )
    cancelled_at = models.DateTimeField(null=True, blank=True)
    cancellation_reason = models.TextField(blank=True)

    created_by = models.ForeignKey(
        settings.AUTH_USER_MODEL, null=True, on_delete=models.SET_NULL, related_name="+"
    )
    closed_by = models.ForeignKey(
        settings.AUTH_USER_MODEL, null=True, blank=True, on_delete=models.SET_NULL, related_name="+"
    )

    class Meta:
        ordering = ["-start_date", "-id"]
        constraints = [
            models.CheckConstraint(
                condition=Q(end_date__isnull=True) | Q(end_date__gte=F("start_date")),
                name="lease_end_after_start",
            ),
            models.CheckConstraint(
                condition=~Q(status=LeaseStatus.TERMINATED) | Q(terminated_on__isnull=False),
                name="lease_terminated_has_date",
            ),
            models.CheckConstraint(
                condition=~Q(status=LeaseStatus.CANCELLED) | Q(cancelled_at__isnull=False),
                name="lease_cancelled_has_timestamp",
            ),
            models.UniqueConstraint(
                fields=["contract_reference"],
                condition=Q(contract_reference__isnull=False) & ~Q(contract_reference=""),
                name="lease_contract_reference_unique",
            ),
            ExclusionConstraint(
                name="lease_no_overlapping_active_per_unit",
                expressions=[
                    (
                        DateRange(
                            "start_date",
                            "end_date",
                            RangeBoundary(inclusive_lower=True, inclusive_upper=True),
                        ),
                        RangeOperators.OVERLAPS,
                    ),
                    ("unit", RangeOperators.EQUAL),
                ],
                condition=Q(status=LeaseStatus.ACTIVE),
            ),
        ]
        indexes = [models.Index(fields=["unit", "status"])]

    @property
    def property_id(self) -> int:
        """The property the leased unit belongs to."""
        return self.unit.building.property_id

    def active_members(self) -> models.QuerySet:
        """The occupants who have not left."""
        return self.members.filter(left_at__isnull=True)

    def __str__(self) -> str:
        return f"Lease #{self.pk} unit={self.unit_id} ({self.status})"


class LeaseMember(TimeStampedModel):
    """Contractual occupant of a lease, with the lease-contextual extras.

    A member always has an application account. Departure never deletes the
    row: `left_at` is stamped so the occupancy history stays auditable.
    Identity/address proofs are `attachments.Attachment` rows attached to the
    member, of types `lease_member_identity` / `lease_member_address`.
    """

    lease = models.ForeignKey(Lease, on_delete=models.CASCADE, related_name="members")
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.PROTECT, related_name="lease_memberships"
    )
    joined_at = models.DateField()
    left_at = models.DateField(null=True, blank=True)
    is_signatory = models.BooleanField(default=False)

    emergency_contact_name = models.CharField(max_length=200, blank=True)
    emergency_contact_phone = models.CharField(max_length=32, blank=True)
    emergency_contact_relation = models.CharField(max_length=80, blank=True)
    vehicles_info = models.JSONField(default=list, blank=True)
    pets_info = models.JSONField(default=list, blank=True)

    added_by = models.ForeignKey(
        settings.AUTH_USER_MODEL, null=True, on_delete=models.SET_NULL, related_name="+"
    )
    departure_recorded_by = models.ForeignKey(
        settings.AUTH_USER_MODEL, null=True, blank=True, on_delete=models.SET_NULL, related_name="+"
    )

    class Meta:
        ordering = ["lease_id", "joined_at", "id"]
        constraints = [
            models.UniqueConstraint(fields=["lease", "user"], name="unique_lease_member"),
            models.CheckConstraint(
                condition=Q(left_at__isnull=True) | Q(left_at__gte=F("joined_at")),
                name="lease_member_left_after_joined",
            ),
        ]
        indexes = [
            models.Index(fields=["user", "left_at"]),
            models.Index(fields=["lease", "left_at"]),
        ]

    def __str__(self) -> str:
        return f"LeaseMember #{self.pk} lease={self.lease_id} user={self.user_id}"


class ComponentCondition(models.TextChoices):
    GOOD = "GOOD", "Good"
    BAD = "BAD", "Bad"


class CheckPhase(models.TextChoices):
    IN = "IN", "Move-in inspection"
    OUT = "OUT", "Move-out inspection"


class LeaseComponentState(TimeStampedModel):
    """State of one equipment/component recorded during a move-in/out inspection."""

    lease = models.ForeignKey(
        Lease, on_delete=models.CASCADE, related_name="lease_component_states"
    )
    name = models.CharField(max_length=120)
    description = models.TextField(blank=True)
    state = models.CharField(max_length=8, choices=ComponentCondition.choices)
    on_check = models.CharField(max_length=4, choices=CheckPhase.choices)
    on_check_date = models.DateField()
    recorded_by = models.ForeignKey(
        settings.AUTH_USER_MODEL, null=True, on_delete=models.SET_NULL, related_name="+"
    )

    class Meta:
        ordering = ["lease_id", "on_check", "name"]
        constraints = [
            models.UniqueConstraint(
                "lease",
                "on_check",
                models.functions.Lower("name"),
                name="unique_component_per_inspection",
            ),
        ]

    def __str__(self) -> str:
        return f"{self.name} [{self.on_check}] {self.state}"
