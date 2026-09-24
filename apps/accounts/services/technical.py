"""Technical accounts: non-human accounts (a promoter's representative) that can never log in."""

from __future__ import annotations

from django.contrib.auth import get_user_model
from django.db import transaction

from apps.accounts import errors
from apps.accounts.services.passwords import normalize_email

User = get_user_model()


class TechnicalAccountService:
    @staticmethod
    @transaction.atomic
    def create(*, actor, email: str, display_name: str):
        email = normalize_email(email)
        if User.objects.filter(email__iexact=email).exists():
            raise errors.email_taken()
        return User.objects.create_user(
            email=email,
            password=None,
            first_name=display_name[:150],
            last_name="",
            is_technical_account=True,
            created_by=actor,
        )
