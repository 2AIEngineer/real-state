"""Actions this module writes in the audit journal."""

from enum import StrEnum


class LibraryAudit(StrEnum):
    DOCUMENT_DELETED = "library.document_deleted"
    DOCUMENT_PUBLISHED = "library.document_published"
    DOCUMENT_UPDATED = "library.document_updated"
    FOLDER_CREATED = "library.folder_created"
    FOLDER_DELETED = "library.folder_deleted"
    FOLDER_UPDATED = "library.folder_updated"
