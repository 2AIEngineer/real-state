from drf_spectacular.utils import extend_schema
from rest_framework import status
from rest_framework.response import Response

from apps.accounts.services.accounts import AccountService
from apps.common.serializers import (
    ActionReasonSerializer,
    UploadFileSerializer,
    UploadFilesSerializer,
)
from apps.common.views import BaseAPIView
from apps.leasing import serializers as s
from apps.leasing.services import (
    LeaseComponentStateService,
    LeaseMemberService,
    LeaseService,
    MemberInput,
)
from apps.properties.services import UnitService

EXTRA_KEYS = (
    "emergency_contact_name",
    "emergency_contact_phone",
    "emergency_contact_relation",
    "vehicles_info",
    "pets_info",
)


def _member_input(raw: dict) -> MemberInput:
    user = AccountService.resolve(user_id=raw["user_id"], field="members")
    return MemberInput(
        user=user,
        is_signatory=raw["is_signatory"],
        joined_at=raw.get("joined_at"),
        extras={k: raw[k] for k in EXTRA_KEYS if k in raw},
    )


@extend_schema(tags=["Leases"])
class LeaseListView(BaseAPIView):
    @extend_schema(
        parameters=[s.LeasesQueryParamsSerializer], responses=s.LeaseSerializer(many=True)
    )
    def get(self, request):
        query = self.parse_query_params(s.LeasesQueryParamsSerializer)
        return self.render_page(
            s.LeaseSerializer,
            LeaseService.list_visible(
                actor=request.user, property_id=self.selected_property_id, **query
            ),
        )

    @extend_schema(request=s.LeaseCreateSerializer, responses={201: s.LeaseSerializer})
    def post(self, request):
        data = self.parse(s.LeaseCreateSerializer)
        unit = UnitService.get(unit_id=data["unit_id"])
        lease = LeaseService.create(
            actor=request.user,
            unit=unit,
            start_date=data["start_date"],
            end_date=data["end_date"],
            contract_reference=data["contract_reference"],
            notes=data["notes"],
            members=[_member_input(m) for m in data["members"]],
        )
        return self.render(
            s.LeaseSerializer,
            LeaseService.get_visible(actor=request.user, lease_id=lease.pk),
            status=status.HTTP_201_CREATED,
        )


@extend_schema(tags=["Leases"])
class LeaseDetailView(BaseAPIView):
    @extend_schema(responses=s.LeaseSerializer)
    def get(self, request, lease_id: int):
        return self.render(
            s.LeaseSerializer, LeaseService.get_visible(actor=request.user, lease_id=lease_id)
        )

    @extend_schema(request=s.LeaseUpdateSerializer, responses=s.LeaseSerializer)
    def patch(self, request, lease_id: int):
        lease = LeaseService.get_visible(actor=request.user, lease_id=lease_id)
        data = self.parse(s.LeaseUpdateSerializer)
        LeaseService.update(actor=request.user, lease=lease, changes=data)
        return self.render(
            s.LeaseSerializer, LeaseService.get_visible(actor=request.user, lease_id=lease_id)
        )

    @extend_schema(
        responses={204: None},
        description="Permanently deletes the lease, its members and its inspections.",
    )
    def delete(self, request, lease_id: int):
        lease = LeaseService.get_visible(actor=request.user, lease_id=lease_id)
        LeaseService.delete(actor=request.user, lease=lease)
        return Response(status=status.HTTP_204_NO_CONTENT)


@extend_schema(tags=["Leases"])
class LeaseTerminateView(BaseAPIView):
    @extend_schema(request=s.LeaseTerminationSerializer, responses=s.LeaseSerializer)
    def post(self, request, lease_id: int):
        lease = LeaseService.get_visible(actor=request.user, lease_id=lease_id)
        data = self.parse(s.LeaseTerminationSerializer)
        LeaseService.terminate(
            actor=request.user,
            lease=lease,
            effective_date=data["effective_date"],
            reason=data["reason"],
        )
        return self.render(
            s.LeaseSerializer, LeaseService.get_visible(actor=request.user, lease_id=lease_id)
        )


@extend_schema(tags=["Leases"])
class LeaseCancelView(BaseAPIView):
    @extend_schema(request=ActionReasonSerializer, responses=s.LeaseSerializer)
    def post(self, request, lease_id: int):
        lease = LeaseService.get_visible(actor=request.user, lease_id=lease_id)
        data = self.parse(ActionReasonSerializer)
        LeaseService.cancel(actor=request.user, lease=lease, reason=data["reason"])
        return self.render(
            s.LeaseSerializer, LeaseService.get_visible(actor=request.user, lease_id=lease_id)
        )


@extend_schema(tags=["Lease members"])
class LeaseMemberListView(BaseAPIView):
    @extend_schema(request=s.LeaseMemberInputSerializer, responses={201: s.LeaseMemberSerializer})
    def post(self, request, lease_id: int):
        lease = LeaseService.get_visible(actor=request.user, lease_id=lease_id)
        data = self.parse(s.LeaseMemberInputSerializer)
        member = LeaseMemberService.add(actor=request.user, lease=lease, member=_member_input(data))
        return self.render(s.LeaseMemberSerializer, member, status=status.HTTP_201_CREATED)


@extend_schema(tags=["Lease members"])
class LeaseMemberDetailView(BaseAPIView):
    @extend_schema(responses=s.LeaseMemberSerializer)
    def get(self, request, member_id: int):
        return self.render(
            s.LeaseMemberSerializer,
            LeaseMemberService.get_visible(actor=request.user, member_id=member_id),
        )

    @extend_schema(request=s.LeaseMemberUpdateSerializer, responses=s.LeaseMemberSerializer)
    def patch(self, request, member_id: int):
        member = LeaseMemberService.get_visible(actor=request.user, member_id=member_id)
        data = self.parse(s.LeaseMemberUpdateSerializer)
        return self.render(
            s.LeaseMemberSerializer,
            LeaseMemberService.update(actor=request.user, member=member, changes=data),
        )


@extend_schema(tags=["Lease members"])
class LeaseMemberDepartureView(BaseAPIView):
    @extend_schema(request=s.LeaseMemberDepartureSerializer, responses=s.LeaseMemberSerializer)
    def post(self, request, member_id: int):
        member = LeaseMemberService.get_visible(actor=request.user, member_id=member_id)
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
        member = LeaseMemberService.get_visible(actor=request.user, member_id=member_id)
        data = self.parse(UploadFileSerializer)
        LeaseMemberService.set_proof_of_identity(
            actor=request.user, member=member, upload=data["file"]
        )
        return self.render(s.LeaseMemberSerializer, member)


@extend_schema(tags=["Lease members"])
class LeaseMemberProofOfAddressView(BaseAPIView):
    @extend_schema(request=UploadFileSerializer, responses=s.LeaseMemberSerializer)
    def patch(self, request, member_id: int):
        member = LeaseMemberService.get_visible(actor=request.user, member_id=member_id)
        data = self.parse(UploadFileSerializer)
        LeaseMemberService.set_proof_of_address(
            actor=request.user, member=member, upload=data["file"]
        )
        return self.render(s.LeaseMemberSerializer, member)


@extend_schema(tags=["Inspections"])
class LeaseComponentStateListView(BaseAPIView):
    @extend_schema(responses=s.LeaseComponentStateSerializer(many=True))
    def get(self, request, lease_id: int):
        lease = LeaseService.get_visible(actor=request.user, lease_id=lease_id)
        return self.render_page(
            s.LeaseComponentStateSerializer,
            LeaseComponentStateService.list_for_lease(actor=request.user, lease=lease),
        )

    @extend_schema(
        request=s.LeaseComponentStateInputSerializer,
        responses={201: s.LeaseComponentStateSerializer},
    )
    def post(self, request, lease_id: int):
        lease = LeaseService.get_visible(actor=request.user, lease_id=lease_id)
        data = self.parse(s.LeaseComponentStateInputSerializer)
        component = LeaseComponentStateService.record(actor=request.user, lease=lease, **data)
        return self.render(
            s.LeaseComponentStateSerializer, component, status=status.HTTP_201_CREATED
        )


@extend_schema(tags=["Inspections"])
class LeaseComponentStateDetailView(BaseAPIView):
    """One line of an inspection, always read through its lease."""

    def _component(self, request, lease_id: int, lease_component_state_id: int):
        lease = LeaseService.get_visible(actor=request.user, lease_id=lease_id)
        return LeaseComponentStateService.get(
            actor=request.user, lease=lease, lease_component_state_id=lease_component_state_id
        )

    @extend_schema(
        request=s.LeaseComponentStateUpdateSerializer, responses=s.LeaseComponentStateSerializer
    )
    def patch(self, request, lease_id: int, lease_component_state_id: int):
        component = self._component(request, lease_id, lease_component_state_id)
        data = self.parse(s.LeaseComponentStateUpdateSerializer)
        return self.render(
            s.LeaseComponentStateSerializer,
            LeaseComponentStateService.update(
                actor=request.user, component=component, changes=data
            ),
        )

    @extend_schema(responses={204: None}, description="Deletes a line recorded by mistake.")
    def delete(self, request, lease_id: int, lease_component_state_id: int):
        component = self._component(request, lease_id, lease_component_state_id)
        LeaseComponentStateService.delete(actor=request.user, component=component)
        return Response(status=status.HTTP_204_NO_CONTENT)


@extend_schema(tags=["Inspections"])
class LeaseComponentStateFilesView(BaseAPIView):
    @extend_schema(request=UploadFilesSerializer, responses={201: s.LeaseComponentStateSerializer})
    def post(self, request, lease_id: int, lease_component_state_id: int):
        lease = LeaseService.get_visible(actor=request.user, lease_id=lease_id)
        component = LeaseComponentStateService.get(
            actor=request.user, lease=lease, lease_component_state_id=lease_component_state_id
        )
        data = self.parse(UploadFilesSerializer)
        LeaseComponentStateService.add_files(
            actor=request.user, component=component, files=data["files"]
        )
        return Response(
            s.LeaseComponentStateSerializer(component, context=self.get_serializer_context()).data,
            status=status.HTTP_201_CREATED,
        )
