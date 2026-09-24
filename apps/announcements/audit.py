"""Actions this module writes in the audit journal."""

from enum import StrEnum


class AnnouncementAudit(StrEnum):
    ARCHIVED = "announcement.archived"
    DELETED = "announcement.deleted"
    PUBLISHED = "announcement.published"
    UPDATED = "announcement.updated"
