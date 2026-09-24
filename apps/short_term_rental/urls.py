from django.urls import path

from apps.short_term_rental import views

urlpatterns = [
    path(
        "short-term-rentals/",
        views.ShortTermRentalListView.as_view(),
        name="short-term-rental-list",
    ),
    path(
        "short-term-rentals/<int:short_term_rental_id>/",
        views.ShortTermRentalDetailView.as_view(),
        name="short-term-rental-detail",
    ),
    path(
        "short-term-rentals/<int:short_term_rental_id>/reschedule/",
        views.RescheduleView.as_view(),
        name="short-term-rental-reschedule",
    ),
    path(
        "short-term-rentals/<int:short_term_rental_id>/check-in/",
        views.CheckInView.as_view(),
        name="short-term-rental-check-in",
    ),
    path(
        "short-term-rentals/<int:short_term_rental_id>/complete/",
        views.CompleteView.as_view(),
        name="short-term-rental-complete",
    ),
    path(
        "short-term-rentals/<int:short_term_rental_id>/cancel/",
        views.CancelView.as_view(),
        name="short-term-rental-cancel",
    ),
    path(
        "short-term-rentals/<int:short_term_rental_id>/members/",
        views.MemberListView.as_view(),
        name="short-term-rental-members",
    ),
    path(
        "short-term-rental-members/<int:short_term_rental_member_id>/",
        views.MemberDetailView.as_view(),
        name="short-term-rental-member-detail",
    ),
    path(
        "short-term-rental-members/<int:short_term_rental_member_id>/id-card/",
        views.MemberIdCardView.as_view(),
        name="short-term-rental-member-id-card",
    ),
]
