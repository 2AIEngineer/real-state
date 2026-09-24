"""Choosing, resetting and changing passwords."""

from __future__ import annotations

from django.contrib.auth import get_user_model, password_validation
from django.core.exceptions import ValidationError as DjangoValidationError
from django.db import transaction
from django.utils import timezone
from django.utils.encoding import force_str
from django.utils.http import urlsafe_base64_decode

from apps.accounts import notices
from apps.accounts.audit import AccountAudit
from apps.accounts.services import setup_links
from apps.accounts.services.tokens import TokenService
from apps.common.exceptions import InvalidInput, PermissionDenied
from apps.common.services.audit import AuditService

User = get_user_model()


def normalize_email(email: str) -> str:
    return User.objects.normalize_email(email.strip()).lower()


class PasswordService:
    @staticmethod
    def apply_new_password(user, password: str) -> None:
        try:
            password_validation.validate_password(password, user)
        except DjangoValidationError as exc:
            raise InvalidInput(
                " ".join(exc.messages), field="password", code="weak_password"
            ) from exc
        user.set_password(password)
        user.password_changed_at = timezone.now()
        user.save(update_fields=["password", "password_changed_at", "updated_at"])
        # Every session opened with the previous password ends here.
        TokenService.revoke_all(user=user)

    @staticmethod
    def request_reset(*, email: str) -> None:
        """Always silent: the caller never learns whether the address exists."""
        user = User.objects.filter(
            email__iexact=normalize_email(email),
            is_active=True,
            is_technical_account=False,
        ).first()
        if user is not None:
            notices.password_setup(user, first_time=not user.has_usable_password())

    @staticmethod
    @transaction.atomic
    def set_password_with_token(*, uid: str, token: str, password: str):
        """Complete an invitation or a reset with the link received by e-mail."""
        try:
            user_id = int(force_str(urlsafe_base64_decode(uid)))
        except (TypeError, ValueError, OverflowError):
            raise _invalid_link() from None
        user = User.objects.filter(pk=user_id, is_active=True, is_technical_account=False).first()
        if user is None or not setup_links.is_valid(user, token):
            raise _invalid_link()
        first_activation = not user.has_usable_password()
        PasswordService.apply_new_password(user, password)
        AuditService.record(actor=user, action=AccountAudit.PASSWORD_SET, target=user)
        if not first_activation:
            notices.critical_change(
                user,
                title="Mot de passe modifié",
                body="Le mot de passe de votre compte vient d'être réinitialisé.",
            )
        return user

    @staticmethod
    @transaction.atomic
    def change_password(*, actor, user, current_password: str, new_password: str):
        """Only the holder changes their own password, and only by giving the
        current one. Someone else sends a new invitation instead."""
        if actor.pk != user.pk:
            raise PermissionDenied(
                "Only the account holder changes their own password; send a new invitation instead."
            )
        if not user.check_password(current_password):
            raise PermissionDenied("Current password is incorrect.", code="invalid_password")
        PasswordService.apply_new_password(user, new_password)
        AuditService.record(actor=user, action=AccountAudit.PASSWORD_CHANGED, target=user)
        notices.critical_change(
            user,
            title="Mot de passe modifié",
            body="Le mot de passe de votre compte vient d'être modifié.",
        )
        return user


def _invalid_link() -> InvalidInput:
    return InvalidInput("This link is invalid or has expired.", code="invalid_token")
