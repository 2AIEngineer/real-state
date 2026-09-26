"""The guests of a short-term rental, and their identity cards."""

from drf_spectacular.utils import extend_schema
from rest_framework import status
from rest_framework.response import Response

from apps.common.serializers import UploadFileSerializer
from apps.common.views import BaseAPIView
from apps.short_term_rental import serializers as s
from apps.short_term_rental.services import (
    ShortTermRentalMemberInput,
    ShortTermRentalMemberService,
    ShortTermRentalService,
)


def member_input(data: dict) -> ShortTermRentalMemberInput:
    data = dict(data)
    data.pop("make_primary", None)
    return ShortTermRentalMemberInput(
        first_name=data.pop("first_name", ""),
        last_name=data.pop("last_name", ""),
        data=data,
    )


@extend_schema(tags=["Short-term rentals"])
class MemberListView(BaseAPIView):
    pagination_class = None  # a plain list of members

    @extend_schema(responses=s.ShortTermRentalMemberSerializer(many=True))
    def get(self, request, short_term_rental_id: int):
        rental = ShortTermRentalService.get_visible(
            actor=request.user,
            prop=self.property,
            short_term_rental_id=short_term_rental_id,
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
            actor=request.user,
            prop=self.property,
            short_term_rental_id=short_term_rental_id,
        )
        data = self.parse(s.ShortTermRentalMemberCreateSerializer)
        member = ShortTermRentalMemberService.add(
            actor=request.user,
            rental=rental,
            new_member=member_input(data),
            make_primary=data["make_primary"],
        )
        return self.render(
            s.ShortTermRentalMemberSerializer, member, status=status.HTTP_201_CREATED
        )


@extend_schema(tags=["Short-term rentals"])
class MemberDetailView(BaseAPIView):
    @extend_schema(
        request=s.ShortTermRentalMemberUpdateSerializer,
        responses=s.ShortTermRentalMemberSerializer,
    )
    def patch(self, request, short_term_rental_member_id: int):
        member = ShortTermRentalMemberService.get_visible(
            actor=request.user,
            prop=self.property,
            member_id=short_term_rental_member_id,
        )
        data = dict(self.parse(s.ShortTermRentalMemberUpdateSerializer))
        make_primary = data.pop("make_primary", False)
        return self.render(
            s.ShortTermRentalMemberSerializer,
            ShortTermRentalMemberService.update(
                actor=request.user,
                member=member,
                changes=data,
                make_primary=make_primary,
            ),
        )

    @extend_schema(responses={204: None})
    def delete(self, request, short_term_rental_member_id: int):
        member = ShortTermRentalMemberService.get_visible(
            actor=request.user,
            prop=self.property,
            member_id=short_term_rental_member_id,
        )
        ShortTermRentalMemberService.remove(actor=request.user, member=member)
        return Response(status=status.HTTP_204_NO_CONTENT)


@extend_schema(tags=["Short-term rentals"])
class MemberIdCardView(BaseAPIView):
    @extend_schema(request=UploadFileSerializer, responses=s.ShortTermRentalMemberSerializer)
    def patch(self, request, short_term_rental_member_id: int):
        member = ShortTermRentalMemberService.get_visible(
            actor=request.user,
            prop=self.property,
            member_id=short_term_rental_member_id,
        )
        data = self.parse(UploadFileSerializer)
        ShortTermRentalMemberService.set_id_card(
            actor=request.user, member=member, upload=data["file"]
        )
        return self.render(s.ShortTermRentalMemberSerializer, member)
