"""Actions this module writes in the audit journal."""

from enum import StrEnum


class EventAudit(StrEnum):
    ARCHIVED = "event.archived"
    CANCELLED = "event.cancelled"
    CREATED = "event.created"
    DELETED = "event.deleted"
    UPDATED = "event.updated"
