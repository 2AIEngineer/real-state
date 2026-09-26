"""Inbox, preferences and push token endpoints."""

from drf_spectacular.utils import extend_schema
from rest_framework import status
from rest_framework.response import Response
from rest_framework.views import APIView

from apps.common.views import ApiMixin
from apps.notifications.serializers import (
    InboxNotificationSerializer,
    NotificationPreferenceSerializer,
    NotificationPreferenceUpdateSerializer,
    NotificationsMarkedReadSerializer,
    NotificationsQueryParamsSerializer,
    NotificationUnreadCountSerializer,
    PushTokenRegisterSerializer,
    PushTokenSerializer,
)
from apps.notifications.services import (
    InboxService,
    PreferenceService,
    PushTokenService,
)


@extend_schema(tags=["Notifications"])
class InboxView(ApiMixin, APIView):
    @extend_schema(
        parameters=[NotificationsQueryParamsSerializer],
        responses=InboxNotificationSerializer(many=True),
    )
    def get(self, request):
        query = self.parse_query_params(NotificationsQueryParamsSerializer)
        qs = InboxService.list_for(
            user=request.user,
            unread_only=query["unread"],
            category=query.get("category"),
        )
        return self.render_page(InboxNotificationSerializer, qs.select_related("content_type"))


@extend_schema(tags=["Notifications"])
class UnreadCountView(ApiMixin, APIView):
    @extend_schema(responses=NotificationUnreadCountSerializer)
    def get(self, request):
        return self.render(
            NotificationUnreadCountSerializer,
            {"unread": InboxService.unread_count(user=request.user)},
        )


@extend_schema(tags=["Notifications"])
class MarkReadView(ApiMixin, APIView):
    @extend_schema(request=None, responses=InboxNotificationSerializer)
    def post(self, request, notification_id: int):
        return self.render(
            InboxNotificationSerializer,
            InboxService.mark_read(user=request.user, notification_id=notification_id),
        )


@extend_schema(tags=["Notifications"])
class MarkAllReadView(ApiMixin, APIView):
    @extend_schema(request=None, responses=NotificationsMarkedReadSerializer)
    def post(self, request):
        return self.render(
            NotificationsMarkedReadSerializer,
            {"updated": InboxService.mark_all_read(user=request.user)},
        )


@extend_schema(tags=["Notifications"])
class PreferenceView(ApiMixin, APIView):
    @extend_schema(responses=NotificationPreferenceSerializer)
    def get(self, request):
        return self.render(
            NotificationPreferenceSerializer, PreferenceService.get(user=request.user)
        )

    @extend_schema(
        request=NotificationPreferenceUpdateSerializer,
        responses=NotificationPreferenceSerializer,
    )
    def patch(self, request):
        data = self.parse(NotificationPreferenceUpdateSerializer)
        return self.render(
            NotificationPreferenceSerializer,
            PreferenceService.update(user=request.user, changes=data),
        )


@extend_schema(tags=["Notifications"])
class PushTokenView(ApiMixin, APIView):
    @extend_schema(request=PushTokenRegisterSerializer, responses=PushTokenSerializer)
    def post(self, request):
        data = self.parse(PushTokenRegisterSerializer)
        return self.render(
            PushTokenSerializer, PushTokenService.register(user=request.user, **data)
        )


@extend_schema(tags=["Notifications"])
class PushTokenDetailView(ApiMixin, APIView):
    @extend_schema(responses={204: None})
    def delete(self, request, device_id: str):
        PushTokenService.unregister(user=request.user, device_id=device_id)
        return Response(status=status.HTTP_204_NO_CONTENT)
