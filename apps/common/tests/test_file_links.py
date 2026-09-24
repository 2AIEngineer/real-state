"""Signed links: usable as they are, personal for private files, never expiring on a timer."""

import time
from unittest import mock

import pytest
from django.utils import timezone
from rest_framework.test import APIClient

from apps.accounts.services.passwords import PasswordService
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


def test_a_private_link_never_changes_nor_expires(world):
    attachment = attach(world, EntityType.SERVICE_REQUEST, 1, f.pdf())
    path = links.path_of(attachment, world.tenant)

    with mock.patch("time.time", return_value=time.time() + 365 * 24 * 3600):
        assert links.path_of(attachment, world.tenant) == path
        assert get(path).status_code == 200


def test_a_private_link_is_personal(world):
    attachment = attach(world, EntityType.SERVICE_REQUEST, 1, f.pdf())

    assert links.path_of(attachment, world.tenant) != links.path_of(attachment, world.manager)


def test_a_public_link_never_expires_and_is_the_same_for_everyone(world):
    logo = attach(world, EntityType.PROPERTY_LOGO, world.prop.pk, f.png())

    path = links.path_of(logo, world.tenant)

    assert path == links.path_of(logo, world.manager) == links.path_of(logo, None)
    assert get(path)["Cache-Control"].startswith("public, max-age=")


def test_a_tampered_link_is_unknown(world):
    attachment = attach(world, EntityType.SERVICE_REQUEST, 1, f.pdf())
    token = links.token_of(links.FileLink(attachment.pk, world.tenant.pk))
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


def test_a_link_dies_when_the_reader_changes_password(world):
    attachment = attach(world, EntityType.SERVICE_REQUEST, 1, f.pdf())
    world.tenant.set_password("Old-Passw0rd!x")
    world.tenant.save()
    path = links.path_of(attachment, world.tenant)
    PasswordService.change_password(
        actor=world.tenant,
        user=world.tenant,
        current_password="Old-Passw0rd!x",
        new_password="N3w-Passw0rd!zz",
    )

    assert get(path).status_code == 404
    assert get(links.path_of(attachment, world.tenant)).status_code == 200


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


def test_with_a_storage_service_the_link_redirects_to_a_short_storage_url(world, monkeypatch):
    attachment = attach(world, EntityType.SERVICE_REQUEST, 1, f.pdf("scan.pdf"))
    signed = {}

    def signed_url(name, **options):
        signed.update(options)
        return "https://acct.blob.core.windows.net/files/x.pdf?sig=abc"

    monkeypatch.setattr(attachment.file.storage, "signed_url", signed_url, raising=False)

    response = get(links.path_of(attachment, world.tenant))

    assert response.status_code == 302 and response["Location"].endswith("?sig=abc")
    assert signed["content_type"] == "application/pdf"
    assert signed["expires_at"] - time.time() > 3600  # the browser follows it at once
