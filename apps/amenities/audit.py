"""Actions this module writes in the audit journal."""

from enum import StrEnum


class AmenityAudit(StrEnum):
    CREATED = "amenity.created"
    DELETED = "amenity.deleted"
    UPDATED = "amenity.updated"


class BookingAudit(StrEnum):
    APPROVED = "booking.approved"
    CANCELLED = "booking.cancelled"
    CREATED = "booking.created"
    DELETED = "booking.deleted"
    REJECTED = "booking.rejected"
