from django.urls import path

from apps.service_requests import views

urlpatterns = [
    path(
        "service-requests/",
        views.ServiceRequestListView.as_view(),
        name="service-request-list",
    ),
    path(
        "service-requests/<int:request_id>/",
        views.ServiceRequestDetailView.as_view(),
        name="service-request-detail",
    ),
    path(
        "service-requests/<int:request_id>/files/",
        views.ServiceRequestFilesView.as_view(),
        name="service-request-files",
    ),
    path(
        "service-requests/<int:request_id>/files/<int:attachment_id>/",
        views.ServiceRequestFileDetailView.as_view(),
        name="service-request-file-detail",
    ),
    path(
        "service-requests/<int:request_id>/assignments/",
        views.AssignmentListView.as_view(),
        name="service-request-assignments",
    ),
    path(
        "service-requests/<int:request_id>/resolve/",
        views.ResolveView.as_view(),
        name="service-request-resolve",
    ),
    path(
        "service-requests/<int:request_id>/feedback/",
        views.FeedbackView.as_view(),
        name="service-request-feedback",
    ),
    path(
        "service-requests/<int:request_id>/close/",
        views.CloseView.as_view(),
        name="service-request-close",
    ),
    path(
        "service-requests/<int:request_id>/cancel/",
        views.CancelView.as_view(),
        name="service-request-cancel",
    ),
]
