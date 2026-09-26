"""Outbox relay: delivers queued messages with retries and back-off."""

from __future__ import annotations

import logging
from datetime import timedelta

import requests
from django.conf import settings
from django.core.mail import EmailMultiAlternatives
from django.db import transaction
from django.utils import timezone

from apps.notifications.models import (
    ExpoPushToken,
    OutboxChannel,
    OutboxMessage,
    OutboxStatus,
)

logger = logging.getLogger(__name__)

EXPO_CHUNK_SIZE = 100
MAX_BACKOFF = timedelta(hours=1)


class DeliveryError(Exception):
    """Transient failure: the message will be retried."""


class EmailTransport:
    @staticmethod
    def send(payload: dict) -> None:
        to, bcc = payload.get("to") or [], payload.get("bcc") or []
        if not to and not bcc:
            return
        message = EmailMultiAlternatives(
            subject=payload["subject"],
            body=payload["text"],
            from_email=settings.DEFAULT_FROM_EMAIL,
            to=to,
            bcc=bcc,
        )
        message.attach_alternative(payload["html"], "text/html")
        try:
            message.send(fail_silently=False)
        except Exception as exc:
            raise DeliveryError(f"SMTP error: {exc}") from exc


class ExpoPushTransport:
    @staticmethod
    def send(payload: dict) -> None:
        tokens = list(
            ExpoPushToken.objects.filter(
                user_id__in=payload["user_ids"], is_active=True
            ).values_list("user_id", "expo_push_token")
        )
        if not tokens:
            return
        inbox_ids = payload.get("inbox_ids") or {}
        messages = [
            {
                "to": token,
                "title": payload["title"],
                "body": payload["body"],
                "sound": "default",
                "priority": "high",
                "channelId": "default",
                "data": {
                    **payload.get("data", {}),
                    "inbox_id": inbox_ids.get(str(user_id)),
                },
            }
            for user_id, token in tokens
        ]
        conf = settings.NOTIFICATIONS
        headers = {"Content-Type": "application/json", "Accept": "application/json"}
        for start in range(0, len(messages), EXPO_CHUNK_SIZE):
            chunk = messages[start : start + EXPO_CHUNK_SIZE]
            try:
                response = requests.post(
                    conf["EXPO_PUSH_URL"], json=chunk, headers=headers, timeout=15
                )
            except requests.RequestException as exc:
                raise DeliveryError(f"Expo unreachable: {exc}") from exc
            if response.status_code >= 500 or response.status_code == 429:
                raise DeliveryError(f"Expo HTTP {response.status_code}")
            if response.status_code >= 400:
                logger.error(
                    "Expo rejected push batch: %s %s",
                    response.status_code,
                    response.text[:500],
                )
                return
            ExpoPushTransport._handle_tickets(chunk, response.json().get("data", []))

    @staticmethod
    def _handle_tickets(chunk: list[dict], tickets: list[dict]) -> None:
        dead_tokens = [
            message["to"]
            for message, ticket in zip(chunk, tickets, strict=False)
            if ticket.get("status") == "error"
            and (ticket.get("details") or {}).get("error") == "DeviceNotRegistered"
        ]
        if dead_tokens:
            ExpoPushToken.objects.filter(expo_push_token__in=dead_tokens, is_active=True).update(
                is_active=False, deactivated_reason="DeviceNotRegistered"
            )


TRANSPORTS = {
    OutboxChannel.EMAIL: EmailTransport,
    OutboxChannel.PUSH: ExpoPushTransport,
}


def redacted(payload: dict) -> dict:
    """What is kept of a message once it will never be sent again.

    The body can hold a secret (a password link) and the recipients are
    personal data: only the subject and the number of recipients remain.
    """
    recipients = len(payload.get("to") or []) + len(payload.get("bcc") or [])
    recipients += len(payload.get("user_ids") or [])
    return {
        "subject": payload.get("subject") or payload.get("title", ""),
        "recipients": recipients,
        "redacted": True,
    }


def _backoff(attempts: int) -> timedelta:
    return min(timedelta(minutes=2**attempts), MAX_BACKOFF)


class OutboxRelay:
    @staticmethod
    def _deliver_one(message_id: int) -> bool:
        """Deliver one message under a row lock. Returns True if it was handled."""
        with transaction.atomic():
            message = (
                OutboxMessage.objects.select_for_update(skip_locked=True)
                .filter(pk=message_id, status=OutboxStatus.PENDING)
                .first()
            )
            if message is None:
                return False
            message.attempts += 1
            try:
                TRANSPORTS[message.channel].send(message.payload)
            except Exception as exc:
                message.last_error = str(exc)[:2000]
                if message.attempts >= settings.NOTIFICATIONS["OUTBOX_MAX_ATTEMPTS"]:
                    message.status = OutboxStatus.FAILED
                    logger.error(
                        "Outbox message %s abandoned after %s attempts: %s",
                        message.pk,
                        message.attempts,
                        exc,
                    )
                else:
                    message.next_attempt_at = timezone.now() + _backoff(message.attempts)
                    logger.warning(
                        "Outbox message %s failed (attempt %s): %s",
                        message.pk,
                        message.attempts,
                        exc,
                    )
            else:
                message.status = OutboxStatus.SENT
                message.sent_at = timezone.now()
                message.last_error = ""
            if message.status != OutboxStatus.PENDING:
                message.payload = redacted(message.payload)
            message.save(
                update_fields=[
                    "status",
                    "attempts",
                    "next_attempt_at",
                    "last_error",
                    "sent_at",
                    "payload",
                ]
            )
            return True

    @staticmethod
    def deliver_ids(message_ids) -> int:
        return sum(1 for message_id in message_ids if OutboxRelay._deliver_one(message_id))

    @staticmethod
    def run_once(batch_size: int | None = None) -> int:
        batch_size = batch_size or settings.NOTIFICATIONS["OUTBOX_BATCH_SIZE"]
        due = list(
            OutboxMessage.objects.filter(
                status=OutboxStatus.PENDING, next_attempt_at__lte=timezone.now()
            )
            .order_by("next_attempt_at", "id")
            .values_list("id", flat=True)[:batch_size]
        )
        return OutboxRelay.deliver_ids(due)
