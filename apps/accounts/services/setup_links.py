"""The e-mailed link to choose a password: an invitation, or a reset.

Both use Django's password-reset tokens, which die as soon as the password (or
the last login) changes. They differ in lifetime: an invitation waits for its
first use for days (`PASSWORD_RESET_TIMEOUT`), a reset of an account already
in use is short-lived (`PASSWORD_RESET_LINK_TIMEOUT`).
"""

from __future__ import annotations

from django.conf import settings
from django.contrib.auth.tokens import default_token_generator
from django.utils.encoding import force_bytes
from django.utils.http import base36_to_int, urlsafe_base64_encode


def lifetime_seconds(user) -> int:
    if user.has_usable_password():
        return settings.PASSWORD_RESET_LINK_TIMEOUT
    return settings.PASSWORD_RESET_TIMEOUT


def build(user) -> str:
    uid = urlsafe_base64_encode(force_bytes(user.pk))
    token = default_token_generator.make_token(user)
    return f"{settings.SITE_URL}/auth/set-password?uid={uid}&token={token}"


def is_valid(user, token: str) -> bool:
    """Django checks the signature and the longest lifetime; the reset one is
    checked here from the timestamp the token carries."""
    if not default_token_generator.check_token(user, token):
        return False
    issued_at = base36_to_int(token.split("-")[0])
    age = (
        default_token_generator._num_seconds(default_token_generator._now()) - issued_at
    )
    return age <= lifetime_seconds(user)
