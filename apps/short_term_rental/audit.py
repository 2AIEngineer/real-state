"""Actions this module writes in the audit journal."""

from enum import StrEnum


class ShortTermRentalAudit(StrEnum):
    CANCELLED = "short_term_rental.cancelled"
    CHECKED_IN = "short_term_rental.checked_in"
    COMPLETED = "short_term_rental.completed"
    DECLARED = "short_term_rental.declared"
    DELETED = "short_term_rental.deleted"
    MEMBER_ADDED = "short_term_rental.member_added"
    MEMBER_REMOVED = "short_term_rental.member_removed"
    MEMBER_UPDATED = "short_term_rental.member_updated"
    RESCHEDULED = "short_term_rental.rescheduled"
