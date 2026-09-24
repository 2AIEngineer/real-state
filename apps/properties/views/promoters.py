from drf_spectacular.utils import extend_schema
from rest_framework import status
from rest_framework.response import Response
from rest_framework.views import APIView

from apps.common.views import ApiMixin
from apps.properties import serializers as s
from apps.properties.services import (
    PromoterService,
)


@extend_schema(tags=["Promoters"])
class PromoterListView(ApiMixin, APIView):
    @extend_schema(responses=s.PromoterSerializer(many=True))
    def get(self, request):
        return self.render_page(
            s.PromoterSerializer, PromoterService.list_visible(actor=request.user)
        )

    @extend_schema(request=s.PromoterInputSerializer, responses={201: s.PromoterSerializer})
    def post(self, request):
        data = dict(self.parse(s.PromoterInputSerializer))
        promoter = PromoterService.create(
            actor=request.user, representative_email=data.pop("representative_email"), data=data
        )
        return self.render(s.PromoterSerializer, promoter, status=status.HTTP_201_CREATED)


@extend_schema(tags=["Promoters"])
class PromoterDetailView(ApiMixin, APIView):
    @extend_schema(responses=s.PromoterSerializer)
    def get(self, request, promoter_id: int):
        return self.render(
            s.PromoterSerializer,
            PromoterService.get_visible(actor=request.user, promoter_id=promoter_id),
        )

    @extend_schema(request=s.PromoterUpdateSerializer, responses=s.PromoterSerializer)
    def patch(self, request, promoter_id: int):
        promoter = PromoterService.get_visible(actor=request.user, promoter_id=promoter_id)
        data = self.parse(s.PromoterUpdateSerializer)
        return self.render(
            s.PromoterSerializer,
            PromoterService.update(actor=request.user, promoter=promoter, changes=data),
        )

    @extend_schema(
        responses={204: None}, description="Deletes a promoter that develops no property."
    )
    def delete(self, request, promoter_id: int):
        promoter = PromoterService.get_visible(actor=request.user, promoter_id=promoter_id)
        PromoterService.delete(actor=request.user, promoter=promoter)
        return Response(status=status.HTTP_204_NO_CONTENT)
