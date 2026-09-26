from django.urls import path

from apps.visitors import views

urlpatterns = [
    path("visitors/", views.VisitorListView.as_view(), name="visitor-list"),
    path(
        "visitors/<int:visitor_id>/",
        views.VisitorDetailView.as_view(),
        name="visitor-detail",
    ),
    path(
        "visitors/<int:visitor_id>/departure/",
        views.VisitorDepartureView.as_view(),
        name="visitor-departure",
    ),
    path(
        "visitors/<int:visitor_id>/id-card/",
        views.VisitorIdCardView.as_view(),
        name="visitor-id-card",
    ),
]
