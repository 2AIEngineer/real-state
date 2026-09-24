import pytest

from tests import factories as f

pytestmark = pytest.mark.django_db


def test_publish_with_files_and_read_as_tenant(api, world):
    response = api(world.manager, world.syndicat, world.prop).post(
        "/api/v1/announcements/",
        {"title": "AGM", "body": "Friday", "target_roles": ["tenant", "owner"], "files": [f.pdf()]},
        format="multipart",
    )
    assert response.status_code == 201
    listing = api(world.tenant, world.syndicat, world.prop).get("/api/v1/announcements/").json()
    assert (
        listing["count"] == 1
        and listing["results"][0]["files"][0]["original_filename"] == "doc.pdf"
    )
    # The file is read straight from its URL, without another API call.
    file_url = listing["results"][0]["files"][0]["url"]
    download = api(world.tenant).get(file_url)
    assert download.status_code == 200 and b"".join(download.streaming_content).startswith(b"%PDF")
