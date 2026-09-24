"""What the request and its rounds share: the lock, and who works the current round."""

from __future__ import annotations

from django.db.models import QuerySet

from apps.service_requests.models import (
    ServiceRequest,
    ServiceRequestAssignment,
    ServiceRequestStatus,
)

OPEN_STATES = (ServiceRequestStatus.OPEN, ServiceRequestStatus.IN_PROGRESS)


def lock(sr: ServiceRequest) -> ServiceRequest:
    """The request, re-read under a row lock: transitions never race."""
    return (
        ServiceRequest.objects.select_for_update(of=("self",))
        .select_related("property", "requester")
        .get(pk=sr.pk)
    )


def current_assignments(sr: ServiceRequest) -> QuerySet[ServiceRequestAssignment]:
    return sr.assignments.filter(resolution_round=sr.current_round)


def current_resolvers(sr: ServiceRequest) -> list:
    return [a.resolver for a in current_assignments(sr).select_related("resolver")]
