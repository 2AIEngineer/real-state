from django.conf import settings
from django.db import models
from django.db.models import F, Q

from apps.common.models import TimeStampedModel


class VisitStatus(models.TextChoices):
    ARRIVED = "ARRIVED", "On site"
    LEFT = "LEFT", "Left"
    DENIED = "DENIED", "Entry denied"


class Visitor(TimeStampedModel):
    unit = models.ForeignKey("properties.Unit", on_delete=models.CASCADE, related_name="visitors")
    property = models.ForeignKey(
        "properties.Property", on_delete=models.CASCADE, related_name="visitors"
    )
    first_name = models.CharField(max_length=120)
    last_name = models.CharField(max_length=120)
    phone = models.CharField(max_length=32, blank=True)
    visit_reason = models.CharField(max_length=200, blank=True)
    vehicle_plate = models.CharField(max_length=32, blank=True)
    status = models.CharField(max_length=8, choices=VisitStatus.choices)
    arrived_at = models.DateTimeField(null=True, blank=True)
    left_at = models.DateTimeField(null=True, blank=True)
    denial_reason = models.TextField(blank=True)
    notes = models.TextField(blank=True)
    registered_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="+",
    )
    checked_out_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name="+",
    )

    class Meta:
        ordering = ["-created_at", "-id"]
        constraints = [
            models.CheckConstraint(
                condition=(
                    Q(status=VisitStatus.ARRIVED)
                    & Q(arrived_at__isnull=False)
                    & Q(left_at__isnull=True)
                )
                | (
                    Q(status=VisitStatus.LEFT)
                    & Q(arrived_at__isnull=False)
                    & Q(left_at__gte=F("arrived_at"))
                )
                | (
                    Q(status=VisitStatus.DENIED)
                    & Q(arrived_at__isnull=True)
                    & Q(left_at__isnull=True)
                ),
                name="visitor_status_timestamps_consistent",
            ),
        ]
        indexes = [
            models.Index(fields=["property", "status", "-created_at"]),
            models.Index(fields=["unit", "-created_at"]),
        ]

    def __str__(self) -> str:
        return f"{self.first_name} {self.last_name} → unit {self.unit_id}"
