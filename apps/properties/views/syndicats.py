from drf_spectacular.utils import extend_schema
from rest_framework import status
from rest_framework.response import Response
from rest_framework.views import APIView

from apps.common.serializers import UploadFileSerializer
from apps.common.views import ApiMixin
from apps.properties import serializers as s
from apps.properties.services import (
    SyndicatService,
)


@extend_schema(tags=["Syndicats"])
class SyndicatListView(ApiMixin, APIView):
    @extend_schema(responses=s.SyndicatSerializer(many=True))
    def get(self, request):
        return self.render_page(
            s.SyndicatSerializer, SyndicatService.list_visible(actor=request.user)
        )

    @extend_schema(request=s.SyndicatInputSerializer, responses={201: s.SyndicatSerializer})
    def post(self, request):
        data = self.parse(s.SyndicatInputSerializer)
        return self.render(
            s.SyndicatSerializer,
            SyndicatService.create(actor=request.user, data=data),
            status=status.HTTP_201_CREATED,
        )


@extend_schema(tags=["Syndicats"])
class SyndicatDetailView(ApiMixin, APIView):
    @extend_schema(responses=s.SyndicatSerializer)
    def get(self, request, syndicat_id: int):
        return self.render(
            s.SyndicatSerializer,
            SyndicatService.get_visible(actor=request.user, syndicat_id=syndicat_id),
        )

    @extend_schema(request=s.SyndicatUpdateSerializer, responses=s.SyndicatSerializer)
    def patch(self, request, syndicat_id: int):
        syndicat = SyndicatService.get_visible(actor=request.user, syndicat_id=syndicat_id)
        data = self.parse(s.SyndicatUpdateSerializer)
        return self.render(
            s.SyndicatSerializer,
            SyndicatService.update(actor=request.user, syndicat=syndicat, changes=data),
        )

    @extend_schema(
        responses={204: None},
        description="Deletes an empty syndicat (409 while it still holds properties).",
    )
    def delete(self, request, syndicat_id: int):
        syndicat = SyndicatService.get_visible(actor=request.user, syndicat_id=syndicat_id)
        SyndicatService.delete(actor=request.user, syndicat=syndicat)
        return Response(status=status.HTTP_204_NO_CONTENT)


@extend_schema(tags=["Syndicats"])
class SyndicatLogoView(ApiMixin, APIView):
    @extend_schema(request=UploadFileSerializer, responses=s.SyndicatSerializer)
    def patch(self, request, syndicat_id: int):
        syndicat = SyndicatService.get_visible(actor=request.user, syndicat_id=syndicat_id)
        data = self.parse(UploadFileSerializer)
        SyndicatService.set_logo(actor=request.user, syndicat=syndicat, upload=data["file"])
        return self.render(s.SyndicatSerializer, syndicat)
