from django.conf import settings
from django.contrib.contenttypes.fields import GenericForeignKey
from django.contrib.contenttypes.models import ContentType
from django.db import models
from django.db.models import Q

from apps.common.models import TimeStampedModel


class NotificationCategory(models.TextChoices):
    ACCOUNT = "account", "Account"
    PROPERTY = "property", "Property administration"
    LEASING = "leasing", "Leasing"
    SERVICE_REQUEST = "service_request", "Service requests"
    WORK_ORDER = "work_order", "Work orders"
    ANNOUNCEMENT = "announcement", "Announcements"
    EVENT = "event", "Events"
    BOOKING = "booking", "Amenity bookings"
    STORE = "store", "Store"
    LIBRARY = "library", "Library"
    SHORT_TERM_RENTAL = "short_term_rental", "Short-term rentals"
    SURVEY = "survey", "Surveys"
    MARKETPLACE = "marketplace", "Marketplace"
    VISITOR = "visitor", "Visitors"
    CHAT = "chat", "Chat"


# Category -> NotificationPreference feature flag. Categories absent from the
# map are operational (account, leasing, ...) and only obey global channels.
CATEGORY_PREFERENCE_FIELD: dict[str, str] = {
    NotificationCategory.SERVICE_REQUEST: "service_request_enabled",
    NotificationCategory.ANNOUNCEMENT: "announcements_enabled",
    NotificationCategory.EVENT: "events_enabled",
    NotificationCategory.BOOKING: "bookings_enabled",
    NotificationCategory.STORE: "store_enabled",
    NotificationCategory.LIBRARY: "library_enabled",
    NotificationCategory.SHORT_TERM_RENTAL: "short_term_rental_enabled",
    NotificationCategory.SURVEY: "surveys_enabled",
    NotificationCategory.MARKETPLACE: "marketplace_enabled",
    NotificationCategory.VISITOR: "visitors_enabled",
    NotificationCategory.CHAT: "chat_enabled",
}


class Severity(models.TextChoices):
    INFO = "INFO", "Information"
    SUCCESS = "SUCCESS", "Success"
    WARNING = "WARNING", "Warning"
    CRITICAL = "CRITICAL", "Critical"


class NotificationPreference(TimeStampedModel):
    user = models.OneToOneField(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="notification_preference",
    )
    enabled_push = models.BooleanField(default=True)
    enabled_email = models.BooleanField(default=True)

    service_request_enabled = models.BooleanField(default=True)
    announcements_enabled = models.BooleanField(default=True)
    events_enabled = models.BooleanField(default=True)
    bookings_enabled = models.BooleanField(default=True)
    store_enabled = models.BooleanField(default=True)
    library_enabled = models.BooleanField(default=True)
    short_term_rental_enabled = models.BooleanField(default=True)
    surveys_enabled = models.BooleanField(default=True)
    marketplace_enabled = models.BooleanField(default=True)
    visitors_enabled = models.BooleanField(default=True)
    chat_enabled = models.BooleanField(default=True)

    def __str__(self) -> str:
        return f"Preferences of user {self.user_id}"


class ExpoPushToken(models.Model):
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="push_tokens"
    )
    device_id = models.CharField(max_length=191)
    expo_push_token = models.CharField(max_length=255)
    platform = models.CharField(max_length=16, blank=True)
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)
    last_seen_at = models.DateTimeField()
    deactivated_reason = models.CharField(max_length=64, blank=True)

    class Meta:
        constraints = [
            models.UniqueConstraint(
                fields=["user", "device_id"], name="unique_push_token_per_user_device"
            ),
            # A physical token belongs to one account at a time (device hand-over).
            models.UniqueConstraint(
                fields=["expo_push_token"],
                condition=Q(is_active=True),
                name="unique_active_expo_token",
            ),
        ]
        indexes = [models.Index(fields=["user", "is_active"])]

    def __str__(self) -> str:
        return f"{self.user_id}:{self.device_id}"


class InboxNotification(models.Model):
    """In-app notification feed item with its read status (spec §4.4)."""

    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="inbox_notifications",
    )
    category = models.CharField(max_length=32, choices=NotificationCategory.choices)
    notification_type = models.CharField(
        max_length=80, help_text="e.g. service_request.created"
    )
    severity = models.CharField(
        max_length=10, choices=Severity.choices, default=Severity.INFO
    )
    title = models.CharField(max_length=200)
    body = models.TextField(blank=True)
    data = models.JSONField(default=dict, blank=True)
    content_type = models.ForeignKey(
        ContentType, null=True, blank=True, on_delete=models.SET_NULL, related_name="+"
    )
    object_id = models.PositiveBigIntegerField(null=True, blank=True)
    target = GenericForeignKey("content_type", "object_id")
    is_read = models.BooleanField(default=False)
    read_at = models.DateTimeField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True, db_index=True)

    class Meta:
        ordering = ["-created_at", "-id"]
        indexes = [
            models.Index(fields=["user", "is_read", "-created_at"]),
            models.Index(fields=["content_type", "object_id"]),
        ]
        constraints = [
            models.CheckConstraint(
                condition=Q(is_read=False, read_at__isnull=True)
                | Q(is_read=True, read_at__isnull=False),
                name="inbox_read_state_consistent",
            )
        ]

    def __str__(self) -> str:
        return f"{self.notification_type} -> {self.user_id}"


class RecipientSnapshot(models.Model):
    """Frozen list of the users a broadcast was addressed to when published."""

    content_type = models.ForeignKey(
        ContentType, on_delete=models.CASCADE, related_name="+"
    )
    object_id = models.PositiveBigIntegerField()
    target = GenericForeignKey("content_type", "object_id")
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="+"
    )
    matched_roles = models.JSONField(
        default=list,
        help_text="The target roles the user had when the snapshot was taken.",
    )
    snapshotted_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        constraints = [
            models.UniqueConstraint(
                fields=["content_type", "object_id", "user"],
                name="unique_snapshot_recipient",
            ),
        ]
        indexes = [models.Index(fields=["content_type", "object_id"])]


class OutboxChannel(models.TextChoices):
    EMAIL = "EMAIL", "E-mail"
    PUSH = "PUSH", "Push"


class OutboxStatus(models.TextChoices):
    PENDING = "PENDING", "Pending"
    PROCESSING = "PROCESSING", "Processing"
    SENT = "SENT", "Sent"
    FAILED = "FAILED", "Failed (gave up)"


class OutboxMessage(models.Model):
    """Transactional outbox: written in the business transaction, relayed later."""

    channel = models.CharField(max_length=8, choices=OutboxChannel.choices)
    notification_type = models.CharField(max_length=80)
    payload = models.JSONField()
    status = models.CharField(
        max_length=12, choices=OutboxStatus.choices, default=OutboxStatus.PENDING
    )
    attempts = models.PositiveSmallIntegerField(default=0)
    next_attempt_at = models.DateTimeField(db_index=True)
    last_error = models.TextField(blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    sent_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        ordering = ["id"]
        indexes = [models.Index(fields=["status", "next_attempt_at"])]

    def __str__(self) -> str:
        return f"Outbox #{self.pk} {self.channel} {self.status}"
