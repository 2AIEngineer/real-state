from django.conf import settings
from django.core.validators import MaxValueValidator, MinValueValidator
from django.db import models
from django.db.models import Q

from apps.common.models import TimeStampedModel


class ServiceRequestCategory(models.TextChoices):
    PLUMBING = "plumbing", "Plumbing"
    ELECTRICITY = "electricity", "Electricity"
    HVAC = "hvac", "Heating / air conditioning"
    ELEVATOR = "elevator", "Elevator"
    CLEANING = "cleaning", "Cleaning"
    SECURITY = "security", "Security"
    COMMON_AREAS = "common_areas", "Common areas"
    NOISE = "noise", "Noise / neighbourhood"
    INFORMATION = "information", "Information request"
    SUGGESTION = "suggestion", "Comment or suggestion"
    OTHER = "other", "Other"


class ServiceRequestPriority(models.TextChoices):
    LOW = "LOW", "Low"
    MEDIUM = "MEDIUM", "Medium"
    HIGH = "HIGH", "High"
    URGENT = "URGENT", "Urgent"


class ServiceRequestStatus(models.TextChoices):
    OPEN = "OPEN", "Open (awaiting assignment)"
    IN_PROGRESS = "IN_PROGRESS", "In progress"
    RESOLVED = "RESOLVED", "Resolved (awaiting requester confirmation)"
    CLOSED = "CLOSED", "Closed"
    CANCELLED = "CANCELLED", "Cancelled"


class ServiceRequest(TimeStampedModel):
    property = models.ForeignKey(
        "properties.Property", on_delete=models.CASCADE, related_name="service_requests"
    )
    unit = models.ForeignKey(
        "properties.Unit",
        null=True,
        blank=True,
        on_delete=models.CASCADE,
        related_name="service_requests",
        help_text="Empty when the request concerns common areas.",
    )
    requester = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.PROTECT, related_name="service_requests"
    )
    title = models.CharField(max_length=200)
    description = models.TextField()
    category = models.CharField(
        max_length=16, choices=ServiceRequestCategory.choices, default=ServiceRequestCategory.OTHER
    )
    priority = models.CharField(
        max_length=8, choices=ServiceRequestPriority.choices, default=ServiceRequestPriority.MEDIUM
    )
    status = models.CharField(
        max_length=12, choices=ServiceRequestStatus.choices, default=ServiceRequestStatus.OPEN
    )
    current_round = models.PositiveIntegerField(default=1)
    resolved_at = models.DateTimeField(null=True, blank=True)
    closed_at = models.DateTimeField(null=True, blank=True)
    closed_by = models.ForeignKey(
        settings.AUTH_USER_MODEL, null=True, blank=True, on_delete=models.SET_NULL, related_name="+"
    )
    cancelled_at = models.DateTimeField(null=True, blank=True)
    cancellation_reason = models.TextField(blank=True)

    class Meta:
        ordering = ["-created_at", "-id"]
        indexes = [
            models.Index(fields=["property", "status"]),
            models.Index(fields=["requester", "status"]),
            models.Index(fields=["unit"]),
        ]
        constraints = [
            models.CheckConstraint(
                condition=Q(current_round__gte=1), name="service_request_round_positive"
            ),
        ]

    def __str__(self) -> str:
        return f"SR#{self.pk} {self.title}"


class RequesterNotice(models.TextChoices):
    DONE = "DONE", "Done"
    NOT_DONE = "NOT_DONE", "Not done"


class ServiceRequestAssignment(TimeStampedModel):
    """One resolver working on one resolution round of a request."""

    service_request = models.ForeignKey(
        ServiceRequest, on_delete=models.CASCADE, related_name="assignments"
    )
    resolver = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.PROTECT, related_name="service_assignments"
    )
    resolution_round = models.PositiveIntegerField(default=1)
    assigned_by = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.PROTECT, related_name="+"
    )
    is_resolved = models.BooleanField(default=False)
    resolved_at = models.DateTimeField(null=True, blank=True)
    resolution_note = models.TextField(blank=True)
    requester_notice = models.CharField(
        max_length=8, choices=RequesterNotice.choices, null=True, blank=True
    )
    requester_rating = models.PositiveSmallIntegerField(
        null=True, blank=True, validators=[MinValueValidator(1), MaxValueValidator(5)]
    )
    requester_comment = models.TextField(blank=True)
    feedback_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        ordering = ["service_request_id", "resolution_round", "id"]
        constraints = [
            models.UniqueConstraint(
                fields=["service_request", "resolver", "resolution_round"],
                name="unique_assignment_per_round",
            ),
            models.CheckConstraint(
                condition=Q(requester_rating__isnull=True)
                | Q(requester_rating__gte=1, requester_rating__lte=5),
                name="assignment_rating_1_to_5",
            ),
            models.CheckConstraint(
                condition=Q(is_resolved=False) | Q(resolved_at__isnull=False),
                name="assignment_resolved_has_timestamp",
            ),
        ]
        indexes = [models.Index(fields=["resolver", "is_resolved"])]

    def __str__(self) -> str:
        return f"SR#{self.service_request_id} round {self.resolution_round} -> {self.resolver_id}"
