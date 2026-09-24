import pytest

pytestmark = pytest.mark.django_db


def test_inbox_and_preferences(api, world):
    client = api(world.tenant)
    inbox = client.get("/api/v1/notifications/", {"unread": "true"}).json()
    assert inbox["count"] >= 1  # the lease creation notified the tenant
    first = inbox["results"][0]["id"]
    assert client.post(f"/api/v1/notifications/{first}/read/").json()["is_read"] is True
    prefs = client.patch(
        "/api/v1/notifications/preferences/", {"chat_enabled": False}, format="json"
    ).json()
    assert prefs["chat_enabled"] is False and prefs["enabled_push"] is True


def test_push_token_registration(api, world):
    client = api(world.tenant)
    response = client.post(
        "/api/v1/notifications/push-tokens/",
        {"device_id": "pixel", "expo_push_token": "ExponentPushToken[xyz]", "platform": "android"},
        format="json",
    )
    assert response.status_code == 200
    assert client.delete("/api/v1/notifications/push-tokens/pixel/").status_code == 204
