"""Short-term rentals: declaring, rescheduling, checking in and out, cancelling."""

from drf_spectacular.utils import extend_schema
from rest_framework import status
from rest_framework.response import Response

from apps.common.serializers import ActionReasonSerializer, BulkActionResultSerializer
from apps.common.views import BaseAPIView
from apps.properties.services import UnitService
from apps.short_term_rental import serializers as s
from apps.short_term_rental.services import (
    ShortTermRentalService,
)
from apps.short_term_rental.views.members import member_input


@extend_schema(tags=["Short-term rentals"])
class ShortTermRentalListView(BaseAPIView):
    @extend_schema(
        parameters=[s.ShortTermRentalsQueryParamsSerializer],
        responses=s.ShortTermRentalSerializer(many=True),
    )
    def get(self, request):
        query = self.parse_query_params(s.ShortTermRentalsQueryParamsSerializer)
        qs = ShortTermRentalService.list_visible(
            actor=request.user, property_id=self.property.pk, **query
        ).prefetch_related("members")
        return self.render_page(s.ShortTermRentalSerializer, qs)

    @extend_schema(
        request=s.ShortTermRentalCreateSerializer,
        responses={201: s.ShortTermRentalSerializer},
    )
    def post(self, request):
        data = self.parse(s.ShortTermRentalCreateSerializer)
        unit = UnitService.get_visible(
            actor=request.user, prop=self.property, unit_id=data["unit_id"]
        )
        rental = ShortTermRentalService.declare(
            actor=request.user,
            unit=unit,
            checkin_date=data["checkin_date"],
            checkout_date=data["checkout_date"],
            members=[member_input(g) for g in data["members"]],
            primary_index=data["primary_index"],
            notes=data["notes"],
        )
        return self.render(
            s.ShortTermRentalSerializer, rental, status=status.HTTP_201_CREATED
        )


@extend_schema(tags=["Short-term rentals"])
class ShortTermRentalDetailView(BaseAPIView):
    @extend_schema(responses=s.ShortTermRentalSerializer)
    def get(self, request, short_term_rental_id: int):
        return self.render(
            s.ShortTermRentalSerializer,
            ShortTermRentalService.get_visible(
                actor=request.user,
                prop=self.property,
                short_term_rental_id=short_term_rental_id,
            ),
        )

    @extend_schema(
        responses={204: None},
        description="Permanently deletes the rental and its members.",
    )
    def delete(self, request, short_term_rental_id: int):
        rental = ShortTermRentalService.get_visible(
            actor=request.user,
            prop=self.property,
            short_term_rental_id=short_term_rental_id,
        )
        ShortTermRentalService.delete(actor=request.user, rental=rental)
        return Response(status=status.HTTP_204_NO_CONTENT)


@extend_schema(tags=["Short-term rentals"])
class RescheduleView(BaseAPIView):
    @extend_schema(
        request=s.ShortTermRentalRescheduleSerializer,
        responses=s.ShortTermRentalSerializer,
    )
    def post(self, request, short_term_rental_id: int):
        rental = ShortTermRentalService.get_visible(
            actor=request.user,
            prop=self.property,
            short_term_rental_id=short_term_rental_id,
        )
        data = self.parse(s.ShortTermRentalRescheduleSerializer)
        return self.render(
            s.ShortTermRentalSerializer,
            ShortTermRentalService.reschedule(
                actor=request.user, rental=rental, **data
            ),
        )


class _TransitionView(BaseAPIView):
    transition = ""

    @extend_schema(
        tags=["Short-term rentals"], request=None, responses=s.ShortTermRentalSerializer
    )
    def post(self, request, short_term_rental_id: int):
        rental = ShortTermRentalService.get_visible(
            actor=request.user,
            prop=self.property,
            short_term_rental_id=short_term_rental_id,
        )
        return self.render(
            s.ShortTermRentalSerializer,
            getattr(ShortTermRentalService, self.transition)(
                actor=request.user, rental=rental
            ),
        )


class CheckInView(_TransitionView):
    transition = "check_in"


class CompleteView(_TransitionView):
    transition = "complete"


@extend_schema(tags=["Short-term rentals"])
class CancelView(BaseAPIView):
    @extend_schema(
        request=ActionReasonSerializer, responses=s.ShortTermRentalSerializer
    )
    def post(self, request, short_term_rental_id: int):
        rental = ShortTermRentalService.get_visible(
            actor=request.user,
            prop=self.property,
            short_term_rental_id=short_term_rental_id,
        )
        data = self.parse(ActionReasonSerializer)
        return self.render(
            s.ShortTermRentalSerializer,
            ShortTermRentalService.cancel(
                actor=request.user, rental=rental, reason=data["reason"]
            ),
        )


@extend_schema(tags=["Short-term rentals"])
class ShortTermRentalCompletePastView(BaseAPIView):
    @extend_schema(
        request=None,
        responses=BulkActionResultSerializer,
        description="Bulk action (admin, syndic, manager): completes every scheduled or checked-in rental of the selected property whose checkout date has passed.",
    )
    def post(self, request):
        count = ShortTermRentalService.complete_past_in(
            actor=request.user, prop=self.property
        )
        return self.render(BulkActionResultSerializer, {"count": count})
