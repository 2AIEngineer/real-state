from drf_spectacular.utils import extend_schema
from rest_framework import status
from rest_framework.response import Response

from apps.common.views import BaseAPIView
from apps.marketplace import serializers as s
from apps.marketplace.services import ListingService
from apps.properties.services import PropertyService


@extend_schema(tags=["Marketplace"])
class ListingListView(BaseAPIView):
    @extend_schema(
        parameters=[s.MarketplaceListingsQueryParamsSerializer],
        responses=s.MarketplaceListingSerializer(many=True),
    )
    def get(self, request):
        query = dict(self.parse_query_params(s.MarketplaceListingsQueryParamsSerializer))
        if query.pop("mine"):
            qs = ListingService.list_mine(actor=request.user, status=query.get("status"))
        else:
            query.pop("status", None)
            qs = ListingService.list_published(
                actor=request.user, property_id=self.selected_property_id, **query
            )
        return self.render_page(s.MarketplaceListingSerializer, qs)

    @extend_schema(
        request=s.MarketplaceListingCreateSerializer,
        responses={201: s.MarketplaceListingSerializer},
    )
    def post(self, request):
        data = dict(self.parse(s.MarketplaceListingCreateSerializer))
        prop = PropertyService.get_visible(
            actor=request.user,
            property_id=self.selected_property_id,
            syndicat_id=self.selected_syndicat_id,
        )
        images = data.pop("images")
        listing = ListingService.publish(actor=request.user, data=data, images=images, prop=prop)
        return self.render(s.MarketplaceListingSerializer, listing, status=status.HTTP_201_CREATED)


@extend_schema(tags=["Marketplace"])
class ListingDetailView(BaseAPIView):
    @extend_schema(responses=s.MarketplaceListingSerializer)
    def get(self, request, listing_id: int):
        return self.render(
            s.MarketplaceListingSerializer,
            ListingService.get_visible(actor=request.user, listing_id=listing_id),
        )

    @extend_schema(
        request=s.MarketplaceListingUpdateSerializer, responses=s.MarketplaceListingSerializer
    )
    def patch(self, request, listing_id: int):
        listing = ListingService.get_visible(actor=request.user, listing_id=listing_id)
        data = self.parse(s.MarketplaceListingUpdateSerializer)
        return self.render(
            s.MarketplaceListingSerializer,
            ListingService.update(actor=request.user, listing=listing, changes=data),
        )

    @extend_schema(responses={204: None}, description="Deletes the listing (seller or moderator).")
    def delete(self, request, listing_id: int):
        listing = ListingService.get_visible(actor=request.user, listing_id=listing_id)
        ListingService.delete(actor=request.user, listing=listing)
        return Response(status=status.HTTP_204_NO_CONTENT)


@extend_schema(tags=["Marketplace"])
class ListingSoldView(BaseAPIView):
    """The item was sold: the ad leaves the catalogue."""

    @extend_schema(request=None, responses=s.MarketplaceListingSerializer)
    def post(self, request, listing_id: int):
        listing = ListingService.get_visible(actor=request.user, listing_id=listing_id)
        return self.render(
            s.MarketplaceListingSerializer,
            ListingService.mark_sold(actor=request.user, listing=listing),
        )


@extend_schema(tags=["Marketplace"])
class ListingArchiveView(BaseAPIView):
    """The seller puts the ad away; the record stays (delete erases it)."""

    @extend_schema(request=None, responses=s.MarketplaceListingSerializer)
    def post(self, request, listing_id: int):
        listing = ListingService.get_visible(actor=request.user, listing_id=listing_id)
        return self.render(
            s.MarketplaceListingSerializer,
            ListingService.archive(actor=request.user, listing=listing),
        )


@extend_schema(tags=["Marketplace"])
class ListingModerationView(BaseAPIView):
    @extend_schema(
        request=s.MarketplaceListingModerationSerializer, responses=s.MarketplaceListingSerializer
    )
    def post(self, request, listing_id: int):
        listing = ListingService.get_visible(actor=request.user, listing_id=listing_id)
        data = self.parse(s.MarketplaceListingModerationSerializer)
        return self.render(
            s.MarketplaceListingSerializer,
            ListingService.moderate(actor=request.user, listing=listing, reason=data["reason"]),
        )


@extend_schema(tags=["Marketplace"])
class ListingImagesView(BaseAPIView):
    @extend_schema(
        request=s.MarketplaceListingImagesSerializer,
        responses={201: s.MarketplaceListingSerializer},
    )
    def post(self, request, listing_id: int):
        listing = ListingService.get_visible(actor=request.user, listing_id=listing_id)
        data = self.parse(s.MarketplaceListingImagesSerializer)
        ListingService.add_images(actor=request.user, listing=listing, images=data["images"])
        return self.render(s.MarketplaceListingSerializer, listing, status=status.HTTP_201_CREATED)


@extend_schema(tags=["Marketplace"])
class ListingImageDetailView(BaseAPIView):
    @extend_schema(responses={204: None})
    def delete(self, request, listing_id: int, attachment_id: int):
        listing = ListingService.get_visible(actor=request.user, listing_id=listing_id)
        ListingService.remove_image(
            actor=request.user, listing=listing, attachment_id=attachment_id
        )
        return Response(status=status.HTTP_204_NO_CONTENT)
