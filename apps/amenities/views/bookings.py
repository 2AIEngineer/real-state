"""Bookings of amenities."""

from drf_spectacular.utils import extend_schema
from rest_framework import status
from rest_framework.response import Response

from apps.amenities import serializers as s
from apps.amenities.services import AmenityService, BookingService
from apps.common.serializers import ActionReasonSerializer
from apps.common.views import BaseAPIView


@extend_schema(tags=["Bookings"])
class BookingListView(BaseAPIView):
    @extend_schema(
        parameters=[s.BookingsQueryParamsSerializer], responses=s.BookingSerializer(many=True)
    )
    def get(self, request):
        query = self.parse_query_params(s.BookingsQueryParamsSerializer)
        return self.render_page(
            s.BookingSerializer,
            BookingService.list_visible(actor=request.user, property_id=self.property.pk, **query),
        )

    @extend_schema(request=s.BookingCreateSerializer, responses={201: s.BookingSerializer})
    def post(self, request):
        data = self.parse(s.BookingCreateSerializer)
        amenity = AmenityService.get_visible(
            actor=request.user, prop=self.property, amenity_id=data["amenity_id"]
        )
        booking = BookingService.book(
            actor=request.user,
            amenity=amenity,
            start=data["start_datetime"],
            end=data["end_datetime"],
            party_size=data["party_size"],
            note=data["note"],
        )
        return self.render(s.BookingSerializer, booking, status=status.HTTP_201_CREATED)


@extend_schema(tags=["Bookings"])
class BookingDetailView(BaseAPIView):
    @extend_schema(responses=s.BookingSerializer)
    def get(self, request, booking_id: int):
        return self.render(
            s.BookingSerializer,
            BookingService.get_visible(
                actor=request.user, prop=self.property, booking_id=booking_id
            ),
        )

    @extend_schema(
        responses={204: None}, description="Permanently deletes the booking and its conversation."
    )
    def delete(self, request, booking_id: int):
        booking = BookingService.get_visible(
            actor=request.user, prop=self.property, booking_id=booking_id
        )
        BookingService.delete(actor=request.user, booking=booking)
        return Response(status=status.HTTP_204_NO_CONTENT)


@extend_schema(tags=["Bookings"])
class BookingDecisionView(BaseAPIView):
    @extend_schema(request=s.BookingDecisionSerializer, responses=s.BookingSerializer)
    def post(self, request, booking_id: int):
        booking = BookingService.get_visible(
            actor=request.user, prop=self.property, booking_id=booking_id
        )
        data = self.parse(s.BookingDecisionSerializer)
        return self.render(
            s.BookingSerializer, BookingService.decide(actor=request.user, booking=booking, **data)
        )


@extend_schema(tags=["Bookings"])
class BookingCancelView(BaseAPIView):
    @extend_schema(request=ActionReasonSerializer, responses=s.BookingSerializer)
    def post(self, request, booking_id: int):
        booking = BookingService.get_visible(
            actor=request.user, prop=self.property, booking_id=booking_id
        )
        data = self.parse(ActionReasonSerializer)
        return self.render(
            s.BookingSerializer,
            BookingService.cancel(actor=request.user, booking=booking, reason=data["reason"]),
        )
