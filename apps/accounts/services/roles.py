"""The single platform-wide role of an account and how it changes.

This service only sets the role. The places where the role is exercised are
the assignment services' concern; giving an account a role together with its
places is done by `AccountService.create_account` / `AccountService.change_role`.

A role change never lets assignments of the former role survive under the new
one: it is refused while the account still has active assignments (they must
be revoked explicitly first, each revocation being audited).

Who may set which role (see `can_change_role`): admins any role; syndics
standard, syndic, manager and field roles; managers standard, manager and
field roles. Only an admin gives the admin or provider role.
"""

from __future__ import annotations

from django.contrib.auth import get_user_model
from django.db import transaction

from apps.accounts import notices
from apps.accounts.audit import RoleAudit
from apps.accounts.enums import StructuralRole
from apps.accounts.policies import AccountPolicy, can_change_role
from apps.accounts.services.assignments import (
    BuildingAssignmentService,
    PropertyAssignmentService,
    SyndicatAssignmentService,
)
from apps.accounts.services.providers import ProviderProfileService
from apps.common.exceptions import BusinessRuleViolation, InvalidInput, NotFound, PermissionDenied
from apps.common.services.audit import AuditService

User = get_user_model()


def _refuse_while_still_assigned(user) -> None:
    """A role change starts from a clean slate: the places of the former role
    must have been revoked, one table at a time."""
    if SyndicatAssignmentService.active_count(user):
        raise _still_assigned("syndicat")
    if PropertyAssignmentService.active_count(user):
        raise _still_assigned("property")
    if BuildingAssignmentService.active_count(user):
        raise _still_assigned("building")


def _still_assigned(table: str) -> BusinessRuleViolation:
    return BusinessRuleViolation(
        f"Revoke the {table} assignments of this account before changing its role.",
        code="active_assignments",
        details={"assignments": table},
    )


def _check_can_change_role(actor, user, new_role: str) -> None:
    if not can_change_role(actor, user, new_role):
        raise PermissionDenied(
            f"You cannot turn this {user.role} account into a {new_role} account."
        )
    if not AccountPolicy.can_view(actor, user):
        raise NotFound("User not found.")


class RoleService:
    @staticmethod
    @transaction.atomic
    def set_role(*, actor, user, role: str):
        """Give the account `role`. Nothing happens when it already has it."""
        if role not in StructuralRole.values:
            raise InvalidInput("Unknown role.", field="role")
        user = User.objects.select_for_update().get(pk=user.pk)
        _check_can_change_role(actor, user, role)  # after the lock: judged on the current role
        if not user.is_active or user.is_technical_account:
            raise BusinessRuleViolation("The role of this account cannot be changed.")
        if role == user.role:
            return user
        _refuse_while_still_assigned(user)
        if user.role == StructuralRole.ADMIN:
            others = User.objects.filter(role=StructuralRole.ADMIN, is_active=True).exclude(
                pk=user.pk
            )
            if not others.exists():
                raise BusinessRuleViolation(
                    "The last platform administrator cannot lose that role.", code="last_admin"
                )
        previous = user.role
        user.role = role
        user.save(update_fields=["role", "updated_at"])
        AuditService.record(
            actor=actor,
            action=RoleAudit.CHANGED,
            target=user,
            metadata={"user_id": user.pk, "from": previous, "to": role},
        )
        if role == StructuralRole.PROVIDER:
            ProviderProfileService.ensure_exists(user=user)
        notices.role_changed(user, actor=actor)
        return user

    @staticmethod
    @transaction.atomic
    def bootstrap_platform_admin(*, user):
        """Out-of-band promotion to platform admin (management commands only)."""
        user = User.objects.select_for_update().get(pk=user.pk)
        if user.role == StructuralRole.ADMIN:
            return user
        _refuse_while_still_assigned(user)
        previous = user.role
        user.role = StructuralRole.ADMIN
        user.save(update_fields=["role", "updated_at"])
        AuditService.record(
            actor=None,
            action=RoleAudit.CHANGED,
            target=user,
            metadata={"from": previous, "to": user.role, "via": "bootstrap"},
        )
        return user
