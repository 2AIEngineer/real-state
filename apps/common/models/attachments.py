"""A stored file, attached to any entity: its rules live in `apps.common.attachments.rules`."""

from __future__ import annotations

import secrets

from django.conf import settings
from django.db import models
from django.db.models import Q
from django.utils import timezone

from apps.common.attachments.rules import EXTENSIONS, SINGLE_FILE_TYPES, EntityType


def attachment_upload_to(instance: Attachment, filename: str) -> str:
    """A random name ending with the extension of the detected format.

    Neither the client's file name nor its extension reaches the storage: the
    original name is kept in the row only.
    """
    extension = EXTENSIONS.get(instance.mime_type, "")
    now = timezone.now()
    return f"attachments/{instance.entity_type}/{now:%Y/%m}/{secrets.token_hex(16)}{extension}"


class Attachment(models.Model):
    """A stored file, attached to one entity: `entity_type` + `entity_id`."""

    entity_type = models.CharField(max_length=40, choices=EntityType.choices)
    entity_id = models.PositiveBigIntegerField()

    file = models.FileField(upload_to=attachment_upload_to, max_length=255)
    mime_type = models.CharField(max_length=127)
    size = models.PositiveBigIntegerField(help_text="Bytes.")
    original_filename = models.CharField(max_length=255)
    checksum_sha256 = models.CharField(max_length=64)
    position = models.PositiveSmallIntegerField(default=0)

    uploaded_by = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.PROTECT, related_name="uploaded_attachments"
    )
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["position", "created_at", "id"]
        indexes = [models.Index(fields=["entity_type", "entity_id"], name="attachment_entity_idx")]
        constraints = [
            models.UniqueConstraint(
                fields=["entity_type", "entity_id"],
                condition=Q(entity_type__in=SINGLE_FILE_TYPES),
                name="attachment_single_file_per_entity",
            ),
            models.CheckConstraint(condition=Q(size__gt=0), name="attachment_size_positive"),
        ]

    def __str__(self) -> str:
        return f"{self.original_filename} ({self.mime_type})"
