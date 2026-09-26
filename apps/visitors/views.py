from drf_spectacular.utils import extend_schema
from rest_framework import status
from rest_framework.response import Response

from apps.common.serializers import UploadFileSerializer
from apps.common.views import BaseAPIView
from apps.properties.services import UnitService
from apps.visitors import serializers as s
from apps.visitors.services import DETAIL_FIELDS, VisitorService


@extend_schema(tags=["Visitors"])
class VisitorListView(BaseAPIView):
    @extend_schema(
        parameters=[s.VisitorsQueryParamsSerializer],
        responses=s.VisitorSerializer(many=True),
    )
    def get(self, request):
        query = self.parse_query_params(s.VisitorsQueryParamsSerializer)
        return self.render_page(
            s.VisitorSerializer,
            VisitorService.list_visible(actor=request.user, property_id=self.property.pk, **query),
        )

    @extend_schema(request=s.VisitorCreateSerializer, responses={201: s.VisitorSerializer})
    def post(self, request):
        data = self.parse(s.VisitorCreateSerializer)
        unit = UnitService.get_visible(
            actor=request.user, prop=self.property, unit_id=data["unit_id"]
        )
        visitor = VisitorService.register(
            actor=request.user,
            unit=unit,
            first_name=data["first_name"],
            last_name=data["last_name"],
            admitted=data["admitted"],
            denial_reason=data["denial_reason"],
            id_card=data["id_card"],
            details={k: data[k] for k in DETAIL_FIELDS if k in data},
        )
        return self.render(s.VisitorSerializer, visitor, status=status.HTTP_201_CREATED)


@extend_schema(tags=["Visitors"])
class VisitorDetailView(BaseAPIView):
    @extend_schema(responses=s.VisitorSerializer)
    def get(self, request, visitor_id: int):
        return self.render(
            s.VisitorSerializer,
            VisitorService.get_visible(
                actor=request.user, prop=self.property, visitor_id=visitor_id
            ),
        )

    @extend_schema(request=s.VisitorUpdateSerializer, responses=s.VisitorSerializer)
    def patch(self, request, visitor_id: int):
        visitor = VisitorService.get_visible(
            actor=request.user, prop=self.property, visitor_id=visitor_id
        )
        data = self.parse(s.VisitorUpdateSerializer)
        return self.render(
            s.VisitorSerializer,
            VisitorService.update_details(actor=request.user, visitor=visitor, changes=data),
        )

    @extend_schema(
        responses={204: None},
        description="Deletes an entry logged by mistake (management only).",
    )
    def delete(self, request, visitor_id: int):
        visitor = VisitorService.get_visible(
            actor=request.user, prop=self.property, visitor_id=visitor_id
        )
        VisitorService.delete(actor=request.user, visitor=visitor)
        return Response(status=status.HTTP_204_NO_CONTENT)


@extend_schema(tags=["Visitors"])
class VisitorDepartureView(BaseAPIView):
    @extend_schema(request=s.VisitorDepartureSerializer, responses=s.VisitorSerializer)
    def post(self, request, visitor_id: int):
        visitor = VisitorService.get_visible(
            actor=request.user, prop=self.property, visitor_id=visitor_id
        )
        data = self.parse(s.VisitorDepartureSerializer)
        return self.render(
            s.VisitorSerializer,
            VisitorService.mark_left(actor=request.user, visitor=visitor, left_at=data["left_at"]),
        )


@extend_schema(tags=["Visitors"])
class VisitorIdCardView(BaseAPIView):
    @extend_schema(request=UploadFileSerializer, responses=s.VisitorSerializer)
    def patch(self, request, visitor_id: int):
        visitor = VisitorService.get_visible(
            actor=request.user, prop=self.property, visitor_id=visitor_id
        )
        data = self.parse(UploadFileSerializer)
        VisitorService.set_id_card(actor=request.user, visitor=visitor, upload=data["file"])
        return self.render(s.VisitorSerializer, visitor)
