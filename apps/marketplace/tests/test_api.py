import pytest

from tests import factories as f

pytestmark = pytest.mark.django_db


def test_publish_requires_images_over_http(api, world):
    client = api(world.tenant, world.syndicat, world.prop)
    payload = {"category": "various_offer", "title": "Sofa", "description": "Blue", "price": "100"}
    assert (
        client.post("/api/v1/marketplace/listings/", payload, format="multipart").status_code == 400
    )
    created = client.post(
        "/api/v1/marketplace/listings/",
        {**payload, "images": [f.png(), f.png()]},
        format="multipart",
    )
    assert created.status_code == 201 and len(created.json()["images"]) == 2
