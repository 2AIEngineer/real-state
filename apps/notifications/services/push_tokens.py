from __future__ import annotations

from django.db import transaction
from django.utils import timezone

from apps.common.exceptions import InvalidInput, NotFound
from apps.notifications.models import ExpoPushToken


class PushTokenService:
    @staticmethod
    @transaction.atomic
    def register(
        *, user, device_id: str, expo_push_token: str, platform: str = ""
    ) -> ExpoPushToken:
        """Idempotent upsert of the token of one of the user's devices.

        A physical token moves with the device: if another account was last
        signed in on it, that registration is deactivated so the previous user
        stops receiving pushes on a device they no longer use.
        """
        if not expo_push_token.startswith(("ExponentPushToken[", "ExpoPushToken[")):
            raise InvalidInput("This is not a valid Expo push token.", field="expo_push_token")
        now = timezone.now()
        ExpoPushToken.objects.filter(expo_push_token=expo_push_token, is_active=True).exclude(
            user=user, device_id=device_id
        ).update(is_active=False, deactivated_reason="token_reassigned")
        token, _ = ExpoPushToken.objects.update_or_create(
            user=user,
            device_id=device_id,
            defaults={
                "expo_push_token": expo_push_token,
                "platform": platform,
                "is_active": True,
                "deactivated_reason": "",
                "last_seen_at": now,
            },
        )
        return token

    @staticmethod
    @transaction.atomic
    def unregister(*, user, device_id: str) -> None:
        deleted, _ = ExpoPushToken.objects.filter(user=user, device_id=device_id).delete()
        if not deleted:
            raise NotFound("No push token registered for this device.")

    @staticmethod
    def deactivate_all(*, user, reason: str) -> None:
        ExpoPushToken.objects.filter(user=user, is_active=True).update(
            is_active=False, deactivated_reason=reason
        )
