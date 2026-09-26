from drf_spectacular.utils import extend_schema
from rest_framework import status
from rest_framework.response import Response
from rest_framework.views import APIView

from apps.common.views import ApiMixin, BaseAPIView
from apps.properties import serializers as s
from apps.properties.services import (
    BuildingService,
    UnitService,
)


@extend_schema(tags=["Units"])
class UnitListView(BaseAPIView):
    @extend_schema(responses=s.UnitSerializer(many=True))
    def get(self, request, building_id: int):
        building = BuildingService.get_visible(
            actor=request.user, prop=self.property, building_id=building_id
        )
        return self.render_page(
            s.UnitSerializer,
            UnitService.list_for_building(actor=request.user, building=building),
        )

    @extend_schema(request=s.UnitInputSerializer, responses={201: s.UnitSerializer})
    def post(self, request, building_id: int):
        building = BuildingService.get_visible(
            actor=request.user, prop=self.property, building_id=building_id
        )
        data = self.parse(s.UnitInputSerializer)
        return self.render(
            s.UnitSerializer,
            UnitService.create(actor=request.user, building=building, data=data),
            status=status.HTTP_201_CREATED,
        )


@extend_schema(tags=["Units"])
class MyUnitsView(ApiMixin, APIView):
    @extend_schema(responses=s.UnitSerializer(many=True))
    def get(self, request):
        return self.render_page(s.UnitSerializer, UnitService.list_mine(actor=request.user))


@extend_schema(tags=["Units"])
class UnitDetailView(BaseAPIView):
    @extend_schema(responses=s.UnitSerializer)
    def get(self, request, unit_id: int):
        unit = UnitService.get_visible(actor=request.user, prop=self.property, unit_id=unit_id)
        return self.render(s.UnitSerializer, unit)

    @extend_schema(request=s.UnitUpdateSerializer, responses=s.UnitSerializer)
    def patch(self, request, unit_id: int):
        unit = UnitService.get_visible(actor=request.user, prop=self.property, unit_id=unit_id)
        data = self.parse(s.UnitUpdateSerializer)
        return self.render(
            s.UnitSerializer,
            UnitService.update(actor=request.user, unit=unit, changes=data),
        )

    @extend_schema(
        responses={204: None},
        description="Deletes a unit that was never leased nor sold.",
    )
    def delete(self, request, unit_id: int):
        unit = UnitService.get_visible(actor=request.user, prop=self.property, unit_id=unit_id)
        UnitService.delete(actor=request.user, unit=unit)
        return Response(status=status.HTTP_204_NO_CONTENT)
