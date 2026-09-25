"""Leases: listing, creating, editing, terminating, cancelling."""

from drf_spectacular.utils import extend_schema
from rest_framework import status
from rest_framework.response import Response

from apps.common.serializers import (
    ActionReasonSerializer,
    BulkActionResultSerializer,
)
from apps.common.views import BaseAPIView
from apps.leasing import serializers as s
from apps.leasing.services import (
    LeaseService,
)
from apps.leasing.views.members import member_input
from apps.properties.services import UnitService


@extend_schema(tags=["Leases"])
class LeaseListView(BaseAPIView):
    @extend_schema(
        parameters=[s.LeasesQueryParamsSerializer], responses=s.LeaseSerializer(many=True)
    )
    def get(self, request):
        query = self.parse_query_params(s.LeasesQueryParamsSerializer)
        return self.render_page(
            s.LeaseSerializer,
            LeaseService.list_visible(actor=request.user, property_id=self.property.pk, **query),
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
            members=[member_input(m) for m in data["members"]],
        )
        return self.render(
            s.LeaseSerializer,
            LeaseService.get_visible(actor=request.user, prop=self.property, lease_id=lease.pk),
            status=status.HTTP_201_CREATED,
        )


@extend_schema(tags=["Leases"])
class LeaseDetailView(BaseAPIView):
    @extend_schema(responses=s.LeaseSerializer)
    def get(self, request, lease_id: int):
        return self.render(
            s.LeaseSerializer,
            LeaseService.get_visible(actor=request.user, prop=self.property, lease_id=lease_id),
        )

    @extend_schema(request=s.LeaseUpdateSerializer, responses=s.LeaseSerializer)
    def patch(self, request, lease_id: int):
        lease = LeaseService.get_visible(actor=request.user, prop=self.property, lease_id=lease_id)
        data = self.parse(s.LeaseUpdateSerializer)
        LeaseService.update(actor=request.user, lease=lease, changes=data)
        return self.render(
            s.LeaseSerializer,
            LeaseService.get_visible(actor=request.user, prop=self.property, lease_id=lease_id),
        )

    @extend_schema(
        responses={204: None},
        description="Permanently deletes the lease, its members and its inspections.",
    )
    def delete(self, request, lease_id: int):
        lease = LeaseService.get_visible(actor=request.user, prop=self.property, lease_id=lease_id)
        LeaseService.delete(actor=request.user, lease=lease)
        return Response(status=status.HTTP_204_NO_CONTENT)


@extend_schema(tags=["Leases"])
class LeaseTerminateView(BaseAPIView):
    @extend_schema(request=s.LeaseTerminationSerializer, responses=s.LeaseSerializer)
    def post(self, request, lease_id: int):
        lease = LeaseService.get_visible(actor=request.user, prop=self.property, lease_id=lease_id)
        data = self.parse(s.LeaseTerminationSerializer)
        LeaseService.terminate(
            actor=request.user,
            lease=lease,
            effective_date=data["effective_date"],
            reason=data["reason"],
        )
        return self.render(
            s.LeaseSerializer,
            LeaseService.get_visible(actor=request.user, prop=self.property, lease_id=lease_id),
        )


@extend_schema(tags=["Leases"])
class LeaseCancelView(BaseAPIView):
    @extend_schema(request=ActionReasonSerializer, responses=s.LeaseSerializer)
    def post(self, request, lease_id: int):
        lease = LeaseService.get_visible(actor=request.user, prop=self.property, lease_id=lease_id)
        data = self.parse(ActionReasonSerializer)
        LeaseService.cancel(actor=request.user, lease=lease, reason=data["reason"])
        return self.render(
            s.LeaseSerializer,
            LeaseService.get_visible(actor=request.user, prop=self.property, lease_id=lease_id),
        )


@extend_schema(tags=["Leases"])
class LeaseExpireDueView(BaseAPIView):
    @extend_schema(
        request=None,
        responses=BulkActionResultSerializer,
        description="Bulk action (admin, syndic, manager): terminates at term every active lease of the selected property whose end date has passed.",
    )
    def post(self, request):
        count = LeaseService.expire_due_in(actor=request.user, prop=self.property)
        return self.render(BulkActionResultSerializer, {"count": count})
