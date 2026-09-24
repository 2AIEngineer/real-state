from __future__ import annotations

from django.db import transaction
from django.db.models import QuerySet
from django.utils import timezone

from apps.common.exceptions import NotFound
from apps.notifications.models import InboxNotification


class InboxService:
    @staticmethod
    def list_for(
        *, user, unread_only: bool = False, category: str | None = None
    ) -> QuerySet[InboxNotification]:
        qs = InboxNotification.objects.filter(user=user)
        if unread_only:
            qs = qs.filter(is_read=False)
        if category:
            qs = qs.filter(category=category)
        return qs

    @staticmethod
    def unread_count(*, user) -> int:
        return InboxNotification.objects.filter(user=user, is_read=False).count()

    @staticmethod
    @transaction.atomic
    def mark_read(*, user, notification_id: int) -> InboxNotification:
        notification = (
            InboxNotification.objects.select_for_update(of=("self",))
            .filter(pk=notification_id, user=user)
            .first()
        )
        if notification is None:
            raise NotFound("Notification not found.")
        if not notification.is_read:
            notification.is_read = True
            notification.read_at = timezone.now()
            notification.save(update_fields=["is_read", "read_at"])
        return notification

    @staticmethod
    def mark_all_read(*, user) -> int:
        return InboxNotification.objects.filter(user=user, is_read=False).update(
            is_read=True, read_at=timezone.now()
        )
