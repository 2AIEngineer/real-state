"""A session ends on sign-out, on a password change and on deactivation."""

import pytest
from rest_framework.test import APIClient

from apps.accounts.services.passwords import PasswordService
from apps.accounts.services.status import AccountStatusService

pytestmark = pytest.mark.django_db

PASSWORD = "Old-Passw0rd!x"


def login(user) -> dict:
    user.set_password(PASSWORD)
    user.save()
    body = {"email": user.email, "password": PASSWORD}
    return APIClient().post("/api/v1/auth/token/", body).json()["credentials"]


def refresh(token: str):
    return APIClient().post("/api/v1/auth/token/refresh/", {"refresh": token})


def me(access: str):
    client = APIClient()
    client.credentials(HTTP_AUTHORIZATION=f"Bearer {access}")
    return client.get("/api/v1/users/me/")


def change_password(user):
    PasswordService.change_password(
        actor=user, user=user, current_password=PASSWORD, new_password="N3w-Passw0rd!zz"
    )


def test_a_rotated_refresh_token_cannot_be_reused(world):
    token = login(world.tenant)["refresh_token"]

    assert refresh(token).status_code == 200
    assert refresh(token).status_code == 401


def test_signing_out_ends_the_session(world):
    token = login(world.tenant)["refresh_token"]

    assert APIClient().post("/api/v1/auth/logout/", {"refresh": token}).status_code == 204
    assert refresh(token).status_code == 401


def test_a_password_change_ends_every_session(world):
    credentials = login(world.tenant)
    change_password(world.tenant)

    assert me(credentials["access_token"]).status_code == 401
    assert refresh(credentials["refresh_token"]).status_code == 401


def test_a_deactivation_ends_every_session(world):
    credentials = login(world.tenant)
    world.lease.members.filter(user=world.tenant).delete()  # no obligation left
    AccountStatusService.deactivate(actor=world.admin, user=world.tenant)

    assert me(credentials["access_token"]).status_code == 401
    assert refresh(credentials["refresh_token"]).status_code == 401
