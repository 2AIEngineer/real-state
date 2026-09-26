"""What people are told about service requests."""

from __future__ import annotations

from apps.accounts.services.directory import UserDirectory
from apps.notifications.models import NotificationCategory, Severity
from apps.notifications.services import NotificationIntent, NotificationService
from apps.service_requests.models import ServiceRequest


def _tell(
    sr: ServiceRequest,
    *,
    event: str,
    title: str,
    body: str,
    actor,
    to=(),
    include_management: bool = True,
    severity: str = Severity.INFO,
) -> None:
    """Tell `to` by name and, unless told otherwise, the property management by BCC."""
    NotificationService.notify(
        NotificationIntent(
            event_type=f"service_request.{event}",
            category=NotificationCategory.SERVICE_REQUEST,
            title=title,
            body=body,
            to=list(to),
            bcc=UserDirectory.management(sr.property) if include_management else [],
            target=sr,
            severity=severity,
            exclude=[actor] if actor else [],
            data={"service_request_id": sr.pk, "property_id": sr.property_id},
            action_path=f"/service-requests/{sr.pk}",
        )
    )


def submitted(sr: ServiceRequest) -> None:
    _tell(
        sr,
        event="created",
        actor=None,
        to=[sr.requester],
        title=f"Demande #{sr.pk} enregistrée",
        body=f"« {sr.title} » a été transmise à la gestion de {sr.property.name}.",
    )


def assigned(sr: ServiceRequest, *, actor, resolvers) -> None:
    lot = f" — lot {sr.unit.number}" if sr.unit_id else ""
    _tell(
        sr,
        event="assigned",
        actor=actor,
        to=resolvers,
        title=f"Intervention assignée — demande #{sr.pk}",
        body=f"« {sr.title} »{lot}",
    )
    _tell(
        sr,
        event="in_progress",
        actor=actor,
        to=[sr.requester],
        include_management=False,
        title=f"Demande #{sr.pk} prise en charge",
        body="Un intervenant a été assigné à votre demande.",
    )


def resolved(sr: ServiceRequest, *, actor) -> None:
    _tell(
        sr,
        event="resolved",
        actor=actor,
        to=[sr.requester],
        severity=Severity.SUCCESS,
        title=f"Demande #{sr.pk} résolue",
        body=(
            "L'intervention est terminée. "
            "Merci de confirmer si le problème est réglé et de noter l'intervention."
        ),
    )


def confirmed_by_requester(sr: ServiceRequest, *, actor, resolvers, rating: int | None) -> None:
    _tell(
        sr,
        event="closed",
        actor=actor,
        to=resolvers,
        severity=Severity.SUCCESS,
        title=f"Demande #{sr.pk} clôturée",
        body="Le demandeur a confirmé la résolution." + (f" Note : {rating}/5." if rating else ""),
    )


def reopened(sr: ServiceRequest, *, actor, resolvers) -> None:
    _tell(
        sr,
        event="reopened",
        actor=actor,
        to=resolvers,
        severity=Severity.WARNING,
        title=f"Demande #{sr.pk} rouverte",
        body="Le demandeur indique que le problème persiste. Une nouvelle intervention est nécessaire.",
    )


def closed_by_management(sr: ServiceRequest, *, actor) -> None:
    _tell(
        sr,
        event="closed",
        actor=actor,
        to=[sr.requester],
        include_management=False,
        title=f"Demande #{sr.pk} clôturée",
        body="Votre demande a été clôturée par la gestion.",
    )


def cancelled(sr: ServiceRequest, *, actor, resolvers, reason: str) -> None:
    _tell(
        sr,
        event="cancelled",
        actor=actor,
        to=[sr.requester, *resolvers],
        title=f"Demande #{sr.pk} annulée",
        body=reason or "La demande a été annulée.",
    )
