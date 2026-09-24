"""Service requests and their resolution rounds.

Lifecycle
    OPEN ──assign──▶ IN_PROGRESS ──(all resolvers resolved)──▶ RESOLVED
    RESOLVED ──requester DONE / management close──▶ CLOSED
    RESOLVED ──requester NOT_DONE──▶ OPEN (round + 1, awaiting reassignment)
    OPEN | IN_PROGRESS ──cancel──▶ CANCELLED
"""

from __future__ import annotations

from dataclasses import dataclass

from django.contrib.auth import get_user_model
from django.db import transaction
from django.db.models import QuerySet
from django.utils import timezone

from apps.accounts.services.authorization import AccessService
from apps.common.db import deleting
from apps.common.exceptions import (
    BusinessRuleViolation,
    InvalidInput,
    InvalidTransition,
    NotFound,
    PermissionDenied,
)
from apps.common.models import EntityType
from apps.common.services.attachments import AttachmentService
from apps.common.services.audit import AuditService
from apps.notifications.services import delete_notification_traces
from apps.properties.enums import Feature
from apps.properties.models import Property, Unit
from apps.properties.services import FeatureGate
from apps.service_requests import notices
from apps.service_requests.audit import ServiceRequestAudit
from apps.service_requests.models import (
    RequesterNotice,
    ServiceRequest,
    ServiceRequestAssignment,
    ServiceRequestPriority,
    ServiceRequestStatus,
)
from apps.service_requests.policies import ServiceRequestPolicy

User = get_user_model()

OPEN_STATES = (ServiceRequestStatus.OPEN, ServiceRequestStatus.IN_PROGRESS)


@dataclass(frozen=True)
class Feedback:
    notice: str
    rating: int | None = None
    comment: str = ""


def _current_assignments(sr: ServiceRequest) -> QuerySet[ServiceRequestAssignment]:
    return sr.assignments.filter(resolution_round=sr.current_round)


def _current_resolvers(sr: ServiceRequest) -> list:
    return [a.resolver for a in _current_assignments(sr).select_related("resolver")]


def _purge_conversation(sr: ServiceRequest) -> None:
    """Drop the chat room of the request being deleted, with its media."""
    from apps.chat.services import ChatService

    ChatService.delete_conversation_of(sr)


class ServiceRequestService:
    @staticmethod
    def list_visible(
        *, actor, property_id: int, status: str | None = None, mine: bool = False
    ) -> QuerySet[ServiceRequest]:
        qs = (
            ServiceRequest.objects.filter(ServiceRequestPolicy.visible_filter(actor))
            .distinct()
            .select_related("property", "unit", "requester")
        )
        if mine:
            qs = qs.filter(requester=actor)
        qs = qs.filter(property_id=property_id)
        if status:
            qs = qs.filter(status=status)
        return qs

    @staticmethod
    def get_visible(*, actor, request_id: int) -> ServiceRequest:
        sr = (
            ServiceRequest.objects.select_related("property", "unit__building", "requester")
            .filter(pk=request_id)
            .first()
        )
        if sr is None or not ServiceRequestPolicy.can_view(actor, sr):
            raise NotFound("Service request not found.")
        return sr

    # --------------------------------------------------------------- creation
    @staticmethod
    @transaction.atomic
    def submit(
        *,
        actor,
        prop: Property,
        title: str,
        description: str,
        category: str,
        priority: str = ServiceRequestPriority.MEDIUM,
        unit: Unit | None = None,
        files=(),
    ) -> ServiceRequest:
        FeatureGate.require(prop, Feature.SERVICE_REQUEST)
        if unit is not None:
            if unit.building.property_id != prop.pk:
                raise InvalidInput("The unit belongs to another property.", field="unit_id")
        if not ServiceRequestPolicy.can_submit(actor, prop, unit):
            raise PermissionDenied("You can only submit requests for your own units or property.")
        sr = ServiceRequest.objects.create(
            property=prop,
            unit=unit,
            requester=actor,
            title=title.strip(),
            description=description,
            category=category,
            priority=priority,
        )
        AttachmentService.attach(
            entity_type=EntityType.SERVICE_REQUEST,
            entity_id=sr.pk,
            files=list(files),
            uploaded_by=actor,
        )
        AuditService.record(
            actor=actor, action=ServiceRequestAudit.SUBMITTED, target=sr, property_id=prop.pk
        )
        notices.submitted(sr)
        return sr

    @staticmethod
    @transaction.atomic
    def add_files(*, actor, sr: ServiceRequest, files) -> list:
        if not ServiceRequestPolicy.can_add_files(actor, sr):
            raise NotFound("Service request not found.")
        if sr.status not in OPEN_STATES:
            raise InvalidTransition("Files can only be added while the request is open.")
        return AttachmentService.attach(
            entity_type=EntityType.SERVICE_REQUEST,
            entity_id=sr.pk,
            files=list(files),
            uploaded_by=actor,
        )

    @staticmethod
    @transaction.atomic
    def remove_file(*, actor, sr: ServiceRequest, attachment_id: int) -> None:
        """The uploader takes back a file, management may remove any."""
        if not ServiceRequestPolicy.can_view(actor, sr):
            raise NotFound("Service request not found.")
        attachment = AttachmentService.get(
            entity_type=EntityType.SERVICE_REQUEST, entity_id=sr.pk, attachment_id=attachment_id
        )
        if not ServiceRequestPolicy.can_remove_file(actor, sr, attachment.uploaded_by_id):
            raise PermissionDenied(
                "Only the uploader or the property management can remove this file."
            )
        AttachmentService.delete(attachment=attachment)

    # -------------------------------------------------------------- lifecycle
    @staticmethod
    def _lock(sr: ServiceRequest) -> ServiceRequest:
        return (
            ServiceRequest.objects.select_for_update(of=("self",))
            .select_related("property", "requester")
            .get(pk=sr.pk)
        )

    @staticmethod
    @transaction.atomic
    def assign(*, actor, sr: ServiceRequest, resolvers: list) -> list[ServiceRequestAssignment]:
        """Assign maintenance staff to the current round (adds to existing ones)."""
        if not ServiceRequestPolicy.can_assign(actor, sr):
            raise PermissionDenied("Only the property management can assign service requests.")
        sr = ServiceRequestService._lock(sr)
        if sr.status not in OPEN_STATES:
            raise InvalidTransition("Only open requests can be assigned.")
        if not resolvers:
            raise InvalidInput("At least one resolver is required.", field="resolver_ids")
        for resolver in resolvers:
            if not AccessService.is_maintenance_of(resolver, sr.property):
                raise InvalidInput(
                    f"{resolver.get_full_name()} does not hold the maintenance role on this property.",
                    field="resolver_ids",
                )
        already = set(_current_assignments(sr).values_list("resolver_id", flat=True))
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
            metadata={"resolvers": [a.resolver_id for a in created], "round": sr.current_round},
        )
        notices.assigned(sr, actor=actor, resolvers=[a.resolver for a in created])

        return created

    @staticmethod
    @transaction.atomic
    def resolve(*, actor, sr: ServiceRequest, note: str = "", files=()) -> ServiceRequestAssignment:
        """The assigned resolver reports their work as done for the current round."""
        sr = ServiceRequestService._lock(sr)
        assignment = (
            _current_assignments(sr).select_for_update(of=("self",)).filter(resolver=actor).first()
        )
        if assignment is None:
            raise PermissionDenied("You are not assigned to the current round of this request.")
        if sr.status != ServiceRequestStatus.IN_PROGRESS:
            raise InvalidTransition("Only requests in progress can be resolved.")
        if assignment.is_resolved:
            raise BusinessRuleViolation("You already reported this round as resolved.")
        now = timezone.now()
        assignment.is_resolved = True
        assignment.resolved_at = now
        assignment.resolution_note = note
        assignment.save(
            update_fields=["is_resolved", "resolved_at", "resolution_note", "updated_at"]
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
        if not _current_assignments(sr).filter(is_resolved=False).exists():
            sr.status = ServiceRequestStatus.RESOLVED
            sr.resolved_at = now
            sr.save(update_fields=["status", "resolved_at", "updated_at"])
            notices.resolved(sr, actor=actor)
        return assignment

    @staticmethod
    @transaction.atomic
    def give_feedback(*, actor, sr: ServiceRequest, feedback: Feedback) -> ServiceRequest:
        """Requester's verdict on the current round: DONE closes, NOT_DONE reopens."""
        sr = ServiceRequestService._lock(sr)
        if not ServiceRequestPolicy.can_give_feedback(actor, sr):
            raise PermissionDenied("Only the requester can give feedback.")
        if sr.status != ServiceRequestStatus.RESOLVED:
            raise InvalidTransition("Feedback is expected once the request is resolved.")
        if feedback.rating is not None and not 1 <= feedback.rating <= 5:
            raise InvalidInput("The rating must be between 1 and 5.", field="rating")
        now = timezone.now()
        _current_assignments(sr).update(
            requester_notice=feedback.notice,
            requester_rating=feedback.rating,
            requester_comment=feedback.comment,
            feedback_at=now,
            updated_at=now,
        )
        resolvers = _current_resolvers(sr)
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
            sr.save(update_fields=["status", "current_round", "resolved_at", "updated_at"])
            AuditService.record(
                actor=actor,
                action=ServiceRequestAudit.REOPENED,
                target=sr,
                property_id=sr.property_id,
            )
            notices.reopened(sr, actor=actor, resolvers=resolvers)
        return sr

    @staticmethod
    @transaction.atomic
    def close(*, actor, sr: ServiceRequest) -> ServiceRequest:
        """Management closes a resolved request (e.g. requester never answered)."""
        if not ServiceRequestPolicy.can_close(actor, sr):
            raise PermissionDenied("Only the property management can close service requests.")
        sr = ServiceRequestService._lock(sr)
        if sr.status != ServiceRequestStatus.RESOLVED:
            raise InvalidTransition("Only resolved requests can be closed.")
        sr.status = ServiceRequestStatus.CLOSED
        sr.closed_at = timezone.now()
        sr.closed_by = actor
        sr.save(update_fields=["status", "closed_at", "closed_by", "updated_at"])
        AuditService.record(
            actor=actor, action=ServiceRequestAudit.CLOSED, target=sr, property_id=sr.property_id
        )
        notices.closed_by_management(sr, actor=actor)
        return sr

    @staticmethod
    @transaction.atomic
    def cancel(*, actor, sr: ServiceRequest, reason: str = "") -> ServiceRequest:
        sr = ServiceRequestService._lock(sr)
        if not ServiceRequestPolicy.can_cancel(actor, sr):
            raise PermissionDenied(
                "Only the requester or the property management can cancel this request."
            )
        if sr.status not in OPEN_STATES:
            raise InvalidTransition("Only open requests can be cancelled.")
        sr.status = ServiceRequestStatus.CANCELLED
        sr.cancelled_at = timezone.now()
        sr.cancellation_reason = reason
        sr.save(update_fields=["status", "cancelled_at", "cancellation_reason", "updated_at"])
        AuditService.record(
            actor=actor, action=ServiceRequestAudit.CANCELLED, target=sr, property_id=sr.property_id
        )
        notices.cancelled(sr, actor=actor, resolvers=_current_resolvers(sr), reason=reason)
        return sr

    @staticmethod
    @transaction.atomic
    def delete(*, actor, sr: ServiceRequest) -> None:
        """Permanent removal of a request, its rounds and its conversation (all cascaded)."""
        if not ServiceRequestPolicy.can_delete(actor, sr):
            raise PermissionDenied("Only the property management can delete service requests.")
        AuditService.record(
            actor=actor,
            action=ServiceRequestAudit.DELETED,
            target=sr,
            property_id=sr.property_id,
            metadata={"status": sr.status, "title": sr.title},
        )
        with deleting("service request"):
            for assignment in sr.assignments.all():
                AttachmentService.delete_for_entity(
                    EntityType.SERVICE_REQUEST_RESOLUTION, assignment.pk
                )
            _purge_conversation(sr)
            AttachmentService.delete_for_entity(EntityType.SERVICE_REQUEST, sr.pk)
            delete_notification_traces(sr)
            sr.delete()

    @staticmethod
    def assignments(*, actor, sr: ServiceRequest) -> QuerySet[ServiceRequestAssignment]:
        if not ServiceRequestPolicy.can_view(actor, sr):
            raise NotFound("Service request not found.")
        return sr.assignments.select_related("resolver", "assigned_by")
