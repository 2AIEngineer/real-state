"""Tables and abstract bases that belong to no business domain.

`TimeStampedModel` and `ArchivableModel` are inherited across the project.
`Attachment` and `AuditLogEntry` are real tables: a file can be attached to any
entity and any sensitive action is journaled, so neither belongs to a module.
"""

from apps.common.models.attachments import Attachment, attachment_upload_to
from apps.common.models.audit import AuditLogEntry
from apps.common.models.base import ArchivableModel, ArchivableQuerySet, TimeStampedModel

__all__ = [
    "ArchivableModel",
    "ArchivableQuerySet",
    "Attachment",
    "AuditLogEntry",
    "TimeStampedModel",
    "attachment_upload_to",
]
