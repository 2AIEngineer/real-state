import pytest

from tests import factories as f

pytestmark = pytest.mark.django_db


def test_folder_and_document_over_http(api, world):
    manager = api(world.manager, world.syndicat, world.prop)
    folder = manager.post(
        "/api/v1/library/folders/", {"en_name": "Minutes", "fr_name": "Procès"}, format="json"
    )
    assert folder.status_code == 201

    document = manager.post(
        "/api/v1/library/documents/",
        {
            "folder_id": folder.json()["id"],
            "title": "Rules",
            "target_roles": ["tenant"],
            "file": f.pdf(),
        },
        format="multipart",
    )
    assert document.status_code == 201

    seen = api(world.tenant, world.syndicat, world.prop).get("/api/v1/library/documents/")
    assert [d["title"] for d in seen.json()["results"]] == ["Rules"]


def test_a_property_created_over_http_comes_with_its_default_folders(api, world):
    admin = api(world.admin, world.syndicat, world.prop)
    promoter = admin.post(
        "/api/v1/promoters/",
        {"name": "Build Co", "representative_email": "rep@build.test"},
        format="json",
    ).json()
    prop = admin.post(
        "/api/v1/properties/",
        {"syndicat_id": world.syndicat.pk, "promoter_id": promoter["id"], "name": "Palms"},
        format="json",
    ).json()

    folders = api(world.admin, world.syndicat, prop["id"]).get("/api/v1/library/folders/")
    assert folders.status_code == 200 and folders.json()["count"] == 6
