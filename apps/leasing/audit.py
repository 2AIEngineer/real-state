"""Actions this module writes in the audit journal."""

from enum import StrEnum


class LeaseAudit(StrEnum):
    CANCELLED = "lease.cancelled"
    COMPONENT_DELETED = "lease.component_deleted"
    COMPONENT_RECORDED = "lease.component_recorded"
    COMPONENT_UPDATED = "lease.component_updated"
    CREATED = "lease.created"
    DELETED = "lease.deleted"
    MEMBER_ADDED = "lease.member_added"
    MEMBER_LEFT = "lease.member_left"
    MEMBER_UPDATED = "lease.member_updated"
    TERMINATED = "lease.terminated"
    UPDATED = "lease.updated"
