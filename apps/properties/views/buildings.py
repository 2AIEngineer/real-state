from drf_spectacular.utils import extend_schema
from rest_framework import status
from rest_framework.response import Response

from apps.common.views import BaseAPIView
from apps.properties import serializers as s
from apps.properties.services import BuildingService


@extend_schema(tags=["Buildings"])
class BuildingListView(BaseAPIView):
    @extend_schema(responses=s.BuildingSerializer(many=True))
    def get(self, request, property_id: int):
        prop = self.selected_property(property_id)
        return self.render_page(
            s.BuildingSerializer,
            BuildingService.list_for_property(actor=request.user, prop=prop),
        )

    @extend_schema(request=s.BuildingInputSerializer, responses={201: s.BuildingSerializer})
    def post(self, request, property_id: int):
        prop = self.selected_property(property_id)
        data = self.parse(s.BuildingInputSerializer)
        return self.render(
            s.BuildingSerializer,
            BuildingService.create(actor=request.user, prop=prop, data=data),
            status=status.HTTP_201_CREATED,
        )


@extend_schema(tags=["Buildings"])
class BuildingDetailView(BaseAPIView):
    @extend_schema(responses=s.BuildingSerializer)
    def get(self, request, building_id: int):
        return self.render(
            s.BuildingSerializer,
            BuildingService.get_visible(
                actor=request.user, prop=self.property, building_id=building_id
            ),
        )

    @extend_schema(request=s.BuildingUpdateSerializer, responses=s.BuildingSerializer)
    def patch(self, request, building_id: int):
        building = BuildingService.get_visible(
            actor=request.user, prop=self.property, building_id=building_id
        )
        data = self.parse(s.BuildingUpdateSerializer)
        return self.render(
            s.BuildingSerializer,
            BuildingService.update(actor=request.user, building=building, changes=data),
        )

    @extend_schema(responses={204: None}, description="Deletes an empty building.")
    def delete(self, request, building_id: int):
        building = BuildingService.get_visible(
            actor=request.user, prop=self.property, building_id=building_id
        )
        BuildingService.delete(actor=request.user, building=building)
        return Response(status=status.HTTP_204_NO_CONTENT)
