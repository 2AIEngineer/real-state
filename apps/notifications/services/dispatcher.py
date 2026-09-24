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


class NotificationService:
    @staticmethod
    def notify(intent: NotificationIntent) -> DispatchResult:
        excluded = {getattr(u, "pk", u) for u in intent.exclude}
        to_users = {u.pk: u for u in intent.to if u.pk not in excluded and u.is_active}
        bcc_users = {
            u.pk: u
            for u in intent.bcc
            if u.pk not in excluded and u.is_active and u.pk not in to_users
        }
        if intent.include_platform_admins:
            for admin in UserDirectory.platform_admins():
                if admin.pk not in excluded and admin.pk not in to_users:
                    bcc_users.setdefault(admin.pk, admin)
        everyone = {**bcc_users, **to_users}
        raw_addresses = sorted(set(intent.to_addresses))
        if raw_addresses and not intent.transactional:
            raise ValueError("Raw e-mail addresses are reserved for transactional notifications.")
        if raw_addresses and "email" in intent.channels and settings.NOTIFICATIONS["EMAIL_ENABLED"]:
            now = timezone.now()
            created = OutboxMessage.objects.bulk_create(
                [
                    OutboxMessage(
                        channel=OutboxChannel.EMAIL,
                        notification_type=intent.event_type,
                        next_attempt_at=now,
                        payload={"to": [address], "bcc": [], **_render_email(intent, None)},
                    )
                    for address in raw_addresses
                ]
            )
            _schedule_relay([m.pk for m in created])
        if not everyone:
            return DispatchResult(0, ())

        prefs = PreferenceService.resolve_many(everyone.keys())

        def allowed(uid: int) -> bool:
            return intent.transactional or _feature_allowed(prefs[uid], intent.category)

        recipients = {uid: user for uid, user in everyone.items() if allowed(uid)}
        if not recipients:
            return DispatchResult(0, ())

        with transaction.atomic():
            content_type = (
                ContentType.objects.get_for_model(intent.target)
                if intent.target is not None
                else None
            )
            inbox_ids: dict[int, int] = {}
            if "inbox" in intent.channels:
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
                            object_id=intent.target.pk if intent.target is not None else None,
                        )
                        for uid in recipients
                    ]
                )
                inbox_ids = {row.user_id: row.pk for row in rows}

            outbox: list[OutboxMessage] = []
            now = timezone.now()
            conf = settings.NOTIFICATIONS

            if "push" in intent.channels and conf["PUSH_ENABLED"]:
                push_ids = [
                    uid for uid in recipients if intent.transactional or prefs[uid].enabled_push
                ]
                if push_ids:
                    outbox.append(
                        OutboxMessage(
                            channel=OutboxChannel.PUSH,
                            notification_type=intent.event_type,
                            next_attempt_at=now,
                            payload={
                                "user_ids": push_ids,
                                "title": intent.title,
                                "body": intent.body,
                                "data": {
                                    **intent.data,
                                    "type": intent.event_type,
                                    "category": intent.category,
                                },
                                "inbox_ids": {str(uid): inbox_ids.get(uid) for uid in push_ids},
                            },
                        )
                    )

            if "email" in intent.channels and conf["EMAIL_ENABLED"]:

                def wants_email(uid: int) -> bool:
                    return intent.transactional or prefs[uid].enabled_email

                for uid, user in to_users.items():
                    if uid in recipients and wants_email(uid):
                        outbox.append(
                            OutboxMessage(
                                channel=OutboxChannel.EMAIL,
                                notification_type=intent.event_type,
                                next_attempt_at=now,
                                payload={
                                    "to": [user.email],
                                    "bcc": [],
                                    **_render_email(intent, user.first_name),
                                },
                            )
                        )
                bcc_emails = sorted(
                    user.email
                    for uid, user in bcc_users.items()
                    if uid in recipients and wants_email(uid)
                )
                if bcc_emails:
                    rendered = _render_email(intent, None)
                    for start in range(0, len(bcc_emails), BCC_CHUNK_SIZE):
                        outbox.append(
                            OutboxMessage(
                                channel=OutboxChannel.EMAIL,
                                notification_type=intent.event_type,
                                next_attempt_at=now,
                                payload={
                                    "to": [],
                                    "bcc": bcc_emails[start : start + BCC_CHUNK_SIZE],
                                    **rendered,
                                },
                            )
                        )

            created = OutboxMessage.objects.bulk_create(outbox)
            outbox_ids = [m.pk for m in created]
            _schedule_relay(outbox_ids)
        return DispatchResult(len(inbox_ids), tuple(outbox_ids))
