import pytest

pytestmark = pytest.mark.django_db


def login(api, email, password="Str0ng-Passw0rd!"):
    return api().post("/api/v1/auth/token/", {"email": email, "password": password}, format="json")


def test_login_is_case_insensitive_and_returns_the_session(api, world):
    response = login(api, "TENANT@Example.test")
    assert response.status_code == 200
    session = response.json()
    assert set(session) == {"credentials", "ui_config", "user"}
    assert session["credentials"]["access_token"] and session["credentials"]["refresh_token"]
    assert session["user"]["email"] == "tenant@example.test"


def test_the_session_leaves_null_what_only_the_client_can_decide(api, world):
    ui_config = login(api, "tenant@example.test").json()["ui_config"]
    assert ui_config["app_mode"] is None and ui_config["step"] is None
    assert ui_config["syndicat"] == {"id": None, "name": None, "logo_url": None}
    prop = ui_config["property"]
    assert prop["id"] is None and prop["name"] is None and prop["logo_url"] is None
    assert len(prop["features"]) == 11 and not any(prop["features"].values())
    assert "include_service_request" in prop["features"] and "include_chat" in prop["features"]


def test_exactly_one_role_flag_is_true(api, world):
    role = login(api, "manager@example.test").json()["user"]["role"]
    flags = {k: v for k, v in role.items() if k.startswith("is_")}
    assert flags["is_manager"] is True
    assert sum(flags.values()) == 1 and len(flags) == 8
    assert role["label"] == "Manager"


def test_the_session_lists_what_the_user_owns_and_rents(api, world):
    tenant = login(api, "tenant@example.test").json()["user"]["assets"]
    assert tenant["user_status"] == {"is_owner": False, "is_tenant": True}
    assert tenant["ownerships"] == []
    (tenancy,) = tenant["tenancies"]
    assert tenancy["unit_id"] == world.unit.pk and tenancy["unit_number"] == "A101"
    assert tenancy["lease_id"] == world.lease.pk and tenancy["is_signatory"] is True

    owner = login(api, "owner@example.test").json()["user"]["assets"]
    assert owner["user_status"] == {"is_owner": True, "is_tenant": False}
    (ownership,) = owner["ownerships"]
    assert ownership["unit_id"] == world.unit.pk and ownership["ownership_share"] == "100.00"
    assert owner["tenancies"] == []


def test_technical_account_cannot_log_in(api, world):
    rep = world.prop.promoter.representative_user
    response = api().post(
        "/api/v1/auth/token/", {"email": rep.email, "password": "anything"}, format="json"
    )
    assert response.status_code == 401


def test_manager_creates_account(api, world):
    response = api(world.manager, syndicat=world.syndicat, prop=world.prop).post(
        "/api/v1/users/",
        {
            "email": "new@example.test",
            "first_name": "N",
            "last_name": "U",
            "tenancy": {"unit_id": world.unit.pk},
        },
        format="json",
    )
    assert response.status_code == 201 and response.json()["is_activated"] is False


def test_a_standard_account_without_a_unit_is_refused(api, world):
    response = api(world.manager, syndicat=world.syndicat, prop=world.prop).post(
        "/api/v1/users/",
        {"email": "nowhere@example.test", "first_name": "N", "last_name": "U"},
        format="json",
    )
    assert (
        response.status_code == 400
        and response.json()["error"]["code"] == "ownership_or_tenancy_required"
    )


def test_an_owner_is_registered_with_the_units_bought(api, world):
    response = api(world.manager, syndicat=world.syndicat, prop=world.prop).post(
        "/api/v1/users/",
        {
            "email": "buyer@example.test",
            "first_name": "B",
            "last_name": "U",
            "ownerships": [{"unit_id": world.other_unit.pk}],
        },
        format="json",
    )
    assert response.status_code == 201
    history = (
        api(world.manager, world.syndicat, world.prop)
        .get(f"/api/v1/units/{world.other_unit.pk}/ownerships/")
        .json()
    )
    active = [row for row in history["results"] if row["status"] == "ACTIVE"]
    assert [row["owner"]["id"] for row in active] == [response.json()["id"]]


def test_an_account_reads_and_edits_itself_as_me(api, world):
    client = api(world.tenant)
    assert client.get("/api/v1/users/me/").json()["email"] == "tenant@example.test"
    patched = client.patch("/api/v1/users/me/", {"first_name": "Renamed"}, format="json")
    assert patched.status_code == 200 and patched.json()["first_name"] == "Renamed"
    # The same endpoint, by id, answers the same thing.
    assert client.get(f"/api/v1/users/{world.tenant.pk}/").json()["first_name"] == "Renamed"


def test_only_the_holder_changes_a_password(api, world):
    body = {"current_password": "Str0ng-Passw0rd!", "new_password": "An0ther-Str0ng-Pass!"}
    refused = api(world.manager).post(
        f"/api/v1/users/{world.tenant.pk}/password/", body, format="json"
    )
    assert refused.status_code == 403
    assert (
        api(world.tenant).post("/api/v1/users/me/password/", body, format="json").status_code == 204
    )


def test_password_reset_never_reveals_accounts(api, world):
    assert (
        api()
        .post("/api/v1/auth/password/reset/", {"email": "nobody@example.test"}, format="json")
        .status_code
        == 202
    )
