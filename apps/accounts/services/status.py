"""The status of an account: deactivating, reactivating, deleting it for good."""

from __future__ import annotations

from django.contrib.auth import get_user_model
from django.db import transaction
from django.utils import timezone

from apps.accounts import notices
from apps.accounts.audit import AccountAudit
from apps.accounts.policies import AccountPolicy
from apps.accounts.services.assignments import (
    BuildingAssignmentService,
    PropertyAssignmentService,
    SyndicatAssignmentService,
)
from apps.accounts.services.tokens import TokenService
from apps.common.deletion import destroy
from apps.common.exceptions import (
    BusinessRuleViolation,
    PermissionDenied,
)
from apps.common.services.audit import AuditService
from apps.leasing.models import Lease, LeaseMember, LeaseStatus
from apps.leasing.services import LeaseService
from apps.notifications.services import PushTokenService
from apps.properties.models import OwnershipStatus, Unit, UnitOwnership
from apps.properties.services import OwnershipService

User = get_user_model()

MANAGE_THIS_ACCOUNT = (
    "You cannot manage this account: admins manage every account, syndics and managers "
    "those holding a role they handle, never their own."
)


class AccountStatusService:
    @staticmethod
    def _ensure_no_active_obligations(user) -> None:
        if LeaseMember.objects.filter(
            user=user, left_at__isnull=True, lease__status=LeaseStatus.ACTIVE
        ).exists():
            raise BusinessRuleViolation(
                "This user is an active member of a lease. "
                "Record their departure before deactivating the account.",
                code="active_lease_member",
            )
        if UnitOwnership.objects.filter(owner=user, status=OwnershipStatus.ACTIVE).exists():
            raise BusinessRuleViolation(
                "This user still owns units. "
                "Transfer the ownerships before deactivating the account.",
                code="active_owner",
            )
        if user.is_technical_account:
            raise BusinessRuleViolation("Technical accounts are managed with their promoter.")

    @staticmethod
    @transaction.atomic
    def deactivate(*, actor, user, reason: str = ""):
        if not AccountPolicy.can_change_status(actor, user):
            raise PermissionDenied(MANAGE_THIS_ACCOUNT)
        if actor.pk == user.pk:
            raise BusinessRuleViolation("You cannot deactivate your own account.")
        user = User.objects.select_for_update(of=("self",)).get(pk=user.pk)
        if not user.is_active:
            raise BusinessRuleViolation("This account is already deactivated.")
        AccountStatusService._ensure_no_active_obligations(user)
        # Notify first: the dispatcher skips inactive recipients.
        notices.critical_change(
            user,
            title="Compte désactivé",
            body="Votre compte a été désactivé. Vous ne pouvez plus vous connecter à l'application.",
        )
        user.is_active = False
        user.deactivated_at = timezone.now()
        user.save(update_fields=["is_active", "deactivated_at", "updated_at"])
        for assignments in (
            SyndicatAssignmentService,
            PropertyAssignmentService,
            BuildingAssignmentService,
        ):
            assignments.revoke_all(actor=actor, user=user, reason="account_deactivated")
        PushTokenService.deactivate_all(user=user, reason="account_deactivated")
        TokenService.revoke_all(user=user)
        AuditService.record(
            actor=actor,
            action=AccountAudit.DEACTIVATED,
            target=user,
            metadata={"reason": reason},
        )
        return user

    @staticmethod
    @transaction.atomic
    def reactivate(*, actor, user):
        if not AccountPolicy.can_change_status(actor, user):
            raise PermissionDenied(MANAGE_THIS_ACCOUNT)
        if user.is_active:
            raise BusinessRuleViolation("This account is already active.")
        user.is_active = True
        user.deactivated_at = None
        user.save(update_fields=["is_active", "deactivated_at", "updated_at"])
        AuditService.record(actor=actor, action=AccountAudit.REACTIVATED, target=user)
        notices.critical_change(user, title="Compte réactivé", body="Votre compte a été réactivé.")
        return user

    @staticmethod
    @transaction.atomic
    def delete(*, actor, user) -> None:
        """Deletes the account for good, with everything that is theirs.

        Deactivating is the alternative that keeps the account. Deleting takes
        what belongs to the person (ownerships, lease memberships, requests,
        bookings, orders, listings, messages, answers, devices, notifications,
        assignments), each with its files. What they only wrote or recorded for
        a residence (announcements, events, documents, visitor entries…) stays,
        without an author. Invariants are restored afterwards: a unit left
        without an owner reverts to its promoter, a lease left without an
        occupant ends.
        """
        if not AccountPolicy.can_change_status(actor, user):
            raise PermissionDenied(MANAGE_THIS_ACCOUNT)
        if actor.pk == user.pk:
            raise BusinessRuleViolation("You cannot delete your own account.")
        if user.is_technical_account:
            raise BusinessRuleViolation("Technical accounts are managed with their promoter.")
        owned_units = list(
            Unit.objects.filter(ownerships__owner=user, ownerships__status=OwnershipStatus.ACTIVE)
            .select_related("building__property")
            .distinct()
        )
        lease_ids = list(
            LeaseMember.objects.filter(
                user=user, left_at__isnull=True, lease__status=LeaseStatus.ACTIVE
            ).values_list("lease_id", flat=True)
        )
        AuditService.record(
            actor=actor, action=AccountAudit.DELETED, target=user, metadata={"role": user.role}
        )
        TokenService.revoke_all(user=user)
        destroy(user)
        for unit in owned_units:
            OwnershipService.ensure_owned(unit, actor=actor)
        for lease in Lease.objects.filter(pk__in=lease_ids).select_related(
            "unit__building__property"
        ):
            LeaseService.end_if_unoccupied(actor=actor, lease=lease)
