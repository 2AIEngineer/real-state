"""Actions this module writes in the audit journal."""

from enum import StrEnum


class VisitorAudit(StrEnum):
    ARRIVED = "visitor.arrived"
    DELETED = "visitor.deleted"
    DENIED = "visitor.denied"
    LEFT = "visitor.left"
    UPDATED = "visitor.updated"
