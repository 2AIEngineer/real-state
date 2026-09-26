"""Move-in and move-out inspections: the state of each component of a leased unit."""

from __future__ import annotations

import datetime as dt

from django.db import transaction
from django.db.models import QuerySet

from apps.common.attachments.rules import EntityType
from apps.common.attachments.service import AttachmentService
from apps.common.db import apply_changes, translate_integrity_errors
from apps.common.deletion import destroy
from apps.common.exceptions import (
    InvalidInput,
    InvalidTransition,
    NotFound,
    PermissionDenied,
)
from apps.common.services.audit import AuditService
from apps.leasing import errors
from apps.leasing.audit import LeaseAudit
from apps.leasing.models import CheckPhase, Lease, LeaseComponentState, LeaseStatus
from apps.leasing.policies import LeaseComponentStatePolicy, LeasePolicy

COMPONENT_FIELDS = ("name", "description", "state", "on_check_date")
COMPONENT_CONSTRAINTS = {
    "unique_component_per_inspection": errors.component_already_recorded
}
RECORDERS_ONLY = "Only the property management can record inspections."


def _check_phase(
    lease: Lease,
    on_check: str,
    on_check_date: dt.date,
    name: str,
    exclude_pk: int | None = None,
) -> None:
    allowed = {
        CheckPhase.IN: (LeaseStatus.ACTIVE,),
        CheckPhase.OUT: (LeaseStatus.ACTIVE, LeaseStatus.TERMINATED),
    }
    if lease.status not in allowed[on_check]:
        raise InvalidTransition(
            f"A {on_check} inspection cannot be recorded on a {lease.status.lower()} lease."
        )
    if on_check_date < lease.start_date - dt.timedelta(days=31):
        raise InvalidInput(
            "The inspection date is too far before the lease start.",
            field="on_check_date",
        )
    if on_check == CheckPhase.OUT:
        check_in = (
            LeaseComponentState.objects.filter(
                lease=lease, on_check=CheckPhase.IN, name__iexact=name
            )
            .exclude(pk=exclude_pk)
            .first()
        )
        if check_in and on_check_date < check_in.on_check_date:
            raise InvalidInput(
                "The move-out inspection cannot precede the move-in inspection.",
                field="on_check_date",
            )


class LeaseComponentStateService:
    @staticmethod
    def list_for_lease(*, actor, lease: Lease) -> QuerySet[LeaseComponentState]:
        if not LeasePolicy.can_view(actor, lease):
            raise NotFound("Lease not found.")
        return LeaseComponentState.objects.filter(lease=lease)

    @staticmethod
    def get(
        *, actor, lease: Lease, lease_component_state_id: int
    ) -> LeaseComponentState:
        """An inspection line only exists inside its lease."""
        state = (
            LeaseComponentState.objects.select_related(
                "lease__unit__building__property"
            )
            .filter(pk=lease_component_state_id, lease=lease)
            .first()
        )
        if state is None or not LeaseComponentStatePolicy.can_view(actor, state):
            raise NotFound("Component state not found.")
        return state

    @staticmethod
    @transaction.atomic
    def record(
        *,
        actor,
        lease: Lease,
        name: str,
        state: str,
        on_check: str,
        on_check_date: dt.date,
        description: str = "",
        files=(),
    ) -> LeaseComponentState:
        if not LeaseComponentStatePolicy.can_record(actor, lease):
            raise PermissionDenied(RECORDERS_ONLY)
        lease = (
            Lease.objects.select_for_update(of=("self",))
            .select_related("unit__building")
            .get(pk=lease.pk)
        )
        _check_phase(lease, on_check, on_check_date, name)
        with translate_integrity_errors(COMPONENT_CONSTRAINTS):
            component = LeaseComponentState.objects.create(
                lease=lease,
                name=name.strip(),
                description=description,
                state=state,
                on_check=on_check,
                on_check_date=on_check_date,
                recorded_by=actor,
            )
        AttachmentService.attach(
            entity_type=EntityType.LEASE_COMPONENT_STATE,
            entity_id=component.pk,
            files=list(files),
            uploaded_by=actor,
        )
        AuditService.record(
            actor=actor,
            action=LeaseAudit.COMPONENT_RECORDED,
            target=component,
            property_id=lease.property_id,
        )
        return component

    @staticmethod
    @transaction.atomic
    def update(
        *, actor, component: LeaseComponentState, changes: dict
    ) -> LeaseComponentState:
        if not LeaseComponentStatePolicy.can_record(actor, component.lease):
            raise PermissionDenied(RECORDERS_ONLY)
        fields = apply_changes(component, changes, COMPONENT_FIELDS)
        _check_phase(
            component.lease,
            component.on_check,
            component.on_check_date,
            component.name,
            exclude_pk=component.pk,
        )
        if fields:
            with translate_integrity_errors(COMPONENT_CONSTRAINTS):
                component.save(update_fields=[*fields, "updated_at"])
            AuditService.record(
                actor=actor,
                action=LeaseAudit.COMPONENT_UPDATED,
                target=component,
                property_id=component.lease.property_id,
            )
        return component

    @staticmethod
    @transaction.atomic
    def delete(*, actor, component: LeaseComponentState) -> None:
        """Remove a line recorded by mistake during an inspection."""
        if not LeaseComponentStatePolicy.can_record(actor, component.lease):
            raise PermissionDenied(RECORDERS_ONLY)
        AuditService.record(
            actor=actor,
            action=LeaseAudit.COMPONENT_DELETED,
            target=component,
            property_id=component.lease.property_id,
        )
        destroy(component)

    @staticmethod
    @transaction.atomic
    def add_files(*, actor, component: LeaseComponentState, files) -> list:
        if not LeaseComponentStatePolicy.can_record(actor, component.lease):
            raise PermissionDenied(RECORDERS_ONLY)
        return AttachmentService.attach(
            entity_type=EntityType.LEASE_COMPONENT_STATE,
            entity_id=component.pk,
            files=list(files),
            uploaded_by=actor,
        )
