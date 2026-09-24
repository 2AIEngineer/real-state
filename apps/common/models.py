"""Base classes shared by every module, and the tables that belong to no domain.

`TimeStampedModel` and `ArchivableModel` are inherited across the project.
`Attachment` and `AuditLogEntry` are real tables: a file can be attached to any
entity and any sensitive action is journaled, so neither belongs to a business
module.

Every file belongs to one entity, named by its type and its id (`EntityType`).
The type also says which slot of the record the file fills (a lease member has
a proof of identity and a proof of address: two types). For each type, `RULES`
fixes the accepted formats, the maximum number of files and the maximum size of
one file. When the maximum is 1, a new upload replaces the current file.
"""

from __future__ import annotations

import secrets
from dataclasses import dataclass
from pathlib import Path

from django.conf import settings
from django.contrib.contenttypes.fields import GenericForeignKey
from django.contrib.contenttypes.models import ContentType
from django.db import models
from django.db.models import Q
from django.utils import timezone

# ------------------------------------------------------------------ base classes


class TimeStampedModel(models.Model):
    created_at = models.DateTimeField(auto_now_add=True, db_index=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        abstract = True


class ArchivableQuerySet(models.QuerySet):
    def not_archived(self):
        """Rows still on air (not archived)."""
        return self.filter(archived_at__isnull=True)


class ArchivableModel(models.Model):
    """Broadcasts that can be taken off air without being erased.

    Archiving keeps the row: the audit trail stays, and the people already
    notified can be told it was retracted. Erasing it for good is a separate,
    explicitly named operation (`delete`). Queries opt in with
    `.live()` rather than going through a hidden manager.
    """

    archived_at = models.DateTimeField(null=True, blank=True, db_index=True)
    archived_by = models.ForeignKey(
        "accounts.User",
        null=True,
        blank=True,
        on_delete=models.PROTECT,
        related_name="+",
    )

    objects = ArchivableQuerySet.as_manager()

    class Meta:
        abstract = True


# ------------------------------------------------------------------ attachment rules


MB = 1024 * 1024

IMAGES = frozenset({"image/jpeg", "image/png", "image/webp", "image/heic"})
PDF = frozenset({"application/pdf"})
OFFICE = frozenset(
    {
        "application/msword",
        "application/vnd.openxmlformats-officedocument.wordprocessingml.document",
        "application/vnd.ms-excel",
        "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        "application/vnd.ms-powerpoint",
        "application/vnd.openxmlformats-officedocument.presentationml.presentation",
    }
)
TEXT = frozenset({"text/csv", "text/plain"})
DOCUMENTS = IMAGES | PDF | OFFICE | TEXT
PHOTOS_AND_PDF = IMAGES | PDF


class EntityType(models.TextChoices):
    SYNDICAT_LOGO = "syndicat_logo", "Syndicat logo"
    PROPERTY_LOGO = "property_logo", "Property logo"
    ANNOUNCEMENT = "announcement", "Announcement files"
    EVENT = "event", "Event files"
    SURVEY = "survey", "Survey files"
    LIBRARY_DOCUMENT = "library_document", "Library document file"
    AMENITY = "amenity", "Amenity images"
    PRODUCT = "product", "Store product images"
    MARKETPLACE_LISTING = "marketplace_listing", "Marketplace listing images"
    SERVICE_REQUEST = "service_request", "Service request files"
    SERVICE_REQUEST_RESOLUTION = (
        "service_request_resolution",
        "Resolution evidence of a service request round",
    )
    WORK_ORDER = "work_order", "Work order files"
    LEASE_COMPONENT_STATE = "lease_component_state", "Inspection files"
    LEASE_MEMBER_IDENTITY = "lease_member_identity", "Lease member proof of identity"
    LEASE_MEMBER_ADDRESS = "lease_member_address", "Lease member proof of address"
    VISITOR_ID_CARD = "visitor_id_card", "Visitor identity card"
    SHORT_TERM_RENTAL_MEMBER_ID_CARD = (
        "short_term_rental_member_id_card",
        "Short-term rental member identity card",
    )
    CHAT_MESSAGE = "chat_message", "Chat message file"


@dataclass(frozen=True)
class AttachmentRule:
    allowed_types: frozenset[str]
    max_files: int
    max_size_bytes: int

    def describe_types(self) -> str:
        return ", ".join(sorted(t.split("/")[-1] for t in self.allowed_types))


RULES: dict[str, AttachmentRule] = {
    EntityType.SYNDICAT_LOGO: AttachmentRule(IMAGES, max_files=1, max_size_bytes=10 * MB),
    EntityType.PROPERTY_LOGO: AttachmentRule(IMAGES, max_files=1, max_size_bytes=10 * MB),
    EntityType.ANNOUNCEMENT: AttachmentRule(DOCUMENTS, max_files=30, max_size_bytes=25 * MB),
    EntityType.EVENT: AttachmentRule(DOCUMENTS, max_files=30, max_size_bytes=25 * MB),
    EntityType.SURVEY: AttachmentRule(DOCUMENTS, max_files=30, max_size_bytes=25 * MB),
    EntityType.LIBRARY_DOCUMENT: AttachmentRule(DOCUMENTS, max_files=1, max_size_bytes=25 * MB),
    EntityType.AMENITY: AttachmentRule(IMAGES, max_files=20, max_size_bytes=10 * MB),
    EntityType.PRODUCT: AttachmentRule(IMAGES, max_files=20, max_size_bytes=10 * MB),
    EntityType.MARKETPLACE_LISTING: AttachmentRule(IMAGES, max_files=20, max_size_bytes=10 * MB),
    EntityType.SERVICE_REQUEST: AttachmentRule(
        PHOTOS_AND_PDF, max_files=30, max_size_bytes=20 * MB
    ),
    EntityType.SERVICE_REQUEST_RESOLUTION: AttachmentRule(
        PHOTOS_AND_PDF, max_files=30, max_size_bytes=20 * MB
    ),
    EntityType.WORK_ORDER: AttachmentRule(PHOTOS_AND_PDF, max_files=30, max_size_bytes=20 * MB),
    EntityType.LEASE_COMPONENT_STATE: AttachmentRule(
        PHOTOS_AND_PDF, max_files=30, max_size_bytes=20 * MB
    ),
    EntityType.LEASE_MEMBER_IDENTITY: AttachmentRule(
        PHOTOS_AND_PDF, max_files=1, max_size_bytes=10 * MB
    ),
    EntityType.LEASE_MEMBER_ADDRESS: AttachmentRule(
        PHOTOS_AND_PDF, max_files=1, max_size_bytes=10 * MB
    ),
    EntityType.VISITOR_ID_CARD: AttachmentRule(PHOTOS_AND_PDF, max_files=1, max_size_bytes=10 * MB),
    EntityType.SHORT_TERM_RENTAL_MEMBER_ID_CARD: AttachmentRule(
        PHOTOS_AND_PDF, max_files=1, max_size_bytes=10 * MB
    ),
    # One file per chat message: png, jpeg or pdf.
    EntityType.CHAT_MESSAGE: AttachmentRule(
        frozenset({"image/png", "image/jpeg", "application/pdf"}),
        max_files=1,
        max_size_bytes=10 * MB,
    ),
}

# Types holding a single file (a new upload replaces it).
SINGLE_FILE_TYPES: tuple[str, ...] = tuple(
    sorted(t for t, rule in RULES.items() if rule.max_files == 1)
)


# ------------------------------------------------------------------ attachments


def attachment_upload_to(instance: Attachment, filename: str) -> str:
    # The stored name is random: the original name is kept in the row only,
    # so user-provided names never reach the storage layer.
    suffix = Path(filename).suffix.lower()[:10]
    now = timezone.now()
    return f"attachments/{instance.entity_type}/{now:%Y/%m}/{secrets.token_hex(16)}{suffix}"


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


# ------------------------------------------------------------------ audit journal


class AuditLogEntry(models.Model):
    """Append-only journal of sensitive actions."""

    actor = models.ForeignKey(
        settings.AUTH_USER_MODEL, null=True, on_delete=models.SET_NULL, related_name="audit_entries"
    )
    action = models.CharField(max_length=80)
    content_type = models.ForeignKey(
        ContentType, null=True, on_delete=models.SET_NULL, related_name="+"
    )
    object_id = models.PositiveBigIntegerField(null=True)
    target = GenericForeignKey("content_type", "object_id")
    object_repr = models.CharField(max_length=255, blank=True)
    property = models.ForeignKey(
        "properties.Property", null=True, blank=True, on_delete=models.SET_NULL, related_name="+"
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
