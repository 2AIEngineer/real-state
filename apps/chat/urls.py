from django.urls import path

from apps.chat import views

urlpatterns = [
    path("chat/rooms/", views.RoomListView.as_view(), name="chat-room-list"),
    path(
        "chat/rooms/<int:room_id>/",
        views.RoomDetailView.as_view(),
        name="chat-room-detail",
    ),
    path(
        "chat/rooms/<int:room_id>/messages/",
        views.MessageListView.as_view(),
        name="chat-messages",
    ),
    path(
        "chat/rooms/<int:room_id>/messages/<int:message_id>/",
        views.MessageDetailView.as_view(),
        name="chat-message-detail",
    ),
    path(
        "chat/rooms/<int:room_id>/read/",
        views.RoomReadView.as_view(),
        name="chat-room-read",
    ),
]
