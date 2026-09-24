"""Rate limits of the authentication endpoints.

`auth` counts per client address on every authentication endpoint; `login`
also counts per account, so guessing one account's password from many
addresses is slowed down too. Rates are in `REST_FRAMEWORK["DEFAULT_THROTTLE_RATES"]`.
"""

from rest_framework.throttling import ScopedRateThrottle, SimpleRateThrottle

from apps.accounts.services.passwords import normalize_email


class PerAccountLoginThrottle(SimpleRateThrottle):
    scope = "login"

    def get_cache_key(self, request, view) -> str | None:
        email = request.data.get("email") if hasattr(request.data, "get") else None
        if not isinstance(email, str) or not email.strip():
            return None
        return self.cache_format % {"scope": self.scope, "ident": normalize_email(email)}


class AuthThrottleMixin:
    throttle_classes = [ScopedRateThrottle]
    throttle_scope = "auth"


class LoginThrottleMixin:
    throttle_classes = [ScopedRateThrottle, PerAccountLoginThrottle]
    throttle_scope = "auth"
