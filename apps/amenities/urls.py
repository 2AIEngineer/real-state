from django.urls import path

from apps.amenities import views

urlpatterns = [
    path("amenities/", views.AmenityListView.as_view(), name="amenity-list"),
    path("amenities/<int:amenity_id>/", views.AmenityDetailView.as_view(), name="amenity-detail"),
    path(
        "amenities/<int:amenity_id>/schedule/",
        views.AmenityScheduleView.as_view(),
        name="amenity-schedule",
    ),
    path(
        "amenities/<int:amenity_id>/images/",
        views.AmenityImagesView.as_view(),
        name="amenity-images",
    ),
    path(
        "amenities/<int:amenity_id>/images/<int:attachment_id>/",
        views.AmenityImageDetailView.as_view(),
        name="amenity-image-detail",
    ),
    path("bookings/", views.BookingListView.as_view(), name="booking-list"),
    path(
        "bookings/complete-past/",
        views.BookingCompletePastView.as_view(),
        name="booking-complete-past",
    ),
    path("bookings/<int:booking_id>/", views.BookingDetailView.as_view(), name="booking-detail"),
    path(
        "bookings/<int:booking_id>/decision/",
        views.BookingDecisionView.as_view(),
        name="booking-decision",
    ),
    path(
        "bookings/<int:booking_id>/cancel/",
        views.BookingCancelView.as_view(),
        name="booking-cancel",
    ),
]
