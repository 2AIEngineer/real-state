"""Amenities: the shared facilities of a property, their schedule and images."""

from drf_spectacular.utils import extend_schema
from rest_framework import status
from rest_framework.response import Response

from apps.amenities import serializers as s
from apps.amenities.services import AmenityService
from apps.common.serializers import UploadFilesSerializer
from apps.common.views import BaseAPIView
from apps.properties.services import BuildingService


@extend_schema(tags=["Amenities"])
class AmenityListView(BaseAPIView):
    @extend_schema(
        parameters=[s.AmenitiesQueryParamsSerializer], responses=s.AmenitySerializer(many=True)
    )
    def get(self, request):
        query = self.parse_query_params(s.AmenitiesQueryParamsSerializer)
        qs = AmenityService.list_visible(
            actor=request.user, prop=self.property, include_inactive=query["include_inactive"]
        )
        return self.render_page(s.AmenitySerializer, qs)

    @extend_schema(request=s.AmenityCreateSerializer, responses={201: s.AmenitySerializer})
    def post(self, request):
        data = dict(self.parse(s.AmenityCreateSerializer))
        building_id = data.pop("building_id")
        building = (
            BuildingService.get_visible(
                actor=request.user, prop=self.property, building_id=building_id
            )
            if building_id
            else None
        )
        amenity = AmenityService.create(
            actor=request.user, prop=self.property, building=building, data=data
        )
        return self.render(s.AmenitySerializer, amenity, status=status.HTTP_201_CREATED)


@extend_schema(tags=["Amenities"])
class AmenityDetailView(BaseAPIView):
    @extend_schema(responses=s.AmenitySerializer)
    def get(self, request, amenity_id: int):
        return self.render(
            s.AmenitySerializer,
            AmenityService.get_visible(
                actor=request.user, prop=self.property, amenity_id=amenity_id
            ),
        )

    @extend_schema(request=s.AmenityUpdateSerializer, responses=s.AmenitySerializer)
    def patch(self, request, amenity_id: int):
        amenity = AmenityService.get_visible(
            actor=request.user, prop=self.property, amenity_id=amenity_id
        )
        data = self.parse(s.AmenityUpdateSerializer)
        return self.render(
            s.AmenitySerializer,
            AmenityService.update(actor=request.user, amenity=amenity, changes=data),
        )

    @extend_schema(responses={204: None}, description="Deletes an amenity that was never booked.")
    def delete(self, request, amenity_id: int):
        amenity = AmenityService.get_visible(
            actor=request.user, prop=self.property, amenity_id=amenity_id
        )
        AmenityService.delete(actor=request.user, amenity=amenity)
        return Response(status=status.HTTP_204_NO_CONTENT)


@extend_schema(tags=["Amenities"])
class AmenityScheduleView(BaseAPIView):
    pagination_class = None  # a plain list of slots

    @extend_schema(
        parameters=[s.AmenityScheduleQueryParamsSerializer],
        responses=s.AmenitySlotSerializer(many=True),
    )
    def get(self, request, amenity_id: int):
        amenity = AmenityService.get_visible(
            actor=request.user, prop=self.property, amenity_id=amenity_id
        )
        query = self.parse_query_params(s.AmenityScheduleQueryParamsSerializer)
        return self.render(
            s.AmenitySlotSerializer,
            AmenityService.schedule(actor=request.user, amenity=amenity, **query),
            many=True,
        )


@extend_schema(tags=["Amenities"])
class AmenityImagesView(BaseAPIView):
    @extend_schema(request=UploadFilesSerializer, responses={201: s.AmenitySerializer})
    def post(self, request, amenity_id: int):
        amenity = AmenityService.get_visible(
            actor=request.user, prop=self.property, amenity_id=amenity_id
        )
        data = self.parse(UploadFilesSerializer)
        AmenityService.add_images(actor=request.user, amenity=amenity, files=data["files"])
        return self.render(s.AmenitySerializer, amenity, status=status.HTTP_201_CREATED)


@extend_schema(tags=["Amenities"])
class AmenityImageDetailView(BaseAPIView):
    @extend_schema(responses={204: None})
    def delete(self, request, amenity_id: int, attachment_id: int):
        amenity = AmenityService.get_visible(
            actor=request.user, prop=self.property, amenity_id=amenity_id
        )
        AmenityService.remove_image(
            actor=request.user, amenity=amenity, attachment_id=attachment_id
        )
        return Response(status=status.HTTP_204_NO_CONTENT)
