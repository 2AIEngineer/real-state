import io

import pytest
from django.core.management import call_command

from apps.accounts.enums import StructuralRole
from apps.notifications.models import NotificationPreference

pytestmark = pytest.mark.django_db


def test_create_default_superuser_sets_up_preferences(monkeypatch):
    monkeypatch.setenv("DJANGO_SUPERUSER_EMAIL", "root@example.test")
    monkeypatch.setenv("DJANGO_SUPERUSER_PASSWORD", "A-very-long-passw0rd")
    call_command("create_default_superuser", stdout=io.StringIO())
    prefs = NotificationPreference.objects.get(user__email="root@example.test")
    assert prefs.user.role == StructuralRole.ADMIN and prefs.store_enabled is True


def test_create_platform_admin_sets_up_preferences():
    call_command(
        "create_platform_admin",
        email="ops@example.test",
        password="A-very-long-passw0rd",
        stdout=io.StringIO(),
    )
    prefs = NotificationPreference.objects.get(user__email="ops@example.test")
    assert prefs.user.role == StructuralRole.ADMIN and prefs.store_enabled is True
