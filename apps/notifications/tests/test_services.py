import datetime as dt
from unittest import mock

import pytest
from django.core import mail
from django.utils import timezone

from apps.accounts.enums import StructuralRole
from apps.common.exceptions import InvalidInput
from apps.notifications.models import (
    ExpoPushToken,
    InboxNotification,
    NotificationCategory,
    OutboxChannel,
    OutboxMessage,
    OutboxStatus,
)
from apps.notifications.services import (
    InboxService,
    NotificationIntent,
    NotificationService,
    OutboxRelay,
    PreferenceService,
    PushTokenService,
)
from tests import factories as f

pytestmark = pytest.mark.django_db


@pytest.fixture(autouse=True)
def clean_slate(world):
    """The world fixture itself notifies (lease, ownership): start from zero."""
    OutboxMessage.objects.all().delete()
    InboxNotification.objects.all().delete()


def intent(**kwargs):
    defaults = dict(
        event_type="test.event", category=NotificationCategory.ANNOUNCEMENT, title="T", body="B"
    )
    return NotificationIntent(**{**defaults, **kwargs})


def token(user, device="d1", value=None):
    return PushTokenService.register(
        user=user,
        device_id=device,
        expo_push_token=value or f"ExponentPushToken[{user.pk}-{device}]",
    )


class TestDispatch:
    def test_inbox_and_outbox_are_written(self, world):
        result = NotificationService.notify(
            intent(to=[world.tenant], include_platform_admins=False)
        )
        assert result.inbox_count == 1
        channels = sorted(
            OutboxMessage.objects.filter(pk__in=result.outbox_ids).values_list("channel", flat=True)
        )
        assert channels == [OutboxChannel.EMAIL, OutboxChannel.PUSH]

    def test_platform_admins_are_added_in_bcc(self, world):
        NotificationService.notify(intent(to=[world.tenant]))
        emails = [m.payload for m in OutboxMessage.objects.filter(channel=OutboxChannel.EMAIL)]
        assert {"to": [world.tenant.email]}.items() <= emails[0].items() or any(
            world.tenant.email in e["to"] for e in emails
        )
        assert any(world.admin.email in e["bcc"] for e in emails)

    def test_bcc_recipients_share_one_email_without_exposed_addresses(self, world):
        NotificationService.notify(
            intent(bcc=[world.tenant, world.co_tenant, world.owner], include_platform_admins=False)
        )
        (email,) = OutboxMessage.objects.filter(channel=OutboxChannel.EMAIL)
        assert email.payload["to"] == [] and len(email.payload["bcc"]) == 3

    def test_emails_carry_the_brand(self, world):
        NotificationService.notify(intent(to=[world.tenant], include_platform_admins=False))
        (email,) = OutboxMessage.objects.filter(channel=OutboxChannel.EMAIL)
        html, text = email.payload["html"], email.payload["text"]
        assert 'src="https://urbisapp.com/logo.png"' in html
        for link in ("https://app-urbis.com/account/login", "https://urbisapp.com/fr"):
            assert link in html and link in text
        assert "Tous droits réservés" in html and "Tous droits réservés" in text

    def test_feature_preference_disables_every_channel(self, world):
        PreferenceService.update(user=world.tenant, changes={"announcements_enabled": False})
        result = NotificationService.notify(
            intent(to=[world.tenant], include_platform_admins=False)
        )
        assert result.inbox_count == 0 and result.outbox_ids == ()

    def test_channel_preference_only_disables_that_channel(self, world):
        PreferenceService.update(user=world.tenant, changes={"enabled_email": False})
        NotificationService.notify(intent(to=[world.tenant], include_platform_admins=False))
        assert not OutboxMessage.objects.filter(channel=OutboxChannel.EMAIL).exists()
        assert InboxNotification.objects.filter(user=world.tenant).exists()

    def test_field_roles_start_opted_out_of_feature_broadcasts(self, world):
        prefs = PreferenceService.get(user=world.security)
        assert prefs.announcements_enabled is False and prefs.enabled_push is True
        assert PreferenceService.get(user=world.tenant).announcements_enabled is True

    def test_transactional_bypasses_preferences(self, world):
        PreferenceService.update(user=world.tenant, changes={"enabled_email": False})
        NotificationService.notify(
            intent(
                category=NotificationCategory.ACCOUNT,
                to=[world.tenant],
                transactional=True,
                include_platform_admins=False,
            )
        )
        assert OutboxMessage.objects.filter(channel=OutboxChannel.EMAIL).exists()

    def test_excluded_actor_and_inactive_users_receive_nothing(self, world):
        world.co_tenant.is_active = False
        NotificationService.notify(
            intent(
                to=[world.tenant, world.co_tenant],
                exclude=[world.tenant],
                include_platform_admins=False,
            )
        )
        assert not InboxNotification.objects.exists()

    def test_rolled_back_business_change_notifies_nobody(self, world):
        from django.db import transaction

        with pytest.raises(RuntimeError), transaction.atomic():
            NotificationService.notify(intent(to=[world.tenant]))
            raise RuntimeError("business failure")
        assert not OutboxMessage.objects.exists() and not InboxNotification.objects.exists()


class TestRelay:
    def test_email_delivery(self, world):
        NotificationService.notify(
            intent(to=[world.tenant], include_platform_admins=False, channels=frozenset({"email"}))
        )
        assert OutboxRelay.run_once() == 1
        assert len(mail.outbox) == 1 and mail.outbox[0].to == [world.tenant.email]
        assert OutboxMessage.objects.get().status == OutboxStatus.SENT

    def test_transient_failure_is_retried_with_backoff_then_abandoned(self, world, settings):
        settings.NOTIFICATIONS = {**settings.NOTIFICATIONS, "OUTBOX_MAX_ATTEMPTS": 2}
        NotificationService.notify(
            intent(to=[world.tenant], include_platform_admins=False, channels=frozenset({"email"}))
        )
        with mock.patch(
            "django.core.mail.EmailMultiAlternatives.send", side_effect=OSError("smtp down")
        ):
            OutboxRelay.run_once()
            message = OutboxMessage.objects.get()
            assert (
                message.status == OutboxStatus.PENDING and message.next_attempt_at > timezone.now()
            )
            OutboxMessage.objects.update(next_attempt_at=timezone.now() - dt.timedelta(seconds=1))
            OutboxRelay.run_once()
        message.refresh_from_db()
        assert (
            message.status == OutboxStatus.FAILED
            and message.attempts == 2
            and "smtp down" in message.last_error
        )

    def test_push_marks_unregistered_devices_inactive(self, world):
        token(world.tenant)
        NotificationService.notify(
            intent(
                to=[world.tenant],
                include_platform_admins=False,
                channels=frozenset({"push", "inbox"}),
            )
        )
        response = mock.Mock(status_code=200)
        response.json.return_value = {
            "data": [{"status": "error", "details": {"error": "DeviceNotRegistered"}}]
        }
        with mock.patch(
            "apps.notifications.services.delivery.requests.post", return_value=response
        ) as post:
            OutboxRelay.run_once()
        sent = post.call_args.kwargs["json"][0]
        assert sent["data"]["inbox_id"] == InboxNotification.objects.get(user=world.tenant).pk
        assert not ExpoPushToken.objects.get(user=world.tenant).is_active


class TestPushTokens:
    def test_register_is_idempotent_per_device(self, world):
        token(world.tenant, value="ExponentPushToken[a]")
        token(world.tenant, value="ExponentPushToken[b]")
        assert ExpoPushToken.objects.filter(user=world.tenant).count() == 1

    def test_device_hand_over_deactivates_previous_account(self, world):
        token(world.tenant, device="phone", value="ExponentPushToken[shared]")
        token(world.owner, device="phone", value="ExponentPushToken[shared]")
        assert not ExpoPushToken.objects.get(user=world.tenant).is_active
        assert ExpoPushToken.objects.get(user=world.owner).is_active

    def test_invalid_token_format(self, world):
        with pytest.raises(InvalidInput):
            PushTokenService.register(
                user=world.tenant, device_id="x", expo_push_token="not-a-token"
            )


class TestInbox:
    def test_read_flow(self, world):
        NotificationService.notify(intent(to=[world.tenant], include_platform_admins=False))
        notification = InboxNotification.objects.get(user=world.tenant)
        assert InboxService.unread_count(user=world.tenant) == 1
        InboxService.mark_read(user=world.tenant, notification_id=notification.pk)
        assert InboxService.unread_count(user=world.tenant) == 0

    def test_cannot_read_someone_elses_notification(self, world):
        from apps.common.exceptions import NotFound

        NotificationService.notify(intent(to=[world.tenant], include_platform_admins=False))
        with pytest.raises(NotFound):
            InboxService.mark_read(
                user=world.owner, notification_id=InboxNotification.objects.get().pk
            )


def test_admin_opt_out_is_respected(world):
    PreferenceService.update(user=world.admin, changes={"announcements_enabled": False})
    f.assign_role(f.make_user(), StructuralRole.ADMIN)
    NotificationService.notify(intent(to=[world.tenant]))
    assert not InboxNotification.objects.filter(user=world.admin).exists()
