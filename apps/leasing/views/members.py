"""Lease members: the people living under a lease, and their documents."""

from drf_spectacular.utils import extend_schema
from rest_framework import status

from apps.accounts.services.accounts import AccountService
from apps.common.serializers import (
    UploadFileSerializer,
)
from apps.common.views import BaseAPIView
from apps.leasing import serializers as s
from apps.leasing.services import (
    LeaseMemberService,
    LeaseService,
    MemberInput,
)

EXTRA_KEYS = (
    "emergency_contact_name",
    "emergency_contact_phone",
    "emergency_contact_relation",
    "vehicles_info",
    "pets_info",
)


def member_input(raw: dict) -> MemberInput:
    user = AccountService.resolve(user_id=raw["user_id"], field="members")
    return MemberInput(
        user=user,
        is_signatory=raw["is_signatory"],
        joined_at=raw.get("joined_at"),
        extras={k: raw[k] for k in EXTRA_KEYS if k in raw},
    )


@extend_schema(tags=["Lease members"])
class LeaseMemberListView(BaseAPIView):
    @extend_schema(request=s.LeaseMemberInputSerializer, responses={201: s.LeaseMemberSerializer})
    def post(self, request, lease_id: int):
        lease = LeaseService.get_visible(actor=request.user, prop=self.property, lease_id=lease_id)
        data = self.parse(s.LeaseMemberInputSerializer)
        member = LeaseMemberService.add(actor=request.user, lease=lease, member=member_input(data))
        return self.render(s.LeaseMemberSerializer, member, status=status.HTTP_201_CREATED)


@extend_schema(tags=["Lease members"])
class LeaseMemberDetailView(BaseAPIView):
    @extend_schema(responses=s.LeaseMemberSerializer)
    def get(self, request, member_id: int):
        return self.render(
            s.LeaseMemberSerializer,
            LeaseMemberService.get_visible(
                actor=request.user, prop=self.property, member_id=member_id
            ),
        )

    @extend_schema(request=s.LeaseMemberUpdateSerializer, responses=s.LeaseMemberSerializer)
    def patch(self, request, member_id: int):
        member = LeaseMemberService.get_visible(
            actor=request.user, prop=self.property, member_id=member_id
        )
        data = self.parse(s.LeaseMemberUpdateSerializer)
        return self.render(
            s.LeaseMemberSerializer,
            LeaseMemberService.update(actor=request.user, member=member, changes=data),
        )


@extend_schema(tags=["Lease members"])
class LeaseMemberDepartureView(BaseAPIView):
    @extend_schema(request=s.LeaseMemberDepartureSerializer, responses=s.LeaseMemberSerializer)
    def post(self, request, member_id: int):
        member = LeaseMemberService.get_visible(
            actor=request.user, prop=self.property, member_id=member_id
        )
        data = self.parse(s.LeaseMemberDepartureSerializer)
        return self.render(
            s.LeaseMemberSerializer,
            LeaseMemberService.record_departure(
                actor=request.user, member=member, left_at=data["left_at"]
            ),
        )


@extend_schema(tags=["Lease members"])
class LeaseMemberProofOfIdentityView(BaseAPIView):
    @extend_schema(request=UploadFileSerializer, responses=s.LeaseMemberSerializer)
    def patch(self, request, member_id: int):
        member = LeaseMemberService.get_visible(
            actor=request.user, prop=self.property, member_id=member_id
        )
        data = self.parse(UploadFileSerializer)
        LeaseMemberService.set_proof_of_identity(
            actor=request.user, member=member, upload=data["file"]
        )
        return self.render(s.LeaseMemberSerializer, member)


@extend_schema(tags=["Lease members"])
class LeaseMemberProofOfAddressView(BaseAPIView):
    @extend_schema(request=UploadFileSerializer, responses=s.LeaseMemberSerializer)
    def patch(self, request, member_id: int):
        member = LeaseMemberService.get_visible(
            actor=request.user, prop=self.property, member_id=member_id
        )
        data = self.parse(UploadFileSerializer)
        LeaseMemberService.set_proof_of_address(
            actor=request.user, member=member, upload=data["file"]
        )
        return self.render(s.LeaseMemberSerializer, member)
