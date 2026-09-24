"""Inspections: the state of each component at check-in and check-out."""

from drf_spectacular.utils import extend_schema
from rest_framework import status
from rest_framework.response import Response

from apps.common.serializers import (
    UploadFilesSerializer,
)
from apps.common.views import BaseAPIView
from apps.leasing import serializers as s
from apps.leasing.services import (
    LeaseComponentStateService,
    LeaseService,
)


@extend_schema(tags=["Inspections"])
class LeaseComponentStateListView(BaseAPIView):
    @extend_schema(responses=s.LeaseComponentStateSerializer(many=True))
    def get(self, request, lease_id: int):
        lease = LeaseService.get_visible(actor=request.user, prop=self.property, lease_id=lease_id)
        return self.render_page(
            s.LeaseComponentStateSerializer,
            LeaseComponentStateService.list_for_lease(actor=request.user, lease=lease),
        )

    @extend_schema(
        request=s.LeaseComponentStateInputSerializer,
        responses={201: s.LeaseComponentStateSerializer},
    )
    def post(self, request, lease_id: int):
        lease = LeaseService.get_visible(actor=request.user, prop=self.property, lease_id=lease_id)
        data = self.parse(s.LeaseComponentStateInputSerializer)
        component = LeaseComponentStateService.record(actor=request.user, lease=lease, **data)
        return self.render(
            s.LeaseComponentStateSerializer, component, status=status.HTTP_201_CREATED
        )


@extend_schema(tags=["Inspections"])
class LeaseComponentStateDetailView(BaseAPIView):
    """One line of an inspection, always read through its lease."""

    def _component(self, request, lease_id: int, lease_component_state_id: int):
        lease = LeaseService.get_visible(actor=request.user, prop=self.property, lease_id=lease_id)
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
        lease = LeaseService.get_visible(actor=request.user, prop=self.property, lease_id=lease_id)
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
