import pytest
from django.core.cache import cache
from rest_framework.test import APIClient

from apps.accounts.throttles import PerAccountLoginThrottle

pytestmark = pytest.mark.django_db

PLATFORM_SEES = "203.0.113.9"  # appended by the ingress: the real client address


@pytest.fixture(autouse=True)
def _fresh_counters():
    cache.clear()
    yield
    cache.clear()


def test_a_forwarded_for_sent_by_the_client_does_not_reset_the_counter(settings):
    settings.REST_FRAMEWORK = {**settings.REST_FRAMEWORK, "NUM_PROXIES": 1}
    codes = {
        APIClient()
        .post(
            "/api/v1/auth/password/reset/",
            {"email": "nobody@example.test"},
            HTTP_X_FORWARDED_FOR=f"10.0.0.{i}, {PLATFORM_SEES}",
        )
        .status_code
        for i in range(30)
    }

    assert 429 in codes


def test_login_attempts_are_counted_per_account_whatever_the_address(world, settings, monkeypatch):
    settings.REST_FRAMEWORK = {**settings.REST_FRAMEWORK, "NUM_PROXIES": 1}
    # Rates are read once, when the throttle classes are defined.
    monkeypatch.setattr(PerAccountLoginThrottle, "THROTTLE_RATES", {"login": "3/min"})
    codes = [
        APIClient()
        .post(
            "/api/v1/auth/token/",
            {"email": world.tenant.email.upper(), "password": "wrong"},
            HTTP_X_FORWARDED_FOR=f"198.51.100.{i}",
        )
        .status_code
        for i in range(5)
    ]

    assert codes[:3] == [401, 401, 401] and codes[3:] == [429, 429]
