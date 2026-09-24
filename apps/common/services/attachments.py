"""Single entry point for storing, listing and deleting files.

A file is attached to an entity (`entity_type` + `entity_id`); the rules of
each type (formats, number of files, size) are in `apps.common.models`.
Reading needs no service: the serializer hands out the URL of the stored
file, which the client uses directly.
"""

from __future__ import annotations

import hashlib
import logging
import mimetypes
from collections.abc import Sequence
from pathlib import Path

import filetype
from django.core.files.uploadedfile import UploadedFile
from django.db import transaction
from django.db.models import QuerySet

from apps.common.exceptions import InvalidInput, NotFound
from apps.common.models import RULES, TEXT, Attachment, AttachmentRule

logger = logging.getLogger(__name__)

_EXTENSION_ALIASES = {"image/jpg": "image/jpeg"}


def _sniff_mime_type(upload: UploadedFile) -> str | None:
    """Detect the real type from content (magic numbers), never trust the client."""
    upload.seek(0)
    head = upload.read(8192)
    upload.seek(0)
    kind = filetype.guess(head)
    if kind is not None:
        return _EXTENSION_ALIASES.get(kind.mime, kind.mime)
    # Plain-text formats have no signature: accept them by extension only when
    # the content decodes as text.
    guessed, _ = mimetypes.guess_type(upload.name or "")
    if guessed in TEXT:
        try:
            head.decode("utf-8")
        except UnicodeDecodeError:
            return None
        return guessed
    return None


def _checksum(upload: UploadedFile) -> str:
    digest = hashlib.sha256()
    upload.seek(0)
    for chunk in upload.chunks():
        digest.update(chunk)
    upload.seek(0)
    return digest.hexdigest()


def _delete_stored_file_on_commit(storage_name: str, storage) -> None:
    def _delete() -> None:
        try:
            storage.delete(storage_name)
        except Exception:  # storage cleanup must never break a committed transaction
            logger.exception("Could not delete stored file %s", storage_name)

    transaction.on_commit(_delete)


class AttachmentService:
    @staticmethod
    def validate(
        files: Sequence[UploadedFile], rule: AttachmentRule, *, field: str = "files"
    ) -> list[str]:
        """Check sizes and formats against the rule; returns the sniffed MIME types."""
        detected: list[str] = []
        for upload in files:
            if upload.size == 0:
                raise InvalidInput(f"'{upload.name}' is empty.", field=field)
            if upload.size > rule.max_size_bytes:
                limit = rule.max_size_bytes // (1024 * 1024)
                raise InvalidInput(f"'{upload.name}' exceeds the {limit} MB limit.", field=field)
            mime = _sniff_mime_type(upload)
            if mime is None or mime not in rule.allowed_types:
                raise InvalidInput(
                    f"'{upload.name}' has an unsupported format. Allowed: {rule.describe_types()}.",
                    field=field,
                )
            detected.append(mime)
        return detected

    @staticmethod
    @transaction.atomic
    def attach(
        *,
        entity_type: str,
        entity_id: int,
        files: Sequence[UploadedFile],
        uploaded_by,
        field: str = "files",
    ) -> list[Attachment]:
        """Store `files` for the entity, following the rule of its type.

        A type holding one file replaces it; the others add files up to their
        maximum. Blobs are written before the transaction commits; if it rolls
        back they stay orphaned and are reclaimed by `purge_orphan_attachments`.
        """
        if not files:
            return []
        rule = RULES[entity_type]
        mime_types = AttachmentService.validate(files, rule, field=field)
        existing = Attachment.objects.filter(entity_type=entity_type, entity_id=entity_id)

        if rule.max_files == 1:
            if len(files) != 1:
                raise InvalidInput("Exactly one file is expected.", field=field)
            for previous in existing.select_for_update():
                AttachmentService.delete(attachment=previous)
            next_position = 0
        else:
            current = existing.count()
            if current + len(files) > rule.max_files:
                raise InvalidInput(
                    f"At most {rule.max_files} file(s) can be attached.", field=field
                )
            next_position = current

        created: list[Attachment] = []
        for offset, (upload, mime) in enumerate(zip(files, mime_types, strict=True)):
            attachment = Attachment(
                entity_type=entity_type,
                entity_id=entity_id,
                mime_type=mime,
                size=upload.size,
                original_filename=Path(upload.name or "file").name[:255],
                checksum_sha256=_checksum(upload),
                position=next_position + offset,
                uploaded_by=uploaded_by,
            )
            attachment.file.save(upload.name or "file", upload, save=False)
            attachment.save()
            created.append(attachment)
        return created

    @staticmethod
    @transaction.atomic
    def attach_one(
        *, entity_type: str, entity_id: int, upload: UploadedFile, uploaded_by
    ) -> Attachment:
        """Fill the single slot of an entity (a logo, a proof of identity…), replacing its file."""
        (attachment,) = AttachmentService.attach(
            entity_type=entity_type,
            entity_id=entity_id,
            files=[upload],
            uploaded_by=uploaded_by,
            field="file",
        )
        return attachment

    @staticmethod
    def list_for_entity(entity_type: str, entity_id: int) -> QuerySet[Attachment]:
        return Attachment.objects.filter(entity_type=entity_type, entity_id=entity_id)

    @staticmethod
    def list_for_entities(entity_type: str, entity_ids) -> QuerySet[Attachment]:
        """Files of several entities of one type, in a single query (list pages)."""
        return Attachment.objects.filter(entity_type=entity_type, entity_id__in=entity_ids)

    @staticmethod
    def count(entity_type: str, entity_id: int) -> int:
        return AttachmentService.list_for_entity(entity_type, entity_id).count()

    @staticmethod
    def get(*, entity_type: str, entity_id: int, attachment_id: int) -> Attachment:
        attachment = (
            AttachmentService.list_for_entity(entity_type, entity_id)
            .filter(pk=attachment_id)
            .first()
        )
        if attachment is None:
            raise NotFound("Attachment not found.")
        return attachment

    @staticmethod
    @transaction.atomic
    def delete(*, attachment: Attachment) -> None:
        name, storage = attachment.file.name, attachment.file.storage
        attachment.delete()
        _delete_stored_file_on_commit(name, storage)

    @staticmethod
    @transaction.atomic
    def delete_for_entity(entity_type: str, entity_id: int) -> None:
        for attachment in AttachmentService.list_for_entity(entity_type, entity_id):
            AttachmentService.delete(attachment=attachment)
