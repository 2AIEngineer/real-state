from django.conf import settings
from django.contrib.postgres.fields import ArrayField
from django.db import models
from django.db.models import F, Q

from apps.accounts.enums import PropertyRole
from apps.common.models import ArchivableModel, TimeStampedModel


class EventStatus(models.TextChoices):
    SCHEDULED = "SCHEDULED", "Scheduled"
    CANCELLED = "CANCELLED", "Cancelled"
    COMPLETED = "COMPLETED", "Completed"


class Event(TimeStampedModel, ArchivableModel):
    property = models.ForeignKey(
        "properties.Property", on_delete=models.CASCADE, related_name="events"
    )
    building = models.ForeignKey(
        "properties.Building",
        null=True,
        blank=True,
        on_delete=models.CASCADE,
        related_name="events",
    )
    title = models.CharField(max_length=200)
    description = models.TextField(blank=True)
    location = models.CharField(max_length=200, blank=True)
    start_at = models.DateTimeField()
    end_at = models.DateTimeField()
    status = models.CharField(
        max_length=12, choices=EventStatus.choices, default=EventStatus.SCHEDULED
    )
    target_roles = ArrayField(models.CharField(max_length=16, choices=PropertyRole.choices))
    cancelled_at = models.DateTimeField(null=True, blank=True)
    cancellation_reason = models.TextField(blank=True)
    completed_at = models.DateTimeField(null=True, blank=True)
    created_by = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True, blank=True, related_name="+"
    )

    class Meta:
        ordering = ["start_at", "id"]
        constraints = [
            models.CheckConstraint(
                condition=Q(end_at__gt=F("start_at")), name="event_end_after_start"
            ),
            models.CheckConstraint(
                condition=Q(target_roles__len__gt=0), name="event_has_target_roles"
            ),
            models.CheckConstraint(
                condition=~Q(status=EventStatus.CANCELLED) | Q(cancelled_at__isnull=False),
                name="event_cancelled_has_timestamp",
            ),
        ]
        indexes = [models.Index(fields=["property", "status", "start_at"])]

    def __str__(self) -> str:
        return self.title
