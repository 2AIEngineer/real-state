from django.conf import settings
from django.db import models
from django.db.models import F, Q

from apps.common.models import TimeStampedModel


class WorkOrderCategory(models.TextChoices):
    PREVENTIVE = "preventive", "Preventive maintenance"
    CORRECTIVE = "corrective", "Corrective maintenance"
    INSPECTION = "inspection", "Inspection"
    CLEANING = "cleaning", "Cleaning"
    RENOVATION = "renovation", "Renovation"
    OTHER = "other", "Other"


class WorkOrderPriority(models.TextChoices):
    LOW = "LOW", "Low"
    MEDIUM = "MEDIUM", "Medium"
    HIGH = "HIGH", "High"
    URGENT = "URGENT", "Urgent"


class WorkOrderStatus(models.TextChoices):
    OPEN = "OPEN", "Open"
    IN_PROGRESS = "IN_PROGRESS", "In progress"
    ON_HOLD = "ON_HOLD", "On hold"
    COMPLETED = "COMPLETED", "Completed"
    CANCELLED = "CANCELLED", "Cancelled"


class WorkOrder(TimeStampedModel):
    """Internal maintenance job on a property, one of its buildings or a unit.

    `property` is always set (filtering, permissions); `building` and
    `unit` narrow the target. The service guarantees the chain is consistent
    (unit ∈ building ∈ property).
    """

    property = models.ForeignKey(
        "properties.Property", on_delete=models.CASCADE, related_name="work_orders"
    )
    building = models.ForeignKey(
        "properties.Building",
        null=True,
        blank=True,
        on_delete=models.CASCADE,
        related_name="work_orders",
    )
    unit = models.ForeignKey(
        "properties.Unit",
        null=True,
        blank=True,
        on_delete=models.CASCADE,
        related_name="work_orders",
    )
    service_request = models.ForeignKey(
        "service_requests.ServiceRequest",
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name="work_orders",
    )
    title = models.CharField(max_length=200)
    description = models.TextField(blank=True)
    category = models.CharField(
        max_length=16,
        choices=WorkOrderCategory.choices,
        default=WorkOrderCategory.CORRECTIVE,
    )
    priority = models.CharField(
        max_length=8,
        choices=WorkOrderPriority.choices,
        default=WorkOrderPriority.MEDIUM,
    )
    status = models.CharField(
        max_length=12, choices=WorkOrderStatus.choices, default=WorkOrderStatus.OPEN
    )
    assignee = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name="work_orders",
    )
    scheduled_start = models.DateTimeField(null=True, blank=True)
    scheduled_end = models.DateTimeField(null=True, blank=True)
    due_date = models.DateField(null=True, blank=True)
    started_at = models.DateTimeField(null=True, blank=True)
    completed_at = models.DateTimeField(null=True, blank=True)
    completion_note = models.TextField(blank=True)
    cancelled_at = models.DateTimeField(null=True, blank=True)
    cancellation_reason = models.TextField(blank=True)
    created_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="+",
    )

    class Meta:
        ordering = ["-created_at", "-id"]
        constraints = [
            models.CheckConstraint(
                condition=Q(unit__isnull=True) | Q(building__isnull=False),
                name="work_order_unit_needs_building",
            ),
            models.CheckConstraint(
                condition=Q(scheduled_start__isnull=True)
                | Q(scheduled_end__isnull=True)
                | Q(scheduled_end__gt=F("scheduled_start")),
                name="work_order_schedule_ordered",
            ),
        ]
        indexes = [
            models.Index(fields=["property", "status"]),
            models.Index(fields=["assignee", "status"]),
        ]

    def __str__(self) -> str:
        return f"WO#{self.pk} {self.title}"
