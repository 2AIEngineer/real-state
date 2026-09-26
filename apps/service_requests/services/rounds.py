"""The resolution rounds of a request: assigning resolvers, resolving, the requester's verdict.

A round is the work of the resolvers assigned since the request was last
(re)opened. When every resolver of the round has resolved, the request is
RESOLVED; the requester then closes it (DONE) or opens a new round (NOT_DONE).
"""

from __future__ import annotations

from dataclasses import dataclass

from django.db import transaction
from django.db.models import QuerySet
from django.utils import timezone

from apps.accounts.services.authorization import AccessService
from apps.common.attachments.rules import EntityType
from apps.common.attachments.service import AttachmentService
from apps.common.exceptions import (
    BusinessRuleViolation,
    InvalidInput,
    InvalidTransition,
    NotFound,
    PermissionDenied,
)
from apps.common.services.audit import AuditService
from apps.service_requests import notices
from apps.service_requests.audit import ServiceRequestAudit
from apps.service_requests.models import (
    RequesterNotice,
    ServiceRequest,
    ServiceRequestAssignment,
    ServiceRequestStatus,
)
from apps.service_requests.policies import ServiceRequestPolicy
from apps.service_requests.services._state import (
    OPEN_STATES,
    current_assignments,
    current_resolvers,
    lock,
)


@dataclass(frozen=True)
class Feedback:
    notice: str
    rating: int | None = None
    comment: str = ""


class RoundService:
    @staticmethod
    def assignments(*, actor, sr: ServiceRequest) -> QuerySet[ServiceRequestAssignment]:
        if not ServiceRequestPolicy.can_view(actor, sr):
            raise NotFound("Service request not found.")
        return sr.assignments.select_related("resolver", "assigned_by")

    @staticmethod
    @transaction.atomic
    def assign(
        *, actor, sr: ServiceRequest, resolvers: list
    ) -> list[ServiceRequestAssignment]:
        """Assign maintenance staff to the current round (adds to existing ones)."""
        if not ServiceRequestPolicy.can_assign(actor, sr):
            raise PermissionDenied(
                "Only the property management can assign service requests."
            )
        sr = lock(sr)
        if sr.status not in OPEN_STATES:
            raise InvalidTransition("Only open requests can be assigned.")
        if not resolvers:
            raise InvalidInput(
                "At least one resolver is required.", field="resolver_ids"
            )
        for resolver in resolvers:
            if not AccessService.is_maintenance_of(resolver, sr.property):
                raise InvalidInput(
                    f"{resolver.get_full_name()} does not hold the maintenance role on this property.",
                    field="resolver_ids",
                )
        already = set(current_assignments(sr).values_list("resolver_id", flat=True))
        created = [
            ServiceRequestAssignment.objects.create(
                service_request=sr,
                resolver=resolver,
                resolution_round=sr.current_round,
                assigned_by=actor,
            )
            for resolver in resolvers
            if resolver.pk not in already
        ]
        if not created:
            raise BusinessRuleViolation(
                "These resolvers are already assigned to the current round."
            )
        sr.status = ServiceRequestStatus.IN_PROGRESS
        sr.save(update_fields=["status", "updated_at"])
        AuditService.record(
            actor=actor,
            action=ServiceRequestAudit.ASSIGNED,
            target=sr,
            property_id=sr.property_id,
            metadata={
                "resolvers": [a.resolver_id for a in created],
                "round": sr.current_round,
            },
        )
        notices.assigned(sr, actor=actor, resolvers=[a.resolver for a in created])

        return created

    @staticmethod
    @transaction.atomic
    def resolve(
        *, actor, sr: ServiceRequest, note: str = "", files=()
    ) -> ServiceRequestAssignment:
        """The assigned resolver reports their work as done for the current round."""
        sr = lock(sr)
        assignment = (
            current_assignments(sr)
            .select_for_update(of=("self",))
            .filter(resolver=actor)
            .first()
        )
        if assignment is None:
            raise PermissionDenied(
                "You are not assigned to the current round of this request."
            )
        if sr.status != ServiceRequestStatus.IN_PROGRESS:
            raise InvalidTransition("Only requests in progress can be resolved.")
        if assignment.is_resolved:
            raise BusinessRuleViolation("You already reported this round as resolved.")
        now = timezone.now()
        assignment.is_resolved = True
        assignment.resolved_at = now
        assignment.resolution_note = note
        assignment.save(
            update_fields=[
                "is_resolved",
                "resolved_at",
                "resolution_note",
                "updated_at",
            ]
        )
        AttachmentService.attach(
            entity_type=EntityType.SERVICE_REQUEST_RESOLUTION,
            entity_id=assignment.pk,
            files=list(files),
            uploaded_by=actor,
        )
        AuditService.record(
            actor=actor,
            action=ServiceRequestAudit.ASSIGNMENT_RESOLVED,
            target=assignment,
            property_id=sr.property_id,
        )
        if not current_assignments(sr).filter(is_resolved=False).exists():
            sr.status = ServiceRequestStatus.RESOLVED
            sr.resolved_at = now
            sr.save(update_fields=["status", "resolved_at", "updated_at"])
            notices.resolved(sr, actor=actor)
        return assignment

    @staticmethod
    @transaction.atomic
    def give_feedback(
        *, actor, sr: ServiceRequest, feedback: Feedback
    ) -> ServiceRequest:
        """Requester's verdict on the current round: DONE closes, NOT_DONE reopens."""
        sr = lock(sr)
        if not ServiceRequestPolicy.can_give_feedback(actor, sr):
            raise PermissionDenied("Only the requester can give feedback.")
        if sr.status != ServiceRequestStatus.RESOLVED:
            raise InvalidTransition(
                "Feedback is expected once the request is resolved."
            )
        if feedback.rating is not None and not 1 <= feedback.rating <= 5:
            raise InvalidInput("The rating must be between 1 and 5.", field="rating")
        now = timezone.now()
        current_assignments(sr).update(
            requester_notice=feedback.notice,
            requester_rating=feedback.rating,
            requester_comment=feedback.comment,
            feedback_at=now,
            updated_at=now,
        )
        resolvers = current_resolvers(sr)
        if feedback.notice == RequesterNotice.DONE:
            sr.status = ServiceRequestStatus.CLOSED
            sr.closed_at = now
            sr.closed_by = actor
            sr.save(update_fields=["status", "closed_at", "closed_by", "updated_at"])
            AuditService.record(
                actor=actor,
                action=ServiceRequestAudit.CONFIRMED,
                target=sr,
                property_id=sr.property_id,
            )
            notices.confirmed_by_requester(
                sr, actor=actor, resolvers=resolvers, rating=feedback.rating
            )
        else:
            sr.status = ServiceRequestStatus.OPEN
            sr.current_round += 1
            sr.resolved_at = None
            sr.save(
                update_fields=["status", "current_round", "resolved_at", "updated_at"]
            )
            AuditService.record(
                actor=actor,
                action=ServiceRequestAudit.REOPENED,
                target=sr,
                property_id=sr.property_id,
            )
            notices.reopened(sr, actor=actor, resolvers=resolvers)
        return sr
