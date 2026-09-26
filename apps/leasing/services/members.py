"""Occupants of a lease: joining, leaving, contextual details and proofs."""

from __future__ import annotations

import datetime as dt

from django.db import transaction

from apps.common.attachments.rules import EntityType
from apps.common.attachments.service import AttachmentService
from apps.common.db import apply_changes, translate_integrity_errors
from apps.common.exceptions import (
    BusinessRuleViolation,
    InvalidInput,
    InvalidTransition,
    NotFound,
    PermissionDenied,
)
from apps.common.services.audit import AuditService
from apps.leasing import errors, notices
from apps.leasing.audit import LeaseAudit
from apps.leasing.models import Lease, LeaseMember, LeaseStatus
from apps.leasing.policies import LeaseMemberPolicy
from apps.leasing.services.rules import (
    MEMBER_EXTRA_FIELDS,
    MemberInput,
    check_member_account,
    check_member_dates,
    lock_active_lease,
)
from apps.properties import timezones
from apps.properties.models import Property

MEMBER_CONSTRAINTS = {"unique_lease_member": errors.already_member}


class LeaseMemberService:
    @staticmethod
    def get_visible(*, actor, prop: Property, member_id: int) -> LeaseMember:
        member = (
            LeaseMember.objects.select_related("lease__unit__building__property", "user")
            .filter(pk=member_id, lease__unit__building__property=prop)
            .first()
        )
        if member is None or not LeaseMemberPolicy.can_view(actor, member):
            raise NotFound("Lease member not found.")
        return member

    @staticmethod
    @transaction.atomic
    def add(*, actor, lease: Lease, member: MemberInput) -> LeaseMember:
        if not LeaseMemberPolicy.can_manage_members(actor, lease):
            raise PermissionDenied("Only the property management can add lease members.")
        lease = lock_active_lease(lease)
        check_member_account(member.user)
        joined_at = member.joined_at or max(
            lease.start_date, timezones.today(lease.unit.building.property)
        )
        check_member_dates(lease, joined_at)
        with translate_integrity_errors(MEMBER_CONSTRAINTS):
            row = LeaseMember.objects.create(
                lease=lease,
                user=member.user,
                joined_at=joined_at,
                is_signatory=member.is_signatory,
                added_by=actor,
                **member.extra_fields(),
            )
        AuditService.record(
            actor=actor,
            action=LeaseAudit.MEMBER_ADDED,
            target=row,
            property_id=lease.property_id,
        )
        notices.member_added(lease, user=member.user)
        return row

    @staticmethod
    @transaction.atomic
    def record_departure(*, actor, member: LeaseMember, left_at: dt.date) -> LeaseMember:
        """A co-tenant leaves: the row is kept and stamped, the lease goes on."""
        if not LeaseMemberPolicy.can_manage_members(actor, member.lease):
            raise PermissionDenied("Only the property management can record a departure.")
        lease = lock_active_lease(member.lease)
        member = LeaseMember.objects.select_for_update(of=("self",)).get(pk=member.pk)
        if member.left_at is not None:
            raise BusinessRuleViolation("This member has already left.")
        if left_at < member.joined_at:
            raise InvalidInput("The departure cannot precede the arrival.", field="left_at")
        if not lease.active_members().exclude(pk=member.pk).exists():
            raise BusinessRuleViolation(
                "The last active member cannot leave an active lease: terminate the lease instead.",
                code="last_active_member",
            )
        member.left_at = left_at
        member.departure_recorded_by = actor
        member.save(update_fields=["left_at", "departure_recorded_by", "updated_at"])
        AuditService.record(
            actor=actor,
            action=LeaseAudit.MEMBER_LEFT,
            target=member,
            property_id=lease.property_id,
        )
        return member

    @staticmethod
    @transaction.atomic
    def update(*, actor, member: LeaseMember, changes: dict) -> LeaseMember:
        if not LeaseMemberPolicy.can_update(actor, member):
            raise PermissionDenied("Members edit their own details; management edits any.")
        if member.lease.status != LeaseStatus.ACTIVE:
            raise InvalidTransition("The lease is closed; its members are frozen.")
        fields = apply_changes(member, changes, MEMBER_EXTRA_FIELDS)
        if "is_signatory" in changes:
            if not LeaseMemberPolicy.can_change_signatory(actor, member):
                raise PermissionDenied("Only management can change the signatory status.")
            member.is_signatory = changes["is_signatory"]
            fields.append("is_signatory")
        if fields:
            member.save(update_fields=[*fields, "updated_at"])
            AuditService.record(
                actor=actor,
                action=LeaseAudit.MEMBER_UPDATED,
                target=member,
                property_id=member.lease.property_id,
                metadata={"fields": fields},
            )
        return member

    @staticmethod
    @transaction.atomic
    def set_proof_of_identity(*, actor, member: LeaseMember, upload) -> None:
        LeaseMemberService._set_proof(
            actor,
            member,
            EntityType.LEASE_MEMBER_IDENTITY,
            "lease.member_proof_of_identity_uploaded",
            upload,
        )

    @staticmethod
    @transaction.atomic
    def set_proof_of_address(*, actor, member: LeaseMember, upload) -> None:
        LeaseMemberService._set_proof(
            actor,
            member,
            EntityType.LEASE_MEMBER_ADDRESS,
            "lease.member_proof_of_address_uploaded",
            upload,
        )

    @staticmethod
    def _set_proof(actor, member: LeaseMember, entity_type: str, audit_action: str, upload) -> None:
        if not LeaseMemberPolicy.can_update(actor, member):
            raise PermissionDenied("Members edit their own details; management edits any.")
        AttachmentService.attach_one(
            entity_type=entity_type,
            entity_id=member.pk,
            upload=upload,
            uploaded_by=actor,
        )
        AuditService.record(
            actor=actor,
            action=audit_action,
            target=member,
            property_id=member.lease.property_id,
        )
