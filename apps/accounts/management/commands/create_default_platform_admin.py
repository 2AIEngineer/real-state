"""Bootstrap the first platform administrator (out-of-band, no API equivalent)."""

import getpass
import os

from django.contrib.auth import get_user_model
from django.core.management.base import BaseCommand, CommandError
from django.db import transaction

from apps.accounts.services.passwords import PasswordService
from apps.accounts.services.roles import RoleService
from apps.common.exceptions import DomainError
from apps.notifications.services import PreferenceService

User = get_user_model()


class Command(BaseCommand):
    help = "Create a user as platform administrator."

    @transaction.atomic
    def handle(self, *args, **options):
        email = (os.environ.get("DJANGO_PLATFORM_ADMIN_EMAIL") or "").strip().lower()
        password = os.environ.get("DJANGO_PLATFORM_ADMIN_PASSWORD") or ""
        user = User.objects.filter(email__iexact=email).first()
        if user and user.is_active:
            self.stdout.write(self.style.SUCCESS(f"{email} is already a platform administrator."))
            return
        user = User.objects.create_user(email=email, first_name="Platform", last_name="Admin")
        password = password or getpass.getpass("Password: ")
        try:
            PasswordService.apply_new_password(user, password)
        except DomainError as exc:
            raise CommandError(exc.message) from exc
        RoleService.bootstrap_platform_admin(user=user)
        PreferenceService.auto_setup(user)
        self.stdout.write(self.style.SUCCESS(f"{email} is a platform administrator."))
