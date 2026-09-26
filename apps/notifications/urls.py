from django.urls import path

from apps.notifications.views import (
    InboxView,
    MarkAllReadView,
    MarkReadView,
    PreferenceView,
    PushTokenDetailView,
    PushTokenView,
    UnreadCountView,
)

urlpatterns = [
    path("notifications/", InboxView.as_view(), name="notification-list"),
    path(
        "notifications/unread-count/",
        UnreadCountView.as_view(),
        name="notification-unread-count",
    ),
    path(
        "notifications/read-all/",
        MarkAllReadView.as_view(),
        name="notification-read-all",
    ),
    path(
        "notifications/<int:notification_id>/read/",
        MarkReadView.as_view(),
        name="notification-read",
    ),
    path(
        "notifications/preferences/",
        PreferenceView.as_view(),
        name="notification-preferences",
    ),
    path(
        "notifications/push-tokens/",
        PushTokenView.as_view(),
        name="push-token-register",
    ),
    path(
        "notifications/push-tokens/<str:device_id>/",
        PushTokenDetailView.as_view(),
        name="push-token-detail",
    ),
]
