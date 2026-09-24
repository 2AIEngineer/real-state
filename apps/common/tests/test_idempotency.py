"""A POST retried with the same Idempotency-Key is answered once, never repeated."""

import datetime as dt

import pytest
from django.utils import timezone

from apps.common import idempotency
from apps.common.models import IdempotencyKey
from apps.service_requests.models import ServiceRequest

pytestmark = pytest.mark.django_db

URL = "/api/v1/service-requests/"
BODY = {"title": "Leak", "description": "Sink"}


def post(client, body=BODY, key="key-1"):
    return client.post(URL, body, format="json", HTTP_IDEMPOTENCY_KEY=key)


def test_a_retry_returns_the_first_answer_without_creating_twice(api, world):
    client = api(world.tenant, world.syndicat, world.prop)

    first = post(client)
    retry = post(client)

    assert first.status_code == retry.status_code == 201
    assert retry.json() == first.json() and retry["Idempotent-Replayed"] == "true"
    assert ServiceRequest.objects.count() == 1


def test_without_the_header_nothing_changes(api, world):
    client = api(world.tenant, world.syndicat, world.prop)

    client.post(URL, BODY, format="json")
    client.post(URL, BODY, format="json")

    assert ServiceRequest.objects.count() == 2 and not IdempotencyKey.objects.exists()


def test_a_key_reused_for_another_request_is_refused(api, world):
    client = api(world.tenant, world.syndicat, world.prop)
    post(client)

    response = post(client, {"title": "Noise", "description": "Upstairs"})

    assert response.status_code == 409
    assert response.json()["error"]["code"] == "idempotency_key_reused"


def test_a_failed_request_can_be_retried_with_the_same_key(api, world):
    client = api(world.tenant, world.syndicat, world.prop)

    assert post(client, {"title": ""}).status_code == 400
    assert post(client).status_code == 201


def test_keys_belong_to_one_account(api, world):
    post(api(world.tenant, world.syndicat, world.prop))
    post(api(world.owner, world.syndicat, world.prop))

    assert ServiceRequest.objects.count() == 2


def test_a_key_still_in_progress_is_refused_then_freed_once_abandoned(api, world):
    client = api(world.tenant, world.syndicat, world.prop)
    post(client)
    IdempotencyKey.objects.update(status_code=None, response=None)  # as if still running

    assert post(client).json()["error"]["code"] == "request_in_progress"

    IdempotencyKey.objects.update(created_at=timezone.now() - dt.timedelta(minutes=10))
    assert post(client).status_code == 201


def test_keys_are_forgotten_after_a_day(api, world):
    post(api(world.tenant, world.syndicat, world.prop))

    assert idempotency.purge_expired() == 0
    assert idempotency.purge_expired(now=timezone.now() + dt.timedelta(days=2)) == 1
