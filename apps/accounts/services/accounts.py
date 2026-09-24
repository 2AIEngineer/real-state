"""Account lifecycle: creation by staff (invitation), profile changes,
deactivation and closure.

There is no public sign-up: the application is not a public storefront, every
account is created by someone entitled to do so and receives an e-mail to set
its password. What ties a new account to the residence is `registration`; its
password is `passwords`.
"""

from __future__ import annotations

from collections.abc import Sequence

from django.contrib.auth import get_user_model
from django.db import transaction
from django.db.models import Q, QuerySet
from django.utils import timezone

from apps.accounts import errors, notices
from apps.accounts.audit import AccountAudit
from apps.accounts.enums import Gender, StructuralRole
from apps.accounts.models import ProviderProfile
from apps.accounts.policies import AccountPolicy, can_give_role
from apps.accounts.services import registration
from apps.accounts.services.assignments import (
    BuildingAssignmentService,
    PropertyAssignmentService,
    SyndicatAssignmentService,
    assign_according_to_role,
    is_assignable_role,
)
from apps.accounts.services.passwords import normalize_email
from apps.accounts.services.providers import ProviderProfileService
from apps.accounts.services.registration import OwnedUnit, RentedUnit
from apps.accounts.services.roles import RoleService
from apps.accounts.services.tokens import TokenService
from apps.common.db import apply_changes, translate_integrity_errors
from apps.common.exceptions import (
    BusinessRuleViolation,
    InvalidInput,
    NotFound,
    PermissionDenied,
)
from apps.common.services.audit import AuditService
from apps.leasing.models import LeaseMember, LeaseStatus
from apps.notifications.services import PushTokenService
from apps.properties.models import OwnershipStatus, UnitOwnership

User = get_user_model()

PROFILE_FIELDS = ("first_name", "last_name", "phone", "gender", "preferred_language")
EMAIL_CONSTRAINTS = {
    "user_email_ci_unique": errors.email_taken,
    "accounts_user_email_key": errors.email_taken,
}
MANAGE_ACCOUNTS_ONLY = "Only administrators, syndics and managers can manage accounts."


class AccountService:
    # ------------------------------------------------------------------ queries
    @staticmethod
    def search(
        *,
        actor,
        query: str | None = None,
        property_id: int | None = None,
        include_inactive: bool = False,
    ) -> QuerySet:
        if not AccountPolicy.can_manage_accounts(actor):
            raise PermissionDenied(MANAGE_ACCOUNTS_ONLY)
        reach = AccountPolicy.searchable_filter(actor, property_id=property_id, query=query)
        users = User.objects.filter(reach, is_technical_account=False)
        if not include_inactive:
            users = users.filter(is_active=True)
        if query:
            users = users.filter(
                Q(email__icontains=query)
                | Q(first_name__icontains=query)
                | Q(last_name__icontains=query)
            )
        return users.order_by("last_name", "first_name", "id")

    @staticmethod
    def resolve(*, user_id: int, field: str = "user_id"):
        """Reference lookup for payload ids; authorization stays with the caller's service."""
        user = User.objects.filter(pk=user_id).first()
        if user is None:
            raise NotFound(f"User {user_id} not found.", field=field)
        return user

    @staticmethod
    def resolve_many(*, user_ids, field: str = "user_ids") -> list:
        ids = list(dict.fromkeys(user_ids))
        users = {user.pk: user for user in User.objects.filter(pk__in=ids)}
        missing = [i for i in ids if i not in users]
        if missing:
            raise NotFound(f"Unknown user(s): {missing}.", field=field)
        return [users[i] for i in ids]

    @staticmethod
    def get_visible(*, actor, user_id: int):
        user = User.objects.filter(pk=user_id).first()
        if user is None or not AccountPolicy.can_view(actor, user):
            raise NotFound("User not found.")
        return user

    # --------------------------------------------------------------- creation & role
    @staticmethod
    @transaction.atomic
    def create_account(
        *,
        actor,
        email: str,
        first_name: str,
        last_name: str,
        phone: str = "",
        gender: str = Gender.UNDISCLOSED,
        preferred_language: str = "fr",
        role: str = StructuralRole.STANDARD,
        syndicat_id: int,
        property_id: int | None = None,
        building_ids=(),
        ownerships: Sequence[OwnedUnit] = (),
        tenancy: RentedUnit | None = None,
    ):
        """Create an account together with what ties it to the residence.

        The account is born with its role: nothing is *changed* here, so none of
        what a role change entails happens (no journal entry about a former
        role, no "your role changed" notice — the invitation is the only message
        the new account receives). A standard account is then registered with
        its units (`ownerships`, `tenancy`), every other role with the place
        where that role is exercised, in this same transaction.

        `syndicat_id` and `property_id` are the syndicat and the property
        selected by the author.
        """
        if not AccountPolicy.can_manage_accounts(actor):
            raise PermissionDenied(MANAGE_ACCOUNTS_ONLY)
        if role not in StructuralRole.values:
            raise InvalidInput("Unknown role.", field="role")
        if not can_give_role(actor, role):
            raise PermissionDenied(f"You cannot create a {role} account.")
        registration.check_ties(role, ownerships=ownerships, tenancy=tenancy)
        email = normalize_email(email)
        if User.objects.filter(email__iexact=email).exists():
            raise errors.email_taken()
        with translate_integrity_errors(EMAIL_CONSTRAINTS):
            user = User.objects.create_user(
                email=email,
                password=None,
                first_name=first_name.strip(),
                last_name=last_name.strip(),
                phone=phone.strip(),
                gender=gender,
                preferred_language=preferred_language,
                role=role,
                created_by=actor,
            )
        AuditService.record(
            actor=actor, action=AccountAudit.CREATED, target=user, metadata={"role": role}
        )
        if ownerships:
            registration.register_ownerships(actor=actor, user=user, ownerships=ownerships)
        if tenancy is not None:
            registration.register_tenancy(actor=actor, user=user, tenancy=tenancy)
        if is_assignable_role(role):
            assign_according_to_role(
                actor=actor,
                user=user,
                syndicat_id=syndicat_id,
                property_id=property_id,
                building_ids=building_ids,
            )
        if role == StructuralRole.PROVIDER:
            ProviderProfileService.ensure_exists(user=user)
        notices.password_setup(user, first_time=True)
        return user

    @staticmethod
    @transaction.atomic
    def change_role(
        *,
        actor,
        user,
        role: str,
        syndicat_id: int,
        property_id: int | None = None,
        building_ids=(),
    ):
        """Give the account a role together with the place where it is exercised.

        Two steps, in one transaction: the role (`RoleService.set_role`), then
        the place (`assign_according_to_role`), which is the syndicat and the property
        the author has selected. Keeping the same role and naming buildings adds them.
        """
        previous_role = (
            User.objects.select_for_update().values_list("role", flat=True).get(pk=user.pk)
        )
        user = RoleService.set_role(actor=actor, user=user, role=role)
        if is_assignable_role(role) and (role != previous_role or building_ids):
            assign_according_to_role(
                actor=actor,
                user=user,
                syndicat_id=syndicat_id,
                property_id=property_id,
                building_ids=building_ids,
            )
        return user

    @staticmethod
    @transaction.atomic
    def resend_invitation(*, actor, user) -> None:
        if not AccountPolicy.can_view(actor, user):
            raise NotFound("User not found.")
        if not AccountPolicy.can_invite(actor, user):
            raise PermissionDenied(MANAGE_ACCOUNTS_ONLY)
        if user.has_usable_password():
            raise BusinessRuleViolation("This account has already been activated.")
        if not user.is_active or user.is_technical_account:
            raise BusinessRuleViolation("This account cannot receive an invitation.")
        AuditService.record(actor=actor, action=AccountAudit.INVITATION_RESENT, target=user)
        notices.password_setup(user, first_time=True)

    # ------------------------------------------------------------------ profile
    @staticmethod
    @transaction.atomic
    def update_profile(*, actor, user, changes: dict):
        if not AccountPolicy.can_edit_profile(actor, user):
            raise PermissionDenied("You can only edit your own profile.")
        fields = apply_changes(user, changes, PROFILE_FIELDS)
        if fields:
            user.save(update_fields=[*fields, "updated_at"])
            AuditService.record(
                actor=actor,
                action=AccountAudit.PROFILE_UPDATED,
                target=user,
                metadata={"fields": fields},
            )
        return user

    @staticmethod
    @transaction.atomic
    def change_email(*, actor, user, new_email: str, current_password: str | None = None):
        """Critical change: the login identifier. Both addresses are warned."""
        if not AccountPolicy.can_change_email(actor, user):
            raise PermissionDenied()
        if actor.pk == user.pk and (
            not current_password or not user.check_password(current_password)
        ):
            raise PermissionDenied("Current password is incorrect.", code="invalid_password")
        new_email = normalize_email(new_email)
        if new_email == user.email:
            return user
        if User.objects.filter(email__iexact=new_email).exclude(pk=user.pk).exists():
            raise errors.email_taken()
        old_email = user.email
        user.email = new_email
        with translate_integrity_errors(EMAIL_CONSTRAINTS):
            user.save(update_fields=["email", "updated_at"])
        AuditService.record(
            actor=actor,
            action=AccountAudit.EMAIL_CHANGED,
            target=user,
            metadata={"old": old_email, "new": new_email},
        )
        notices.critical_change(
            user,
            title="Adresse e-mail modifiée",
            body=(
                f"L'adresse de connexion de votre compte est désormais {new_email}. "
                "Si vous n'êtes pas à l'origine de ce changement, contactez votre gestionnaire."
            ),
            extra_emails=(old_email,),
        )
        return user

    # ------------------------------------------------------------------ status
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
        AccountService._ensure_no_active_obligations(user)
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
        data is erased (the account becomes an anonymous, inactive tombstone)."""
        if user.is_active:
            AccountService.deactivate(actor=actor, user=user, reason="account_closed")
        elif not AccountPolicy.can_change_status(actor):
            raise PermissionDenied()
        user = User.objects.select_for_update(of=("self",)).get(pk=user.pk)
        user.email = f"user-{user.pk}@erased.invalid"
        user.first_name = "Compte"
        user.last_name = "supprimé"
        user.phone = ""
        user.set_unusable_password()
        user.save(
            update_fields=["email", "first_name", "last_name", "phone", "password", "updated_at"]
        )
        ProviderProfile.objects.filter(user=user).delete()
        AuditService.record(actor=actor, action=AccountAudit.CLOSED, target=user)
        return user
