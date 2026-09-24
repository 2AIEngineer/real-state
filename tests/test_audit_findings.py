"""Findings of the 2026-09 audit (docs/AUDIT.md), written as the behaviour we want.

Each test is `xfail(strict=True)`: it fails today because the defect is real.
Once the defect is fixed the test passes, strict mode turns that into a
failure, and the marker must be removed — the test then guards the fix.
"""

import pytest
from django.core.cache import cache
from rest_framework.test import APIClient

from apps.accounts.enums import StructuralRole
from apps.accounts.services.passwords import PasswordService
from tests import factories as f

pytestmark = pytest.mark.django_db


def _submit(api, world, **extra):
    body = {"title": "Leak", "description": "Sink", **extra}
    fmt = "multipart" if "files" in extra else "json"
    return api(world.tenant, world.syndicat, world.prop).post(
        "/api/v1/service-requests/", body, format=fmt
    )


@pytest.mark.xfail(strict=True, reason="AUDIT S1: detail routes ignore X-Property-Id")
def test_a_record_is_not_reachable_under_another_selected_property(api, world):
    other = f.make_property(syndicat=world.syndicat, name="Other")
    f.assign_role(world.manager, StructuralRole.MANAGER, other)
    sr_id = _submit(api, world).json()["id"]

    response = api(world.manager, world.syndicat, other).get(f"/api/v1/service-requests/{sr_id}/")

    assert response.status_code == 404


@pytest.mark.xfail(strict=True, reason="AUDIT S1: the syndicat header is never checked on lists")
def test_a_foreign_syndicat_header_is_rejected(api, world):
    foreign = f.make_syndicat(name="Foreign")

    response = api(world.manager, foreign, world.prop).get("/api/v1/service-requests/")

    assert response.status_code in (400, 404)


@pytest.mark.xfail(strict=True, reason="AUDIT S4: tokens outlive a password change")
def test_a_password_change_revokes_existing_tokens(world):
    world.tenant.set_password("Old-Passw0rd!x")
    world.tenant.save()
    login = APIClient().post(
        "/api/v1/auth/token/", {"email": world.tenant.email, "password": "Old-Passw0rd!x"}
    )
    refresh = login.json()["credentials"]["refresh_token"]
    PasswordService.change_password(
        actor=world.tenant,
        user=world.tenant,
        current_password="Old-Passw0rd!x",
        new_password="N3w-Passw0rd!zz",
    )

    response = APIClient().post("/api/v1/auth/token/refresh/", {"refresh": refresh})

    assert response.status_code == 401


@pytest.mark.xfail(strict=True, reason="AUDIT S4: rotated refresh tokens stay valid")
def test_a_rotated_refresh_token_cannot_be_reused(world):
    world.tenant.set_password("Old-Passw0rd!x")
    world.tenant.save()
    login = APIClient().post(
        "/api/v1/auth/token/", {"email": world.tenant.email, "password": "Old-Passw0rd!x"}
    )
    refresh = login.json()["credentials"]["refresh_token"]
    assert APIClient().post("/api/v1/auth/token/refresh/", {"refresh": refresh}).status_code == 200

    response = APIClient().post("/api/v1/auth/token/refresh/", {"refresh": refresh})

    assert response.status_code == 401


@pytest.mark.xfail(strict=True, reason="AUDIT S5: X-Forwarded-For resets the auth throttle")
def test_the_auth_throttle_ignores_a_spoofed_forwarded_for(world):
    cache.clear()
    codes = {
        APIClient()
        .post(
            "/api/v1/auth/password/reset/",
            {"email": "nobody@example.test"},
            HTTP_X_FORWARDED_FOR=f"10.0.0.{i}",
        )
        .status_code
        for i in range(30)
    }

    assert 429 in codes
