from django.urls import path

from apps.marketplace import views

urlpatterns = [
    path("marketplace/listings/", views.ListingListView.as_view(), name="listing-list"),
    path(
        "marketplace/listings/<int:listing_id>/",
        views.ListingDetailView.as_view(),
        name="listing-detail",
    ),
    path(
        "marketplace/listings/<int:listing_id>/sold/",
        views.ListingSoldView.as_view(),
        name="listing-sold",
    ),
    path(
        "marketplace/listings/<int:listing_id>/archive/",
        views.ListingArchiveView.as_view(),
        name="listing-archive",
    ),
    path(
        "marketplace/listings/<int:listing_id>/moderation/",
        views.ListingModerationView.as_view(),
        name="listing-moderation",
    ),
    path(
        "marketplace/listings/<int:listing_id>/images/",
        views.ListingImagesView.as_view(),
        name="listing-images",
    ),
    path(
        "marketplace/listings/<int:listing_id>/images/<int:attachment_id>/",
        views.ListingImageDetailView.as_view(),
        name="listing-image-detail",
    ),
]
