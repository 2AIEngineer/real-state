from __future__ import annotations

from dataclasses import dataclass

import pytest
from rest_framework.test import APIClient

from apps.accounts.enums import StructuralRole
from tests import factories as f


@dataclass
class World:
    """A small but complete residence: one property, two buildings, a few
    people holding each kind of right."""

    admin: object
    syndicat: object
    prop: object
    building: object
    other_building: object
    unit: object
    other_unit: object
    manager: object
    syndic: object
    security: object
    maintenance: object
    owner: object
    tenant: object
    co_tenant: object
    outsider: object
    lease: object


@pytest.fixture(autouse=True)
def _media_root(settings, tmp_path):
    settings.MEDIA_ROOT = tmp_path / "media"


@pytest.fixture
def world(db) -> World:
    admin = f.make_admin()
    syndicat = f.make_syndicat()
    prop = f.make_property(syndicat=syndicat)
    building = f.make_building(prop, name="Bloc A")
    other_building = f.make_building(prop, name="Bloc B")
    unit = f.make_unit(building, admin, number="A101")
    other_unit = f.make_unit(other_building, admin, number="B201")

    manager = f.make_user(email="manager@example.test")
    f.assign_role(manager, StructuralRole.MANAGER, prop)
    syndic = f.make_user(email="syndic@example.test")
    f.assign_role(syndic, StructuralRole.SYNDIC, syndicat)
    security = f.make_user(email="security@example.test")
    f.assign_role(security, StructuralRole.SECURITY, building)
    maintenance = f.make_user(email="maintenance@example.test")
    f.assign_role(maintenance, StructuralRole.MAINTENANCE, prop)

    owner = f.make_user(email="owner@example.test")
    f.make_owner(unit, owner, admin)
    tenant = f.make_user(email="tenant@example.test")
    co_tenant = f.make_user(email="cotenant@example.test")
    lease = f.make_lease(unit, [tenant, co_tenant], admin)
    outsider = f.make_user(email="outsider@example.test")
    return World(
        admin=admin,
        syndicat=syndicat,
        prop=prop,
        building=building,
        other_building=other_building,
        unit=unit,
        other_unit=other_unit,
        manager=manager,
        syndic=syndic,
        security=security,
        maintenance=maintenance,
        owner=owner,
        tenant=tenant,
        co_tenant=co_tenant,
        outsider=outsider,
        lease=lease,
    )


@pytest.fixture
def api():
    """API client carrying the selection headers.

    `syndicat` and `prop` are the pair selected while configuring the session
    (see `apps.common.views.BaseAPIView`, which requires both plus the
    `dashboard` step). When both are given and `step` is not, `step` defaults
    to `dashboard` — the ordinary case for every call once the session is
    configured. Pass `step="syndicat"` / `"property"` explicitly to exercise
    the UI configuration path itself.
    """

    def _client(user=None, syndicat=None, prop=None, step=None) -> APIClient:
        client = APIClient()
        if user is not None:
            client.force_authenticate(user)
        if syndicat is not None:
            client.defaults["HTTP_X_SYNDICAT_ID"] = str(getattr(syndicat, "pk", syndicat))
        if prop is not None:
            client.defaults["HTTP_X_PROPERTY_ID"] = str(getattr(prop, "pk", prop))
        if step is None and syndicat is not None and prop is not None:
            step = "dashboard"
        if step is not None:
            client.defaults["HTTP_X_UI_CONFIG_STEP"] = str(step)
        return client

    return _client
