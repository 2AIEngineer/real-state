"""Tables and abstract bases that belong to no business domain.

`TimeStampedModel` and `ArchivableModel` are inherited across the project.
`Attachment` and `AuditLogEntry` are real tables: a file can be attached to any
entity and any sensitive action is journaled, so neither belongs to a module.
`IdempotencyKey` remembers the outcome of a POST so that its retries do not repeat it.
"""

from apps.common.models.attachments import Attachment, attachment_upload_to
from apps.common.models.audit import AuditLogEntry
from apps.common.models.base import ArchivableModel, ArchivableQuerySet, TimeStampedModel
from apps.common.models.idempotency import IdempotencyKey

__all__ = [
    "ArchivableModel",
    "ArchivableQuerySet",
    "Attachment",
    "AuditLogEntry",
    "IdempotencyKey",
    "TimeStampedModel",
    "attachment_upload_to",
]
