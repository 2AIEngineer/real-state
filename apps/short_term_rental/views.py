from drf_spectacular.utils import extend_schema
from rest_framework import status
from rest_framework.response import Response

from apps.common.serializers import ActionReasonSerializer, UploadFileSerializer
from apps.common.views import BaseAPIView
from apps.properties.services import UnitService
from apps.short_term_rental import serializers as s
from apps.short_term_rental.services import (
    ShortTermRentalMemberInput,
    ShortTermRentalMemberService,
    ShortTermRentalService,
)


def _member_input(data: dict) -> ShortTermRentalMemberInput:
    data = dict(data)
    data.pop("make_primary", None)
    return ShortTermRentalMemberInput(
        first_name=data.pop("first_name", ""), last_name=data.pop("last_name", ""), data=data
    )


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
        request=s.ShortTermRentalCreateSerializer, responses={201: s.ShortTermRentalSerializer}
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
            members=[_member_input(g) for g in data["members"]],
            primary_index=data["primary_index"],
            notes=data["notes"],
        )
        return self.render(s.ShortTermRentalSerializer, rental, status=status.HTTP_201_CREATED)


@extend_schema(tags=["Short-term rentals"])
class ShortTermRentalDetailView(BaseAPIView):
    @extend_schema(responses=s.ShortTermRentalSerializer)
    def get(self, request, short_term_rental_id: int):
        return self.render(
            s.ShortTermRentalSerializer,
            ShortTermRentalService.get_visible(
                actor=request.user, prop=self.property, short_term_rental_id=short_term_rental_id
            ),
        )

    @extend_schema(
        responses={204: None}, description="Permanently deletes the rental and its members."
    )
    def delete(self, request, short_term_rental_id: int):
        rental = ShortTermRentalService.get_visible(
            actor=request.user, prop=self.property, short_term_rental_id=short_term_rental_id
        )
        ShortTermRentalService.delete(actor=request.user, rental=rental)
        return Response(status=status.HTTP_204_NO_CONTENT)


@extend_schema(tags=["Short-term rentals"])
class RescheduleView(BaseAPIView):
    @extend_schema(
        request=s.ShortTermRentalRescheduleSerializer, responses=s.ShortTermRentalSerializer
    )
    def post(self, request, short_term_rental_id: int):
        rental = ShortTermRentalService.get_visible(
            actor=request.user, prop=self.property, short_term_rental_id=short_term_rental_id
        )
        data = self.parse(s.ShortTermRentalRescheduleSerializer)
        return self.render(
            s.ShortTermRentalSerializer,
            ShortTermRentalService.reschedule(actor=request.user, rental=rental, **data),
        )


class _TransitionView(BaseAPIView):
    transition = ""

    @extend_schema(tags=["Short-term rentals"], request=None, responses=s.ShortTermRentalSerializer)
    def post(self, request, short_term_rental_id: int):
        rental = ShortTermRentalService.get_visible(
            actor=request.user, prop=self.property, short_term_rental_id=short_term_rental_id
        )
        return self.render(
            s.ShortTermRentalSerializer,
            getattr(ShortTermRentalService, self.transition)(actor=request.user, rental=rental),
        )


class CheckInView(_TransitionView):
    transition = "check_in"


class CompleteView(_TransitionView):
    transition = "complete"


@extend_schema(tags=["Short-term rentals"])
class CancelView(BaseAPIView):
    @extend_schema(request=ActionReasonSerializer, responses=s.ShortTermRentalSerializer)
    def post(self, request, short_term_rental_id: int):
        rental = ShortTermRentalService.get_visible(
            actor=request.user, prop=self.property, short_term_rental_id=short_term_rental_id
        )
        data = self.parse(ActionReasonSerializer)
        return self.render(
            s.ShortTermRentalSerializer,
            ShortTermRentalService.cancel(actor=request.user, rental=rental, reason=data["reason"]),
        )


@extend_schema(tags=["Short-term rentals"])
class MemberListView(BaseAPIView):
    pagination_class = None  # a plain list of members

    @extend_schema(responses=s.ShortTermRentalMemberSerializer(many=True))
    def get(self, request, short_term_rental_id: int):
        rental = ShortTermRentalService.get_visible(
            actor=request.user, prop=self.property, short_term_rental_id=short_term_rental_id
        )
        return self.render(
            s.ShortTermRentalMemberSerializer,
            ShortTermRentalMemberService.list_for_rental(actor=request.user, rental=rental),
            many=True,
        )

    @extend_schema(
        request=s.ShortTermRentalMemberCreateSerializer,
        responses={201: s.ShortTermRentalMemberSerializer},
    )
    def post(self, request, short_term_rental_id: int):
        rental = ShortTermRentalService.get_visible(
            actor=request.user, prop=self.property, short_term_rental_id=short_term_rental_id
        )
        data = self.parse(s.ShortTermRentalMemberCreateSerializer)
        member = ShortTermRentalMemberService.add(
            actor=request.user,
            rental=rental,
            new_member=_member_input(data),
            make_primary=data["make_primary"],
        )
        return self.render(
            s.ShortTermRentalMemberSerializer, member, status=status.HTTP_201_CREATED
        )


@extend_schema(tags=["Short-term rentals"])
class MemberDetailView(BaseAPIView):
    @extend_schema(
        request=s.ShortTermRentalMemberUpdateSerializer, responses=s.ShortTermRentalMemberSerializer
    )
    def patch(self, request, short_term_rental_member_id: int):
        member = ShortTermRentalMemberService.get_visible(
            actor=request.user, prop=self.property, member_id=short_term_rental_member_id
        )
        data = dict(self.parse(s.ShortTermRentalMemberUpdateSerializer))
        make_primary = data.pop("make_primary", False)
        return self.render(
            s.ShortTermRentalMemberSerializer,
            ShortTermRentalMemberService.update(
                actor=request.user, member=member, changes=data, make_primary=make_primary
            ),
        )

    @extend_schema(responses={204: None})
    def delete(self, request, short_term_rental_member_id: int):
        member = ShortTermRentalMemberService.get_visible(
            actor=request.user, prop=self.property, member_id=short_term_rental_member_id
        )
        ShortTermRentalMemberService.remove(actor=request.user, member=member)
        return Response(status=status.HTTP_204_NO_CONTENT)


@extend_schema(tags=["Short-term rentals"])
class MemberIdCardView(BaseAPIView):
    @extend_schema(request=UploadFileSerializer, responses=s.ShortTermRentalMemberSerializer)
    def patch(self, request, short_term_rental_member_id: int):
        member = ShortTermRentalMemberService.get_visible(
            actor=request.user, prop=self.property, member_id=short_term_rental_member_id
        )
        data = self.parse(UploadFileSerializer)
        ShortTermRentalMemberService.set_id_card(
            actor=request.user, member=member, upload=data["file"]
        )
        return self.render(s.ShortTermRentalMemberSerializer, member)
