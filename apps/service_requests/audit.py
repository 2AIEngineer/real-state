"""Actions this module writes in the audit journal."""

from enum import StrEnum


class ServiceRequestAudit(StrEnum):
    ASSIGNED = "service_request.assigned"
    ASSIGNMENT_RESOLVED = "service_request.assignment_resolved"
    CANCELLED = "service_request.cancelled"
    CLOSED = "service_request.closed"
    CONFIRMED = "service_request.confirmed"
    DELETED = "service_request.deleted"
    REOPENED = "service_request.reopened"
    SUBMITTED = "service_request.submitted"
