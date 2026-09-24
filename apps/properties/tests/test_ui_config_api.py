"""The three steps a client walks through after logging in, over HTTP."""

import pytest

from tests import factories as f

pytestmark = pytest.mark.django_db


def test_the_three_steps_over_http(api, world):
    """syndicat -> property -> dashboard, each carrying the headers of its step."""
    syndicats = api(world.manager, step="syndicat").get("/api/v1/ui-config/syndicats/").json()
    assert [s["id"] for s in syndicats] == [world.syndicat.pk]
    assert syndicats[0]["accessible_properties_count"] == 1

    properties = (
        api(world.manager, syndicat=world.syndicat, step="property")
        .get("/api/v1/ui-config/properties/")
        .json()
    )
    assert [p["id"] for p in properties] == [world.prop.pk]

    # The dashboard itself: any dashboard endpoint now answers, headers all present.
    statistics = api(world.manager, world.syndicat, world.prop).get(
        f"/api/v1/properties/{world.prop.pk}/statistics/"
    )
    assert statistics.status_code == 200


def test_each_configuration_page_answers_at_its_own_step_only(api, world):
    wrong_step = api(world.manager, syndicat=world.syndicat, step="dashboard").get(
        "/api/v1/ui-config/syndicats/"
    )
    assert wrong_step.status_code == 400
    assert wrong_step.json()["error"]["code"] == "wrong_ui_config_step"


def test_the_property_step_requires_a_selected_syndicat(api, world):
    response = api(world.manager, step="property").get("/api/v1/ui-config/properties/")
    assert response.status_code == 400
    assert response.json()["error"]["field"] == "X-Syndicat-Id"


class TestDashboardRequiresTheFullSelection:
    """Once inside the dashboard, an endpoint answers only with all three
    headers present: the syndicat, the property, and the `dashboard` step."""

    url = "/api/v1/announcements/"

    def test_missing_property_is_refused(self, api, world):
        client = api(world.manager, syndicat=world.syndicat)
        client.defaults["HTTP_X_UI_CONFIG_STEP"] = "dashboard"
        response = client.get(self.url)
        assert response.status_code == 400
        assert response.json()["error"]["field"] == "X-Property-Id"

    def test_missing_syndicat_is_refused(self, api, world):
        client = api(world.manager, prop=world.prop)
        client.defaults["HTTP_X_UI_CONFIG_STEP"] = "dashboard"
        response = client.get(self.url)
        assert response.status_code == 400
        assert response.json()["error"]["field"] == "X-Syndicat-Id"

    def test_missing_dashboard_step_is_refused(self, api, world):
        client = api(world.manager, world.syndicat, world.prop, step="property")
        response = client.get(self.url)
        assert response.status_code == 400
        assert response.json()["error"]["code"] == "wrong_ui_config_step"

    def test_all_three_present_succeeds(self, api, world):
        response = api(world.manager, world.syndicat, world.prop).get(self.url)
        assert response.status_code == 200


def test_property_outside_the_selected_syndicat_is_refused(api, world):
    other_syndicat = f.make_syndicat()
    response = api(world.admin, other_syndicat, world.prop).get(
        f"/api/v1/properties/{world.prop.pk}/statistics/"
    )
    assert response.status_code == 400
    assert response.json()["error"]["code"] == "property_outside_syndicat"


def test_the_configuration_pages_return_the_whole_list_without_pagination(api, world):
    for _ in range(25):
        f.make_property(syndicat=world.syndicat)
    properties = (
        api(world.syndic, syndicat=world.syndicat, step="property")
        .get("/api/v1/ui-config/properties/")
        .json()
    )
    assert isinstance(properties, list) and len(properties) == 26  # beyond the page size
