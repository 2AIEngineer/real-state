"""The status of an account: deactivating, reactivating, closing (erasing personal data)."""

from __future__ import annotations

from django.contrib.auth import get_user_model
from django.db import transaction
from django.utils import timezone

from apps.accounts import notices
from apps.accounts.audit import AccountAudit
from apps.accounts.models import ProviderProfile
from apps.accounts.policies import AccountPolicy
from apps.accounts.services.assignments import (
    BuildingAssignmentService,
    PropertyAssignmentService,
    SyndicatAssignmentService,
)
from apps.accounts.services.tokens import TokenService
from apps.common.exceptions import (
    BusinessRuleViolation,
    PermissionDenied,
)
from apps.common.services.audit import AuditService
from apps.leasing.models import LeaseMember, LeaseStatus
from apps.notifications.services import PushTokenService, erase_notifications_of
from apps.properties.models import OwnershipStatus, UnitOwnership

User = get_user_model()


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
        if not AccountPolicy.can_change_status(actor):
            raise PermissionDenied("Only platform administrators can deactivate accounts.")
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
        if not AccountPolicy.can_change_status(actor):
            raise PermissionDenied("Only platform administrators can reactivate accounts.")
        if user.is_active:
            raise BusinessRuleViolation("This account is already active.")
        if user.email.endswith("@erased.invalid"):
            raise BusinessRuleViolation("A closed account cannot be reactivated.")
        user.is_active = True
        user.deactivated_at = None
        user.save(update_fields=["is_active", "deactivated_at", "updated_at"])
        AuditService.record(actor=actor, action=AccountAudit.REACTIVATED, target=user)
        notices.critical_change(user, title="Compte réactivé", body="Votre compte a été réactivé.")
        return user

    @staticmethod
    @transaction.atomic
    def close(*, actor, user):
        """Account deletion. Rows referenced by history are kept but personal
        data is erased: the account becomes an anonymous, inactive tombstone.

        Erased: identity (e-mail, names, phone, gender, language), password,
        provider profile, devices, in-app notifications and preferences.
        Kept: what other records point at (leases, requests, audit entries),
        now attached to the tombstone.
        """
        if user.is_active:
            AccountStatusService.deactivate(actor=actor, user=user, reason="account_closed")
        elif not AccountPolicy.can_change_status(actor):
            raise PermissionDenied()
        user = User.objects.select_for_update(of=("self",)).get(pk=user.pk)
        user.email = f"user-{user.pk}@erased.invalid"
        user.first_name = "Compte"
        user.last_name = "supprimé"
        user.phone = ""
        user.gender = User._meta.get_field("gender").default
        user.preferred_language = User._meta.get_field("preferred_language").default
        user.set_unusable_password()
        user.save(
            update_fields=[
                "email",
                "first_name",
                "last_name",
                "phone",
                "gender",
                "preferred_language",
                "password",
                "updated_at",
            ]
        )
        ProviderProfile.objects.filter(user=user).delete()
        erase_notifications_of(user)
        AuditService.record(actor=actor, action=AccountAudit.CLOSED, target=user)
        return user
