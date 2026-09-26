from drf_spectacular.utils import extend_schema
from rest_framework import status
from rest_framework.response import Response
from rest_framework.views import APIView

from apps.common.serializers import UploadFileSerializer
from apps.common.views import ApiMixin, BaseAPIView
from apps.properties import serializers as s
from apps.properties.services import (
    PromoterService,
    PropertyService,
    SyndicatService,
)


@extend_schema(tags=["Properties"])
class PropertyListView(ApiMixin, APIView):
    @extend_schema(responses=s.PropertySerializer(many=True))
    def get(self, request):
        return self.render_page(
            s.PropertySerializer, PropertyService.list_visible(actor=request.user)
        )

    @extend_schema(
        request=s.PropertyInputSerializer, responses={201: s.PropertySerializer}
    )
    def post(self, request):
        data = dict(self.parse(s.PropertyInputSerializer))
        syndicat = SyndicatService.get_visible(
            actor=request.user, syndicat_id=data.pop("syndicat_id")
        )
        promoter = PromoterService.get(promoter_id=data.pop("promoter_id"))
        features = data.pop("features", None)
        prop = PropertyService.create(
            actor=request.user,
            syndicat=syndicat,
            promoter=promoter,
            data=data,
            features=features,
        )
        return self.render(s.PropertySerializer, prop, status=status.HTTP_201_CREATED)


@extend_schema(tags=["Properties"])
class PropertyDetailView(BaseAPIView):
    @extend_schema(responses=s.PropertySerializer)
    def get(self, request, property_id: int):
        return self.render(
            s.PropertySerializer,
            self.selected_property(property_id),
        )

    @extend_schema(request=s.PropertyUpdateSerializer, responses=s.PropertySerializer)
    def patch(self, request, property_id: int):
        prop = self.selected_property(property_id)
        data = self.parse(s.PropertyUpdateSerializer)
        return self.render(
            s.PropertySerializer,
            PropertyService.update(actor=request.user, prop=prop, changes=data),
        )

    @extend_schema(
        responses={204: None},
        description="Deletes an empty property (409 while it still holds content).",
    )
    def delete(self, request, property_id: int):
        prop = self.selected_property(property_id)
        PropertyService.delete(actor=request.user, prop=prop)
        return Response(status=status.HTTP_204_NO_CONTENT)


@extend_schema(tags=["Properties"])
class PropertyFeaturesView(BaseAPIView):
    @extend_schema(request=s.PropertyFeaturesSerializer, responses=s.PropertySerializer)
    def patch(self, request, property_id: int):
        prop = self.selected_property(property_id)
        data = self.parse(s.PropertyFeaturesSerializer)
        return self.render(
            s.PropertySerializer,
            PropertyService.set_features(actor=request.user, prop=prop, features=data),
        )


@extend_schema(tags=["Properties"])
class PropertyPromoterView(BaseAPIView):
    @extend_schema(request=s.PromoterChangeSerializer, responses=s.PropertySerializer)
    def post(self, request, property_id: int):
        prop = self.selected_property(property_id)
        data = self.parse(s.PromoterChangeSerializer)
        promoter = PromoterService.get_visible(
            actor=request.user, promoter_id=data["promoter_id"]
        )
        prop = PropertyService.change_promoter(
            actor=request.user,
            prop=prop,
            promoter=promoter,
            effective_date=data["effective_date"],
        )
        return self.render(s.PropertySerializer, prop)


@extend_schema(tags=["Properties"])
class PropertyLogoView(BaseAPIView):
    @extend_schema(request=UploadFileSerializer, responses=s.PropertySerializer)
    def patch(self, request, property_id: int):
        prop = self.selected_property(property_id)
        data = self.parse(UploadFileSerializer)
        PropertyService.set_logo(actor=request.user, prop=prop, upload=data["file"])
        return self.render(s.PropertySerializer, prop)
