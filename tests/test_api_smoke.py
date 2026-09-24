"""Cross-cutting HTTP guarantees, checked on every registered route."""

import pytest
from django.urls import URLPattern, URLResolver, get_resolver

pytestmark = pytest.mark.django_db

PUBLIC = {
    "auth-token",
    "auth-token-refresh",
    "auth-logout",
    "auth-password-reset",
    "auth-password-set",
    "schema",
    "docs",
    "healthz",
    "readyz",
    "file",  # signed links carry their own authorization
}


def _named_routes(resolver=None, prefix=""):
    resolver = resolver or get_resolver()
    for entry in resolver.url_patterns:
        if isinstance(entry, URLResolver):
            yield from _named_routes(entry, prefix + str(entry.pattern))
        elif isinstance(entry, URLPattern) and entry.name:
            yield entry.name, prefix + str(entry.pattern)


def _concrete(path: str) -> str:
    import re

    return "/" + re.sub(r"<(?:\w+:)?\w+>", "1", path)


def test_every_private_route_requires_authentication(api):
    client = api()
    checked = 0
    for name, path in _named_routes():
        if name in PUBLIC:
            continue
        response = client.get(_concrete(path))
        if response.status_code == 405:
            response = client.post(_concrete(path), {})
        assert response.status_code == 401, f"{name} ({path}) answered {response.status_code}"
        assert response.json()["error"]["code"] == "not_authenticated"
        checked += 1
    assert checked > 80


def test_validation_errors_use_the_uniform_envelope(api, world):
    response = api(world.admin).post("/api/v1/syndicats/", {}, format="json")
    assert response.status_code == 400
    body = response.json()["error"]
    assert body["code"] == "invalid" and "name" in body["details"]


def test_domain_errors_use_the_uniform_envelope(api, world):
    response = api(world.tenant).post("/api/v1/syndicats/", {"name": "X"}, format="json")
    assert response.status_code == 403
    assert response.json()["error"]["code"] == "permission_denied"


def test_lists_are_paginated(api, world):
    body = api(world.admin).get("/api/v1/properties/").json()
    assert set(body) == {"count", "next", "previous", "results"}
