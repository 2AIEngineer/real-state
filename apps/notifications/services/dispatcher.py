"""Unified notification entry point.

Business services describe *what happened and to whom* with a
`NotificationIntent`; this module applies preferences, writes the in-app
inbox and enqueues e-mail/push messages in the transactional outbox. Nothing
is sent over the network here: delivery is the relay's job, after commit, so
a notification failure can never undo a business change and a rolled-back
change never notifies anyone.
"""

from __future__ import annotations

import logging
from collections.abc import Iterable
from dataclasses import dataclass, field
from typing import Any

from django.conf import settings
from django.contrib.contenttypes.models import ContentType
from django.db import models, transaction
from django.template.loader import render_to_string
from django.utils import timezone

from apps.accounts.services.directory import UserDirectory
from apps.notifications.models import (
    CATEGORY_PREFERENCE_FIELD,
    InboxNotification,
    NotificationPreference,
    OutboxChannel,
    OutboxMessage,
    Severity,
)
from apps.notifications.services.delivery import OutboxRelay
from apps.notifications.services.preferences import PreferenceService

logger = logging.getLogger(__name__)

BCC_CHUNK_SIZE = 50
PUSH_BATCH_SIZE = 100  # one Expo request per message


@dataclass
class NotificationIntent:
    event_type: str
    category: str
    title: str
    body: str
    # Nominative recipients: one personal e-mail each.
    to: Iterable = ()
    # Grouped recipients: one e-mail with every address in BCC (addresses never exposed).
    bcc: Iterable = ()
    # Raw addresses not bound to an account (e.g. the previous address after an
    # e-mail change). Only allowed for transactional e-mails.
    to_addresses: Iterable[str] = ()
    target: models.Model | None = None
    severity: str = Severity.INFO
    data: dict[str, Any] = field(default_factory=dict)
    action_path: str | None = None
    exclude: Iterable = ()
    # Platform admins receive every notification in BCC unless they opted out.
    include_platform_admins: bool = True
    # Security/account e-mails (password setup) bypass preferences.
    transactional: bool = False
    email_lines: list[str] = field(default_factory=list)
    channels: frozenset[str] = frozenset({"inbox", "email", "push"})


@dataclass(frozen=True)
class DispatchResult:
    inbox_count: int
    outbox_ids: tuple[int, ...]


def _feature_allowed(pref: NotificationPreference, category: str) -> bool:
    flag = CATEGORY_PREFERENCE_FIELD.get(category)
    return True if flag is None else bool(getattr(pref, flag))


def _render_email(intent: NotificationIntent, greeting_name: str | None) -> dict[str, str]:
    action_url = f"{settings.SITE_URL}{intent.action_path}" if intent.action_path else None
    context = {
        "title": intent.title,
        "body": intent.body,
        "lines": intent.email_lines,
        "action_url": action_url,
        "greeting_name": greeting_name,
        "brand": settings.BRAND,
        "year": timezone.localdate().year,
    }
    return {
        "subject": intent.title,
        "text": render_to_string("notifications/email.txt", context),
        "html": render_to_string("notifications/email.html", context),
    }


def _schedule_relay(outbox_ids: list[int]) -> None:
    if not outbox_ids or not settings.NOTIFICATIONS["DELIVER_ON_COMMIT"]:
        return

    def _relay() -> None:
        try:
            OutboxRelay.deliver_ids(outbox_ids)
        except Exception:  # the worker will retry; never surface to the caller
            logger.exception("Immediate outbox relay failed; the worker will retry.")

    transaction.on_commit(_relay)


@dataclass
class _Audience:
    """Who receives a notification, once exclusions and preferences are applied."""

    to: dict[int, Any]  # nominative: one personal e-mail each
    bcc: dict[int, Any]  # grouped: e-mails in BCC
    prefs: dict[int, NotificationPreference]

    @property
    def everyone(self) -> dict[int, Any]:
        return {**self.bcc, **self.to}


def _audience(intent: NotificationIntent) -> _Audience:
    excluded = {getattr(u, "pk", u) for u in intent.exclude}
    to = {u.pk: u for u in intent.to if u.pk not in excluded and u.is_active}
    bcc = {u.pk: u for u in intent.bcc if u.pk not in excluded and u.is_active and u.pk not in to}
    if intent.include_platform_admins:
        for admin in UserDirectory.platform_admins():
            if admin.pk not in excluded and admin.pk not in to:
                bcc.setdefault(admin.pk, admin)
    everyone = {**bcc, **to}
    prefs = PreferenceService.resolve_many(everyone.keys()) if everyone else {}

    def allowed(uid: int) -> bool:
        return intent.transactional or _feature_allowed(prefs[uid], intent.category)

    return _Audience(
        to={uid: u for uid, u in to.items() if allowed(uid)},
        bcc={uid: u for uid, u in bcc.items() if allowed(uid)},
        prefs=prefs,
    )


def _outbox_message(intent: NotificationIntent, channel: str, payload: dict) -> OutboxMessage:
    return OutboxMessage(
        channel=channel,
        notification_type=intent.event_type,
        next_attempt_at=timezone.now(),
        payload=payload,
    )


def _raw_address_emails(intent: NotificationIntent) -> list[OutboxMessage]:
    """E-mails to addresses bound to no account (transactional only)."""
    addresses = sorted(set(intent.to_addresses))
    if addresses and not intent.transactional:
        raise ValueError("Raw e-mail addresses are reserved for transactional notifications.")
    if not addresses or "email" not in intent.channels:
        return []
    if not settings.NOTIFICATIONS["EMAIL_ENABLED"]:
        return []
    return [
        _outbox_message(
            intent,
            OutboxChannel.EMAIL,
            {"to": [address], "bcc": [], **_render_email(intent, None)},
        )
        for address in addresses
    ]


def _inbox_rows(intent: NotificationIntent, audience: _Audience) -> dict[int, int]:
    """Writes the in-app notifications; returns {user id: inbox id}."""
    if "inbox" not in intent.channels:
        return {}
    target = intent.target
    content_type = ContentType.objects.get_for_model(target) if target is not None else None
    rows = InboxNotification.objects.bulk_create(
        [
            InboxNotification(
                user_id=uid,
                category=intent.category,
                notification_type=intent.event_type,
                severity=intent.severity,
                title=intent.title[:200],
                body=intent.body,
                data=intent.data,
                content_type=content_type,
                object_id=target.pk if target is not None else None,
            )
            for uid in audience.everyone
        ]
    )
    return {row.user_id: row.pk for row in rows}


def _push_messages(
    intent: NotificationIntent, audience: _Audience, inbox_ids: dict[int, int]
) -> list[OutboxMessage]:
    """One message per batch of recipients: a failed batch is retried alone,
    and the batches already delivered are not sent twice."""
    if "push" not in intent.channels or not settings.NOTIFICATIONS["PUSH_ENABLED"]:
        return []
    user_ids = [
        uid for uid in audience.everyone if intent.transactional or audience.prefs[uid].enabled_push
    ]
    data = {**intent.data, "type": intent.event_type, "category": intent.category}
    return [
        _outbox_message(
            intent,
            OutboxChannel.PUSH,
            {
                "user_ids": batch,
                "title": intent.title,
                "body": intent.body,
                "data": data,
                "inbox_ids": {str(uid): inbox_ids.get(uid) for uid in batch},
            },
        )
        for batch in _batches(user_ids, PUSH_BATCH_SIZE)
    ]


def _email_messages(intent: NotificationIntent, audience: _Audience) -> list[OutboxMessage]:
    """A personal e-mail per nominative recipient, and BCC batches for the others."""
    if "email" not in intent.channels or not settings.NOTIFICATIONS["EMAIL_ENABLED"]:
        return []

    def wants_email(uid: int) -> bool:
        return intent.transactional or audience.prefs[uid].enabled_email

    messages = [
        _outbox_message(
            intent,
            OutboxChannel.EMAIL,
            {"to": [user.email], "bcc": [], **_render_email(intent, user.first_name)},
        )
        for uid, user in audience.to.items()
        if wants_email(uid)
    ]
    bcc_emails = sorted(user.email for uid, user in audience.bcc.items() if wants_email(uid))
    if bcc_emails:
        rendered = _render_email(intent, None)
        messages += [
            _outbox_message(intent, OutboxChannel.EMAIL, {"to": [], "bcc": batch, **rendered})
            for batch in _batches(bcc_emails, BCC_CHUNK_SIZE)
        ]
    return messages


def _batches(items: list, size: int) -> list[list]:
    return [items[start : start + size] for start in range(0, len(items), size)]


def _enqueue(messages: list[OutboxMessage]) -> list[int]:
    ids = [m.pk for m in OutboxMessage.objects.bulk_create(messages)] if messages else []
    _schedule_relay(ids)
    return ids


class NotificationService:
    @staticmethod
    def notify(intent: NotificationIntent) -> DispatchResult:
        """Writes the inbox and queues the e-mails and pushes of one event.

        Runs inside the caller's transaction: nothing leaves before it commits.
        """
        _enqueue(_raw_address_emails(intent))
        audience = _audience(intent)
        if not audience.everyone:
            return DispatchResult(0, ())
        with transaction.atomic():
            inbox_ids = _inbox_rows(intent, audience)
            outbox_ids = _enqueue(
                _push_messages(intent, audience, inbox_ids) + _email_messages(intent, audience)
            )
        return DispatchResult(len(inbox_ids), tuple(outbox_ids))
