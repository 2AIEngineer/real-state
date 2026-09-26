"""The append-only journal of sensitive actions."""

from django.conf import settings
from django.contrib.contenttypes.fields import GenericForeignKey
from django.contrib.contenttypes.models import ContentType
from django.db import models


class AuditLogEntry(models.Model):
    """Append-only journal of sensitive actions."""

    actor = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        null=True,
        on_delete=models.SET_NULL,
        related_name="audit_entries",
    )
    action = models.CharField(max_length=80)
    content_type = models.ForeignKey(
        ContentType, null=True, on_delete=models.SET_NULL, related_name="+"
    )
    object_id = models.PositiveBigIntegerField(null=True)
    target = GenericForeignKey("content_type", "object_id")
    object_repr = models.CharField(max_length=255, blank=True)
    property = models.ForeignKey(
        "properties.Property",
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name="+",
    )
    metadata = models.JSONField(default=dict, blank=True)
    created_at = models.DateTimeField(auto_now_add=True, db_index=True)

    class Meta:
        ordering = ["-created_at", "-id"]
        indexes = [
            models.Index(fields=["content_type", "object_id"]),
            models.Index(fields=["actor", "created_at"]),
            models.Index(fields=["property", "created_at"]),
            models.Index(fields=["action"]),
        ]

    def __str__(self) -> str:
        return f"{self.action} by {self.actor_id}"
