"""The store catalogue."""

from drf_spectacular.utils import extend_schema
from rest_framework import status
from rest_framework.response import Response

from apps.common.serializers import (
    UploadFilesSerializer,
)
from apps.common.views import BaseAPIView
from apps.store import serializers as s
from apps.store.services import ProductService


@extend_schema(tags=["Store"])
class ProductListView(BaseAPIView):
    @extend_schema(
        parameters=[s.ProductsQueryParamsSerializer], responses=s.ProductSerializer(many=True)
    )
    def get(self, request):
        query = self.parse_query_params(s.ProductsQueryParamsSerializer)
        qs = ProductService.list_visible(
            actor=request.user,
            prop=self.property,
            include_inactive=query["include_inactive"],
            search=query.get("search"),
        )
        return self.render_page(s.ProductSerializer, qs)

    @extend_schema(request=s.ProductCreateSerializer, responses={201: s.ProductSerializer})
    def post(self, request):
        data = dict(self.parse(s.ProductCreateSerializer))
        return self.render(
            s.ProductSerializer,
            ProductService.create(actor=request.user, prop=self.property, data=data),
            status=status.HTTP_201_CREATED,
        )


@extend_schema(tags=["Store"])
class ProductDetailView(BaseAPIView):
    @extend_schema(responses=s.ProductSerializer)
    def get(self, request, product_id: int):
        return self.render(
            s.ProductSerializer,
            ProductService.get_visible(
                actor=request.user, prop=self.property, product_id=product_id
            ),
        )

    @extend_schema(request=s.ProductUpdateSerializer, responses=s.ProductSerializer)
    def patch(self, request, product_id: int):
        product = ProductService.get_visible(
            actor=request.user, prop=self.property, product_id=product_id
        )
        data = self.parse(s.ProductUpdateSerializer)
        return self.render(
            s.ProductSerializer,
            ProductService.update(actor=request.user, product=product, changes=data),
        )

    @extend_schema(responses={204: None}, description="Deletes a product that was never ordered.")
    def delete(self, request, product_id: int):
        product = ProductService.get_visible(
            actor=request.user, prop=self.property, product_id=product_id
        )
        ProductService.delete(actor=request.user, product=product)
        return Response(status=status.HTTP_204_NO_CONTENT)


@extend_schema(tags=["Store"])
class ProductImagesView(BaseAPIView):
    @extend_schema(request=UploadFilesSerializer, responses={201: s.ProductSerializer})
    def post(self, request, product_id: int):
        product = ProductService.get_visible(
            actor=request.user, prop=self.property, product_id=product_id
        )
        data = self.parse(UploadFilesSerializer)
        ProductService.add_images(actor=request.user, product=product, files=data["files"])
        return self.render(s.ProductSerializer, product, status=status.HTTP_201_CREATED)


@extend_schema(tags=["Store"])
class ProductImageDetailView(BaseAPIView):
    @extend_schema(responses={204: None})
    def delete(self, request, product_id: int, attachment_id: int):
        product = ProductService.get_visible(
            actor=request.user, prop=self.property, product_id=product_id
        )
        ProductService.remove_image(
            actor=request.user, product=product, attachment_id=attachment_id
        )
        return Response(status=status.HTTP_204_NO_CONTENT)
