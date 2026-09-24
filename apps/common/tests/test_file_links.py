"""Signed links: usable as they are, personal for private files, bounded in time."""

import time

import pytest
from django.utils import timezone
from rest_framework.test import APIClient

from apps.common.files import links
from apps.common.files.rules import EntityType
from apps.common.files.service import AttachmentService
from tests import factories as f

pytestmark = pytest.mark.django_db


def attach(world, entity_type, entity_id, upload):
    (attachment,) = AttachmentService.attach(
        entity_type=entity_type, entity_id=entity_id, files=[upload], uploaded_by=world.admin
    )
    return attachment


def get(path):
    return APIClient().get(path)


def test_a_private_link_opens_the_file_without_any_header(world):
    attachment = attach(world, EntityType.SERVICE_REQUEST, 1, f.pdf("scan.pdf"))

    response = get(links.path_of(attachment, world.tenant))

    assert response.status_code == 200
    assert response["Content-Type"] == "application/pdf"
    assert response["Content-Disposition"] == "inline; filename*=UTF-8''scan.pdf"
    assert response["Cache-Control"].startswith("private, max-age=")
    assert b"".join(response.streaming_content).startswith(b"%PDF")


def test_a_file_is_served_as_its_detected_format_whatever_its_name(world):
    attachment = attach(world, EntityType.SERVICE_REQUEST, 1, f.pdf("evil.html"))

    response = get(links.path_of(attachment, world.tenant))

    assert response["Content-Type"] == "application/pdf"


def test_a_private_link_is_stable_within_a_window(world):
    attachment = attach(world, EntityType.SERVICE_REQUEST, 1, f.pdf())

    assert links.path_of(attachment, world.tenant) == links.path_of(attachment, world.tenant)


def test_a_private_link_is_personal(world):
    attachment = attach(world, EntityType.SERVICE_REQUEST, 1, f.pdf())

    assert links.path_of(attachment, world.tenant) != links.path_of(attachment, world.manager)


def test_a_public_link_never_expires_and_is_the_same_for_everyone(world):
    logo = attach(world, EntityType.PROPERTY_LOGO, world.prop.pk, f.png())

    path = links.path_of(logo, world.tenant)

    assert path == links.path_of(logo, world.manager) == links.path_of(logo, None)
    assert get(path)["Cache-Control"].startswith("public, max-age=")


def test_an_expired_link_is_refused(world):
    attachment = attach(world, EntityType.SERVICE_REQUEST, 1, f.pdf())
    token = links.token_of(links.FileLink(attachment.pk, world.tenant.pk, int(time.time()) - 1))

    response = get(f"/api/v1/files/{token}/")

    assert response.status_code == 403 and response.json()["error"]["code"] == "link_expired"


def test_a_tampered_link_is_unknown(world):
    attachment = attach(world, EntityType.SERVICE_REQUEST, 1, f.pdf())
    token = links.token_of(links.FileLink(attachment.pk, world.tenant.pk, 2**40))
    forged = token.replace(str(world.tenant.pk), str(world.manager.pk), 1)

    assert get(f"/api/v1/files/{forged}/").status_code == 404
    assert get(f"/api/v1/files/{attachment.pk}/").status_code == 404


def test_a_link_dies_with_the_reader_account(world):
    attachment = attach(world, EntityType.SERVICE_REQUEST, 1, f.pdf())
    path = links.path_of(attachment, world.tenant)
    type(world.tenant).objects.filter(pk=world.tenant.pk).update(
        is_active=False, deactivated_at=timezone.now()
    )

    assert get(path).status_code == 404


def test_stored_files_are_not_served_by_path(world):
    attachment = attach(world, EntityType.SERVICE_REQUEST, 1, f.pdf())

    assert get(f"/media/{attachment.file.name}").status_code == 404


def test_api_responses_hand_out_signed_links(api, world):
    response = api(world.tenant, world.syndicat, world.prop).post(
        "/api/v1/service-requests/",
        {"title": "Leak", "description": "Sink", "files": [f.pdf()]},
        format="multipart",
    )

    url = response.json()["files"][0]["url"]

    assert url.startswith("http://testserver/api/v1/files/")
    assert get(url.removeprefix("http://testserver")).status_code == 200
