from django.conf import settings
from django.contrib.postgres.fields import ArrayField
from django.db import models
from django.db.models import F, Q

from apps.accounts.enums import PropertyRole
from apps.common.models import ArchivableModel, TimeStampedModel


class AnnouncementCategory(models.TextChoices):
    GENERAL = "general", "General information"
    MEETING = "meeting", "Meetings & assemblies"
    MAINTENANCE = "maintenance", "Maintenance work"
    SECURITY = "security", "Security"
    RULES = "rules", "Rules & policies"
    FINANCIAL = "financial", "Financial information"
    COMMUNITY = "community", "Community life"
    EMERGENCY = "emergency", "Emergency"


class AnnouncementPriority(models.TextChoices):
    NORMAL = "normal", "Normal"
    IMPORTANT = "important", "Important"
    URGENT = "urgent", "Urgent"


class Announcement(TimeStampedModel, ArchivableModel):
    property = models.ForeignKey(
        "properties.Property", on_delete=models.PROTECT, related_name="announcements"
    )
    building = models.ForeignKey(
        "properties.Building",
        null=True,
        blank=True,
        on_delete=models.PROTECT,
        related_name="announcements",
        help_text="Optional narrowing of the target roles to one building.",
    )
    title = models.CharField(max_length=200)
    body = models.TextField()
    category = models.CharField(
        max_length=16, choices=AnnouncementCategory.choices, default=AnnouncementCategory.GENERAL
    )
    priority = models.CharField(
        max_length=10, choices=AnnouncementPriority.choices, default=AnnouncementPriority.NORMAL
    )
    target_roles = ArrayField(models.CharField(max_length=16, choices=PropertyRole.choices))
    published_at = models.DateTimeField()
    expires_at = models.DateTimeField(null=True, blank=True)
    created_by = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.PROTECT, related_name="+"
    )

    class Meta:
        ordering = ["-published_at", "-id"]
        constraints = [
            models.CheckConstraint(
                condition=Q(target_roles__len__gt=0), name="announcement_has_target_roles"
            ),
            models.CheckConstraint(
                condition=Q(expires_at__isnull=True) | Q(expires_at__gt=F("published_at")),
                name="announcement_expires_after_publication",
            ),
        ]
        indexes = [models.Index(fields=["property", "archived_at", "-published_at"])]

    def __str__(self) -> str:
        return self.title
