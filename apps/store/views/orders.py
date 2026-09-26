"""Store orders and their lifecycle."""

from drf_spectacular.utils import extend_schema
from rest_framework import status
from rest_framework.response import Response

from apps.common.serializers import (
    ActionNoteSerializer,
    ActionReasonSerializer,
)
from apps.common.views import BaseAPIView
from apps.properties.services import UnitService
from apps.store import serializers as s
from apps.store.services import OrderLine, OrderService


@extend_schema(tags=["Store"])
class OrderListView(BaseAPIView):
    @extend_schema(
        parameters=[s.OrdersQueryParamsSerializer],
        responses=s.OrderSerializer(many=True),
    )
    def get(self, request):
        query = self.parse_query_params(s.OrdersQueryParamsSerializer)
        return self.render_page(
            s.OrderSerializer,
            OrderService.list_visible(
                actor=request.user, property_id=self.property.pk, **query
            ),
        )

    @extend_schema(request=s.OrderCreateSerializer, responses={201: s.OrderSerializer})
    def post(self, request):
        data = self.parse(s.OrderCreateSerializer)
        unit = (
            UnitService.get_visible(
                actor=request.user, prop=self.property, unit_id=data["unit_id"]
            )
            if data["unit_id"]
            else None
        )
        order = OrderService.place(
            actor=request.user,
            prop=self.property,
            unit=unit,
            lines=[OrderLine(**line) for line in data["items"]],
            delivery_instructions=data["delivery_instructions"],
            customer_note=data["customer_note"],
        )
        return self.render(
            s.OrderSerializer,
            OrderService.get_visible(
                actor=request.user, prop=self.property, order_id=order.pk
            ),
            status=status.HTTP_201_CREATED,
        )


@extend_schema(tags=["Store"])
class OrderDetailView(BaseAPIView):
    @extend_schema(responses=s.OrderSerializer)
    def get(self, request, order_id: int):
        return self.render(
            s.OrderSerializer,
            OrderService.get_visible(
                actor=request.user, prop=self.property, order_id=order_id
            ),
        )

    @extend_schema(
        responses={204: None},
        description="Permanently deletes the order; reserved stock is restored.",
    )
    def delete(self, request, order_id: int):
        order = OrderService.get_visible(
            actor=request.user, prop=self.property, order_id=order_id
        )
        OrderService.delete(actor=request.user, order=order)
        return Response(status=status.HTTP_204_NO_CONTENT)


class _OrderTransitionView(BaseAPIView):
    transition: str = ""

    @extend_schema(
        tags=["Store"], request=ActionNoteSerializer, responses=s.OrderSerializer
    )
    def post(self, request, order_id: int):
        order = OrderService.get_visible(
            actor=request.user, prop=self.property, order_id=order_id
        )
        data = self.parse(ActionNoteSerializer)
        getattr(OrderService, self.transition)(
            actor=request.user, order=order, note=data["note"]
        )
        return self.render(
            s.OrderSerializer,
            OrderService.get_visible(
                actor=request.user, prop=self.property, order_id=order_id
            ),
        )


class OrderConfirmView(_OrderTransitionView):
    transition = "confirm"


class OrderDeliverView(_OrderTransitionView):
    transition = "deliver"


@extend_schema(tags=["Store"])
class OrderCancelView(BaseAPIView):
    @extend_schema(request=ActionReasonSerializer, responses=s.OrderSerializer)
    def post(self, request, order_id: int):
        order = OrderService.get_visible(
            actor=request.user, prop=self.property, order_id=order_id
        )
        data = self.parse(ActionReasonSerializer)
        OrderService.cancel(actor=request.user, order=order, reason=data["reason"])
        return self.render(
            s.OrderSerializer,
            OrderService.get_visible(
                actor=request.user, prop=self.property, order_id=order_id
            ),
        )
