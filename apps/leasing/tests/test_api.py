import datetime as dt

import pytest

from tests import factories as f

pytestmark = pytest.mark.django_db


def test_create_lease_with_members_and_extras(api, world):
    tenant = f.make_user()
    response = api(world.manager, world.syndicat, world.prop).post(
        "/api/v1/leases/",
        {
            "unit_id": world.other_unit.pk,
            "start_date": str(dt.date.today()),
            "members": [
                {
                    "user_id": tenant.pk,
                    "is_signatory": True,
                    "vehicles_info": [{"plate_number": "AB-123-CD"}],
                }
            ],
        },
        format="json",
    )
    assert response.status_code == 201
    assert response.json()["members"][0]["vehicles_info"] == [{"plate_number": "AB-123-CD"}]


def test_overlap_answers_409_with_a_stable_code(api, world):
    response = api(world.manager, world.syndicat, world.prop).post(
        "/api/v1/leases/",
        {
            "unit_id": world.unit.pk,
            "start_date": str(dt.date.today()),
            "members": [{"user_id": f.make_user().pk, "is_signatory": True}],
        },
        format="json",
    )
    assert response.status_code == 409 and response.json()["error"]["code"] == "lease_overlap"


def test_tenant_uploads_own_identity_proof(api, world):
    member = world.lease.members.get(user=world.tenant)
    response = api(world.tenant, world.syndicat, world.prop).patch(
        f"/api/v1/lease-members/{member.pk}/proof-of-identity/",
        {"file": f.pdf()},
        format="multipart",
    )
    assert (
        response.status_code == 200
        and response.json()["proof_of_identity"]["mime_type"] == "application/pdf"
    )
    proof = response.json()["proof_of_identity"]
    assert proof["url"].endswith(".pdf") and proof["entity_type"] == "lease_member_identity"
