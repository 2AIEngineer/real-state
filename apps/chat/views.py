from drf_spectacular.utils import extend_schema
from rest_framework import status
from rest_framework.response import Response

from apps.chat import serializers as s
from apps.chat.services import ChatService
from apps.common.views import BaseAPIView


@extend_schema(tags=["Chat"])
class RoomListView(BaseAPIView):
    @extend_schema(responses=s.ChatRoomSerializer(many=True))
    def get(self, request):
        return self.render_page(
            s.ChatRoomSerializer,
            ChatService.list_rooms(actor=request.user, property_id=self.selected_property_id),
        )

    @extend_schema(request=s.ChatRoomOpenSerializer, responses=s.ChatRoomSerializer)
    def post(self, request):
        data = self.parse(s.ChatRoomOpenSerializer)
        room = ChatService.open_room(
            actor=request.user, kind=data["context_type"], object_id=data["context_id"]
        )
        return self.render(s.ChatRoomSerializer, room)


@extend_schema(tags=["Chat"])
class RoomDetailView(BaseAPIView):
    @extend_schema(responses=s.ChatRoomSerializer)
    def get(self, request, room_id: int):
        return self.render(
            s.ChatRoomSerializer, ChatService.get_room(actor=request.user, room_id=room_id)
        )


@extend_schema(tags=["Chat"])
class MessageListView(BaseAPIView):
    @extend_schema(
        parameters=[s.ChatMessagesQueryParamsSerializer],
        responses=s.ChatMessageSerializer(many=True),
    )
    def get(self, request, room_id: int):
        room = ChatService.get_room(actor=request.user, room_id=room_id)
        query = self.parse_query_params(s.ChatMessagesQueryParamsSerializer)
        return self.render_page(
            s.ChatMessageSerializer, ChatService.messages(actor=request.user, room=room, **query)
        )

    @extend_schema(request=s.ChatMessageCreateSerializer, responses={201: s.ChatMessageSerializer})
    def post(self, request, room_id: int):
        room = ChatService.get_room(actor=request.user, room_id=room_id)
        data = self.parse(s.ChatMessageCreateSerializer)
        message = ChatService.post(
            actor=request.user, room=room, body=data["body"], media=data["media"]
        )
        return self.render(s.ChatMessageSerializer, message, status=status.HTTP_201_CREATED)


@extend_schema(tags=["Chat"])
class MessageDetailView(BaseAPIView):
    """Edit or delete one message of the conversation."""

    @extend_schema(request=s.ChatMessageEditSerializer, responses=s.ChatMessageSerializer)
    def patch(self, request, room_id: int, message_id: int):
        room = ChatService.get_room(actor=request.user, room_id=room_id)
        message = ChatService.get_message(actor=request.user, room=room, message_id=message_id)
        data = self.parse(s.ChatMessageEditSerializer)
        return self.render(
            s.ChatMessageSerializer,
            ChatService.edit_message(actor=request.user, message=message, body=data["body"]),
        )

    @extend_schema(
        responses={204: None},
        description="Deletes the message and its media (author, or property management).",
    )
    def delete(self, request, room_id: int, message_id: int):
        room = ChatService.get_room(actor=request.user, room_id=room_id)
        message = ChatService.get_message(actor=request.user, room=room, message_id=message_id)
        ChatService.delete_message(actor=request.user, message=message)
        return Response(status=status.HTTP_204_NO_CONTENT)


@extend_schema(tags=["Chat"])
class RoomReadView(BaseAPIView):
    @extend_schema(request=None, responses={204: None})
    def post(self, request, room_id: int):
        room = ChatService.get_room(actor=request.user, room_id=room_id)
        ChatService.mark_read(actor=request.user, room=room)
        return Response(status=status.HTTP_204_NO_CONTENT)
