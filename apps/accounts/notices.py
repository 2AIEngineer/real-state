"""What account holders are told about their account.

These are transactional messages: they bypass the notification preferences.
"""

from __future__ import annotations

from apps.accounts.enums import StructuralRole
from apps.accounts.services import setup_links
from apps.notifications.models import NotificationCategory, Severity
from apps.notifications.services import NotificationIntent, NotificationService


def password_setup(user, *, first_time: bool) -> None:
    """The e-mail with the link to choose a password: an invitation or a reset."""
    hours = setup_links.lifetime_seconds(user) // 3600
    NotificationService.notify(
        NotificationIntent(
            event_type=("account.invited" if first_time else "account.password_reset_requested"),
            category=NotificationCategory.ACCOUNT,
            title=(
                "Bienvenue — activez votre compte"
                if first_time
                else "Réinitialisation de votre mot de passe"
            ),
            body=(
                "Un compte a été créé pour vous. Définissez votre mot de passe pour y accéder."
                if first_time
                else "Une demande de réinitialisation de mot de passe a été reçue. "
                "Si vous n'en êtes pas à l'origine, ignorez ce message."
            ),
            to=[user],
            email_lines=[f"Lien (valable {hours} h) : {setup_links.build(user)}"],
            include_platform_admins=False,
            transactional=True,
            channels=frozenset({"email"}),
        )
    )


def critical_change(user, *, title: str, body: str, extra_emails: tuple[str, ...] = ()) -> None:
    """A change of the login identifier, the password or the status of the account."""
    NotificationService.notify(
        NotificationIntent(
            event_type="account.critical_change",
            category=NotificationCategory.ACCOUNT,
            title=title,
            body=body,
            to=[user],
            severity=Severity.WARNING,
            target=user,
            include_platform_admins=False,
            transactional=True,
        )
    )
    if extra_emails:
        # Previous address after an e-mail change: it must learn about it too.
        NotificationService.notify(
            NotificationIntent(
                event_type="account.critical_change",
                category=NotificationCategory.ACCOUNT,
                title=title,
                body=body,
                to_addresses=extra_emails,
                include_platform_admins=False,
                transactional=True,
                channels=frozenset({"email"}),
            )
        )


def role_changed(user, *, actor) -> None:
    NotificationService.notify(
        NotificationIntent(
            event_type="account.role_changed",
            category=NotificationCategory.ACCOUNT,
            title="Rôle modifié",
            body=f"Votre compte a désormais le rôle « {StructuralRole(user.role).label} ».",
            to=[user],
            target=user,
            severity=Severity.WARNING,
            exclude=[actor] if actor else [],
            include_platform_admins=False,
            transactional=True,
        )
    )
