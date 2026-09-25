import datetime as dt

import pytest
from django.contrib.auth.tokens import default_token_generator

from apps.accounts.services import setup_links
from tests import factories as f

pytestmark = pytest.mark.django_db


def token_aged(user, monkeypatch, hours: int) -> str:
    token = default_token_generator.make_token(user)
    later = default_token_generator._now() + dt.timedelta(hours=hours)
    monkeypatch.setattr(default_token_generator, "_now", lambda: later)
    return token


@pytest.fixture(autouse=True)
def _lifetimes(settings):
    settings.PASSWORD_RESET_LINK_TIMEOUT = 2 * 3600
    settings.PASSWORD_RESET_TIMEOUT = 72 * 3600


def test_a_reset_link_is_short_lived(monkeypatch):
    user = f.make_user()
    user.set_password("Some-Passw0rd!")
    user.save()

    assert setup_links.is_valid(user, token_aged(user, monkeypatch, hours=1))
    assert not setup_links.is_valid(user, token_aged(user, monkeypatch, hours=3))


def test_an_invitation_waits_for_days(monkeypatch):
    user = f.make_user()
    user.set_unusable_password()
    user.save()

    assert setup_links.is_valid(user, token_aged(user, monkeypatch, hours=48))
