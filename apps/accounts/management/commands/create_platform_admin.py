"""Bootstrap the first platform administrator (out-of-band, no API equivalent)."""

import getpass

from django.contrib.auth import get_user_model
from django.core.management.base import BaseCommand, CommandError
from django.db import transaction

from apps.accounts.services.passwords import PasswordService
from apps.accounts.services.roles import RoleService
from apps.common.exceptions import DomainError
from apps.notifications.services import PreferenceService

User = get_user_model()


class Command(BaseCommand):
    help = "Create (or promote) a user as platform administrator."

    def add_arguments(self, parser):
        parser.add_argument("--email", required=True)
        parser.add_argument("--first-name", default="Platform")
        parser.add_argument("--last-name", default="Admin")
        parser.add_argument("--password", help="Prompted when omitted for a new account.")

    @transaction.atomic
    def handle(
        self, *args, email: str, first_name: str, last_name: str, password: str | None, **options
    ):
        email = email.strip().lower()
        user = User.objects.filter(email__iexact=email).first()
        if user is None:
            user = User.objects.create_user(email=email, first_name=first_name, last_name=last_name)
            password = password or getpass.getpass("Password: ")
            try:
                PasswordService.apply_new_password(user, password)
            except DomainError as exc:
                raise CommandError(exc.message) from exc
        RoleService.bootstrap_platform_admin(user=user)
        PreferenceService.auto_setup(user)
        self.stdout.write(self.style.SUCCESS(f"{email} is a platform administrator."))
