"""Ending sessions: the JWT pairs handed out at login.

Every refresh token is recorded (`OutstandingToken`) and a used one is
blacklisted as soon as it is rotated. Signing out blacklists the token the
client holds; a password change or a deactivation blacklists every token of
the account, so a stolen session never outlives it. Access tokens carry a
fingerprint of the password (`CHECK_REVOKE_TOKEN`): they stop working at the
same moment.
"""

from __future__ import annotations

from django.utils import timezone
from rest_framework_simplejwt.exceptions import TokenError
from rest_framework_simplejwt.token_blacklist.models import BlacklistedToken, OutstandingToken
from rest_framework_simplejwt.tokens import RefreshToken

from apps.common.exceptions import InvalidInput


class TokenService:
    @staticmethod
    def sign_out(*, refresh_token: str) -> None:
        try:
            RefreshToken(refresh_token).blacklist()
        except TokenError:
            raise InvalidInput("This session token is invalid or expired.", code="invalid_token")

    @staticmethod
    def revoke_all(*, user) -> int:
        """Blacklist every refresh token of the account; returns how many were live."""
        live = OutstandingToken.objects.filter(user=user, blacklistedtoken__isnull=True)
        revoked = BlacklistedToken.objects.bulk_create(
            [BlacklistedToken(token=token) for token in live], ignore_conflicts=True
        )
        return len(revoked)

    @staticmethod
    def flush_expired() -> int:
        """Forget the tokens that expired on their own (they are useless to keep)."""
        deleted, _ = OutstandingToken.objects.filter(expires_at__lte=timezone.now()).delete()
        return deleted
