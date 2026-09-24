"""Idempotent POST requests: a retry never creates a second record.

A client that may resend a POST (a mobile app losing its connection before
the answer arrives, a double tap) sends an `Idempotency-Key` header, a value it
generates once per intended action (a UUID) and reuses on every retry:

- first request: processed normally; a successful answer is remembered;
- retry with the same key and the same request: the remembered answer is
  returned (header `Idempotent-Replayed: true`), nothing is done again;
- same key while the first request is still running: 409 `request_in_progress`;
- same key with a different request: 409 `idempotency_key_reused`.

A failed request (4xx, 5xx) is not remembered: the client can fix it and retry
with the same key. Keys are per account and forgotten after a day
(`purge_expired`, run by `run_scheduled_jobs`). Without the header nothing
changes. `ApiMixin` applies it to every authenticated POST.
"""

from __future__ import annotations

import hashlib
import json
from datetime import timedelta

from django.db import IntegrityError, transaction
from django.utils import timezone
from rest_framework.renderers import JSONRenderer
from rest_framework.response import Response

from apps.common.exceptions import BusinessRuleViolation, InvalidInput
from apps.common.models import IdempotencyKey

HEADER = "Idempotency-Key"
RETENTION = timedelta(hours=24)
# A first request still unanswered after this long has died: its key is free again.
ABANDONED_AFTER = timedelta(minutes=5)


class Replay(Exception):
    """Raised to answer a retry with the remembered response."""

    def __init__(self, response: Response):
        self.response = response
        super().__init__("idempotent replay")


def _fingerprint(request) -> str:
    django_request = request._request
    content_type = django_request.content_type or ""
    # JSON bodies are small and hashed; uploads are identified by their size
    # (reading them here would load every file in memory).
    body = (
        django_request.body
        if content_type == "application/json"
        else django_request.META.get("CONTENT_LENGTH", "").encode()
    )
    digest = hashlib.sha256()
    for part in (
        django_request.method,
        django_request.get_full_path(),
        django_request.headers.get("X-Syndicat-Id", ""),
        django_request.headers.get("X-Property-Id", ""),
        content_type,
    ):
        digest.update(part.encode() + b"\0")
    digest.update(body)
    return digest.hexdigest()


def claim(request) -> IdempotencyKey | None:
    """Reserve the key of this request, or raise `Replay` / a domain error.

    Returns None when the request carries no key (nothing to do).
    """
    key = request.headers.get(HEADER)
    if not key or request.method != "POST" or not request.user.is_authenticated:
        return None
    if len(key) > 255:
        raise InvalidInput(f"{HEADER} is too long (255 characters at most).", field=HEADER)
    fingerprint = _fingerprint(request)
    try:
        with transaction.atomic():
            return IdempotencyKey.objects.create(
                user=request.user, key=key, fingerprint=fingerprint
            )
    except IntegrityError:
        pass
    previous = IdempotencyKey.objects.get(user=request.user, key=key)
    if previous.fingerprint != fingerprint:
        raise BusinessRuleViolation(
            f"This {HEADER} was already used for another request.", code="idempotency_key_reused"
        )
    if previous.status_code is not None:
        replay = Response(previous.response, status=previous.status_code)
        replay["Idempotent-Replayed"] = "true"
        raise Replay(replay)
    if previous.created_at > timezone.now() - ABANDONED_AFTER:
        raise BusinessRuleViolation(
            "The first request with this key is still being processed.",
            code="request_in_progress",
        )
    previous.created_at = timezone.now()
    previous.save(update_fields=["created_at"])
    return previous


def settle(claimed: IdempotencyKey, response: Response) -> None:
    """Remember a successful answer; release the key of a failed one."""
    if 200 <= response.status_code < 300:
        data = response.data
        claimed.status_code = response.status_code
        claimed.response = None if data is None else json.loads(JSONRenderer().render(data))
        claimed.save(update_fields=["status_code", "response"])
    else:
        claimed.delete()


def purge_expired(*, now=None) -> int:
    deleted, _ = IdempotencyKey.objects.filter(
        created_at__lt=(now or timezone.now()) - RETENTION
    ).delete()
    return deleted
