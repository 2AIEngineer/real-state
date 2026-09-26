from drf_spectacular.utils import extend_schema
from rest_framework import status
from rest_framework.response import Response

from apps.common.serializers import (
    ActionReasonSerializer,
    BulkActionResultSerializer,
    UploadFilesSerializer,
)
from apps.common.views import BaseAPIView
from apps.events import serializers as s
from apps.events.services import EventService
from apps.properties.services import BuildingService


@extend_schema(tags=["Events"])
class EventListView(BaseAPIView):
    @extend_schema(
        parameters=[s.EventsQueryParamsSerializer],
        responses=s.EventSerializer(many=True),
    )
    def get(self, request):
        query = dict(self.parse_query_params(s.EventsQueryParamsSerializer))
        return self.render_page(
            s.EventSerializer,
            EventService.list_visible(actor=request.user, prop=self.property, **query),
        )

    @extend_schema(request=s.EventCreateSerializer, responses={201: s.EventSerializer})
    def post(self, request):
        data = dict(self.parse(s.EventCreateSerializer))
        building_id = data.pop("building_id")
        building = (
            BuildingService.get_visible(
                actor=request.user, prop=self.property, building_id=building_id
            )
            if building_id
            else None
        )
        event = EventService.create(
            actor=request.user, prop=self.property, building=building, **data
        )
        return self.render(s.EventSerializer, event, status=status.HTTP_201_CREATED)


@extend_schema(tags=["Events"])
class EventDetailView(BaseAPIView):
    @extend_schema(responses=s.EventSerializer)
    def get(self, request, event_id: int):
        return self.render(
            s.EventSerializer,
            EventService.get_visible(
                actor=request.user, prop=self.property, event_id=event_id
            ),
        )

    @extend_schema(request=s.EventUpdateSerializer, responses=s.EventSerializer)
    def patch(self, request, event_id: int):
        event = EventService.get_visible(
            actor=request.user, prop=self.property, event_id=event_id
        )
        data = self.parse(s.EventUpdateSerializer)
        return self.render(
            s.EventSerializer,
            EventService.update(actor=request.user, event=event, changes=data),
        )

    @extend_schema(
        responses={204: None},
        description=(
            "Erases the event for good, with its files and the notifications already delivered "
            "(administrators and syndics). To archive it instead (keeping the record), use /archive/."
        ),
    )
    def delete(self, request, event_id: int):
        event = EventService.get_manageable(
            actor=request.user, prop=self.property, event_id=event_id
        )
        EventService.delete(actor=request.user, event=event)
        return Response(status=status.HTTP_204_NO_CONTENT)


@extend_schema(tags=["Events"])
class EventCancelView(BaseAPIView):
    @extend_schema(request=ActionReasonSerializer, responses=s.EventSerializer)
    def post(self, request, event_id: int):
        event = EventService.get_visible(
            actor=request.user, prop=self.property, event_id=event_id
        )
        data = self.parse(ActionReasonSerializer)
        return self.render(
            s.EventSerializer,
            EventService.cancel(actor=request.user, event=event, reason=data["reason"]),
        )


@extend_schema(tags=["Events"])
class EventArchiveView(BaseAPIView):
    """Archives the event: it leaves the feed but the record stays."""

    @extend_schema(request=None, responses=s.EventSerializer)
    def post(self, request, event_id: int):
        event = EventService.get_visible(
            actor=request.user, prop=self.property, event_id=event_id
        )
        EventService.archive(actor=request.user, event=event)
        return self.render(s.EventSerializer, event)


@extend_schema(tags=["Events"])
class EventFilesView(BaseAPIView):
    @extend_schema(request=UploadFilesSerializer, responses={201: s.EventSerializer})
    def post(self, request, event_id: int):
        event = EventService.get_visible(
            actor=request.user, prop=self.property, event_id=event_id
        )
        data = self.parse(UploadFilesSerializer)
        EventService.add_files(actor=request.user, event=event, files=data["files"])
        return self.render(s.EventSerializer, event, status=status.HTTP_201_CREATED)


@extend_schema(tags=["Events"])
class EventFileDetailView(BaseAPIView):
    @extend_schema(responses={204: None})
    def delete(self, request, event_id: int, attachment_id: int):
        event = EventService.get_visible(
            actor=request.user, prop=self.property, event_id=event_id
        )
        EventService.remove_file(
            actor=request.user, event=event, attachment_id=attachment_id
        )
        return Response(status=status.HTTP_204_NO_CONTENT)


@extend_schema(tags=["Events"])
class EventCompletePastView(BaseAPIView):
    @extend_schema(
        request=None,
        responses=BulkActionResultSerializer,
        description="Bulk action (admin, syndic, manager): completes every scheduled event of the selected property that has ended.",
    )
    def post(self, request):
        count = EventService.complete_past_in(actor=request.user, prop=self.property)
        return self.render(BulkActionResultSerializer, {"count": count})
