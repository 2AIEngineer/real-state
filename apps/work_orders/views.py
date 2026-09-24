from drf_spectacular.utils import extend_schema
from rest_framework import status
from rest_framework.response import Response

from apps.accounts.services.accounts import AccountService
from apps.common.serializers import UploadFilesSerializer
from apps.common.views import BaseAPIView
from apps.properties.services import BuildingService, UnitService
from apps.service_requests.services import ServiceRequestService
from apps.work_orders import serializers as s
from apps.work_orders.services import WorkOrderService


def _assignee(user_id):
    if user_id is None:
        return None
    return AccountService.resolve(user_id=user_id, field="assignee_id")


@extend_schema(tags=["Work orders"])
class WorkOrderListView(BaseAPIView):
    @extend_schema(
        parameters=[s.WorkOrdersQueryParamsSerializer], responses=s.WorkOrderSerializer(many=True)
    )
    def get(self, request):
        query = self.parse_query_params(s.WorkOrdersQueryParamsSerializer)
        return self.render_page(
            s.WorkOrderSerializer,
            WorkOrderService.list_visible(
                actor=request.user, property_id=self.property.pk, **query
            ),
        )

    @extend_schema(request=s.WorkOrderCreateSerializer, responses={201: s.WorkOrderSerializer})
    def post(self, request):
        data = dict(self.parse(s.WorkOrderCreateSerializer))
        actor = request.user
        prop = self.property
        building_id, unit_id, sr_id = (
            data.pop("building_id"),
            data.pop("unit_id"),
            data.pop("service_request_id"),
        )
        wo = WorkOrderService.create(
            actor=actor,
            prop=prop,
            title=data.pop("title"),
            building=BuildingService.get_visible(
                actor=actor, prop=self.property, building_id=building_id
            )
            if building_id
            else None,
            unit=UnitService.get_visible(actor=actor, prop=self.property, unit_id=unit_id)
            if unit_id
            else None,
            service_request=ServiceRequestService.get_visible(
                actor=actor, prop=self.property, request_id=sr_id
            )
            if sr_id
            else None,
            assignee=_assignee(data.pop("assignee_id")),
            files=data.pop("files"),
            data=data,
        )
        return self.render(s.WorkOrderSerializer, wo, status=status.HTTP_201_CREATED)


@extend_schema(tags=["Work orders"])
class WorkOrderDetailView(BaseAPIView):
    @extend_schema(responses=s.WorkOrderSerializer)
    def get(self, request, work_order_id: int):
        return self.render(
            s.WorkOrderSerializer,
            WorkOrderService.get_visible(
                actor=request.user, prop=self.property, work_order_id=work_order_id
            ),
        )

    @extend_schema(request=s.WorkOrderUpdateSerializer, responses=s.WorkOrderSerializer)
    def patch(self, request, work_order_id: int):
        wo = WorkOrderService.get_visible(
            actor=request.user, prop=self.property, work_order_id=work_order_id
        )
        data = dict(self.parse(s.WorkOrderUpdateSerializer))
        if "assignee_id" in data:
            data["assignee"] = _assignee(data.pop("assignee_id"))
        return self.render(
            s.WorkOrderSerializer, WorkOrderService.update(actor=request.user, wo=wo, changes=data)
        )

    @extend_schema(
        responses={204: None}, description="Permanently deletes the work order and its files."
    )
    def delete(self, request, work_order_id: int):
        wo = WorkOrderService.get_visible(
            actor=request.user, prop=self.property, work_order_id=work_order_id
        )
        WorkOrderService.delete(actor=request.user, wo=wo)
        return Response(status=status.HTTP_204_NO_CONTENT)


@extend_schema(tags=["Work orders"])
class WorkOrderTransitionView(BaseAPIView):
    @extend_schema(request=s.WorkOrderTransitionSerializer, responses=s.WorkOrderSerializer)
    def post(self, request, work_order_id: int):
        wo = WorkOrderService.get_visible(
            actor=request.user, prop=self.property, work_order_id=work_order_id
        )
        data = self.parse(s.WorkOrderTransitionSerializer)
        return self.render(
            s.WorkOrderSerializer, WorkOrderService.transition(actor=request.user, wo=wo, **data)
        )


@extend_schema(tags=["Work orders"])
class WorkOrderFilesView(BaseAPIView):
    @extend_schema(request=UploadFilesSerializer, responses={201: s.WorkOrderSerializer})
    def post(self, request, work_order_id: int):
        wo = WorkOrderService.get_visible(
            actor=request.user, prop=self.property, work_order_id=work_order_id
        )
        data = self.parse(UploadFilesSerializer)
        WorkOrderService.add_files(actor=request.user, wo=wo, files=data["files"])
        return self.render(s.WorkOrderSerializer, wo, status=status.HTTP_201_CREATED)
