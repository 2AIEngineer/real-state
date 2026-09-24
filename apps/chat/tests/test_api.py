import pytest

from tests import factories as f

pytestmark = pytest.mark.django_db


def test_conversation_over_http(api, world):
    sr = (
        api(world.tenant, world.syndicat, world.prop)
        .post("/api/v1/service-requests/", {"title": "Q", "description": "?"}, format="json")
        .json()
    )
    room = (
        api(world.tenant, world.syndicat, world.prop)
        .post(
            "/api/v1/chat/rooms/",
            {"context_type": "service_request", "context_id": sr["id"]},
            format="json",
        )
        .json()
    )
    sent = api(world.tenant, world.syndicat, world.prop).post(
        f"/api/v1/chat/rooms/{room['id']}/messages/",
        {"body": "Photo", "media": f.png()},
        format="multipart",
    )
    assert sent.status_code == 201 and sent.json()["media"]["mime_type"] == "image/png"
    rooms = (
        api(world.manager, world.syndicat, world.prop).get("/api/v1/chat/rooms/").json()["results"]
    )
    assert rooms[0]["unread_count"] == 1 and rooms[0]["context_type"] == "service_request"
    assert (
        api(world.outsider, world.syndicat, world.prop)
        .get(f"/api/v1/chat/rooms/{room['id']}/messages/")
        .status_code
        == 404
    )


def test_edit_and_delete_a_message_over_http(api, world):
    client = api(world.tenant, world.syndicat, world.prop)
    sr = client.post(
        "/api/v1/service-requests/", {"title": "Q", "description": "?"}, format="json"
    ).json()
    room = client.post(
        "/api/v1/chat/rooms/",
        {"context_type": "service_request", "context_id": sr["id"]},
        format="json",
    ).json()
    message = client.post(
        f"/api/v1/chat/rooms/{room['id']}/messages/", {"body": "Typo"}, format="json"
    ).json()

    edited = client.patch(
        f"/api/v1/chat/rooms/{room['id']}/messages/{message['id']}/",
        {"body": "Fixed"},
        format="json",
    )
    assert (
        edited.status_code == 200
        and edited.json()["body"] == "Fixed"
        and edited.json()["edited_at"]
    )

    assert (
        api(world.manager, world.syndicat, world.prop)
        .patch(
            f"/api/v1/chat/rooms/{room['id']}/messages/{message['id']}/",
            {"body": "Nope"},
            format="json",
        )
        .status_code
        == 403
    )
    assert (
        client.delete(f"/api/v1/chat/rooms/{room['id']}/messages/{message['id']}/").status_code
        == 204
    )
