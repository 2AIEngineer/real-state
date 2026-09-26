"""Non-interactive, idempotent bootstrap of the first platform administrator.

Runs at every container start (scripts/startup.sh). Reads DJANGO_SUPERUSER_EMAIL and
DJANGO_SUPERUSER_PASSWORD; does nothing when they are not set, and never
resets the password of an existing account.
"""

import os

from django.contrib.auth import get_user_model
from django.core.management.base import BaseCommand
from django.db import transaction

from apps.accounts.services.passwords import PasswordService
from apps.accounts.services.roles import RoleService
from apps.common.exceptions import DomainError
from apps.notifications.services import PreferenceService

User = get_user_model()


class Command(BaseCommand):
    help = "Ensure the platform administrator defined by DJANGO_SUPERUSER_* exists."

    @transaction.atomic
    def handle(self, *args, **options):
        email = (os.environ.get("DJANGO_SUPERUSER_EMAIL") or "").strip().lower()
        password = os.environ.get("DJANGO_SUPERUSER_PASSWORD") or ""
        if not email:
            self.stdout.write("DJANGO_SUPERUSER_EMAIL not set: skipping.")
            return
        if not password:
            self.stderr.write("DJANGO_SUPERUSER_PASSWORD not set: cannot create the administrator.")
            return
        user = User.objects.filter(email__iexact=email).first()
        if user and user.is_active:
            self.stdout.write(f"{email} is already a superuser.")
            return
        user = User.objects.create_superuser(
            email=email,
            first_name="Super",
            last_name="User",
        )
        try:
            PasswordService.apply_new_password(user, password)
        except DomainError as exc:
            # Never block the container start: log and roll back.
            transaction.set_rollback(True)
            self.stderr.write(f"Administrator not created: {exc.message}")
            return
        self.stdout.write(f"Created administrator {email}.")
        RoleService.bootstrap_platform_admin(user=user)
        PreferenceService.auto_setup(user)
        self.stdout.write(f"{email} holds the platform admin role.")
