from drf_spectacular.utils import extend_schema
from rest_framework import status
from rest_framework.response import Response

from apps.announcements import serializers as s
from apps.announcements.services import AnnouncementService
from apps.common.serializers import UploadFilesSerializer
from apps.common.views import BaseAPIView
from apps.properties.services import BuildingService


@extend_schema(tags=["Announcements"])
class AnnouncementListView(BaseAPIView):
    @extend_schema(
        parameters=[s.AnnouncementsQueryParamsSerializer],
        responses=s.AnnouncementSerializer(many=True),
    )
    def get(self, request):
        query = self.parse_query_params(s.AnnouncementsQueryParamsSerializer)
        qs = AnnouncementService.list_visible(
            actor=request.user,
            prop=self.property,
            include_expired=query["include_expired"],
            category=query.get("category"),
        )
        return self.render_page(s.AnnouncementSerializer, qs)

    @extend_schema(
        request=s.AnnouncementCreateSerializer,
        responses={201: s.AnnouncementSerializer},
    )
    def post(self, request):
        data = dict(self.parse(s.AnnouncementCreateSerializer))
        building_id = data.pop("building_id")
        building = (
            BuildingService.get_visible(
                actor=request.user, prop=self.property, building_id=building_id
            )
            if building_id
            else None
        )
        announcement = AnnouncementService.publish(
            actor=request.user, prop=self.property, building=building, **data
        )
        return self.render(
            s.AnnouncementSerializer, announcement, status=status.HTTP_201_CREATED
        )


@extend_schema(tags=["Announcements"])
class AnnouncementDetailView(BaseAPIView):
    @extend_schema(responses=s.AnnouncementSerializer)
    def get(self, request, announcement_id: int):
        return self.render(
            s.AnnouncementSerializer,
            AnnouncementService.get_visible(
                actor=request.user, prop=self.property, announcement_id=announcement_id
            ),
        )

    @extend_schema(
        request=s.AnnouncementUpdateSerializer, responses=s.AnnouncementSerializer
    )
    def patch(self, request, announcement_id: int):
        announcement = AnnouncementService.get_visible(
            actor=request.user, prop=self.property, announcement_id=announcement_id
        )
        data = self.parse(s.AnnouncementUpdateSerializer)
        return self.render(
            s.AnnouncementSerializer,
            AnnouncementService.update(
                actor=request.user, announcement=announcement, changes=data
            ),
        )

    @extend_schema(
        responses={204: None},
        description=(
            "Erases the announcement for good, with its files and the notifications already delivered "
            "(administrators and syndics). To archive it instead (keeping the record), use /archive/."
        ),
    )
    def delete(self, request, announcement_id: int):
        announcement = AnnouncementService.get_manageable(
            actor=request.user, prop=self.property, announcement_id=announcement_id
        )
        AnnouncementService.delete(actor=request.user, announcement=announcement)
        return Response(status=status.HTTP_204_NO_CONTENT)


@extend_schema(tags=["Announcements"])
class AnnouncementArchiveView(BaseAPIView):
    """Archives the announcement: it leaves the feed but the record stays."""

    @extend_schema(request=None, responses=s.AnnouncementSerializer)
    def post(self, request, announcement_id: int):
        announcement = AnnouncementService.get_visible(
            actor=request.user, prop=self.property, announcement_id=announcement_id
        )
        AnnouncementService.archive(actor=request.user, announcement=announcement)
        return self.render(s.AnnouncementSerializer, announcement)


@extend_schema(tags=["Announcements"])
class AnnouncementFilesView(BaseAPIView):
    @extend_schema(
        request=UploadFilesSerializer, responses={201: s.AnnouncementSerializer}
    )
    def post(self, request, announcement_id: int):
        announcement = AnnouncementService.get_visible(
            actor=request.user, prop=self.property, announcement_id=announcement_id
        )
        data = self.parse(UploadFilesSerializer)
        AnnouncementService.add_files(
            actor=request.user, announcement=announcement, files=data["files"]
        )
        return self.render(
            s.AnnouncementSerializer, announcement, status=status.HTTP_201_CREATED
        )


@extend_schema(tags=["Announcements"])
class AnnouncementFileDetailView(BaseAPIView):
    @extend_schema(responses={204: None})
    def delete(self, request, announcement_id: int, attachment_id: int):
        announcement = AnnouncementService.get_visible(
            actor=request.user, prop=self.property, announcement_id=announcement_id
        )
        AnnouncementService.remove_file(
            actor=request.user, announcement=announcement, attachment_id=attachment_id
        )
        return Response(status=status.HTTP_204_NO_CONTENT)
