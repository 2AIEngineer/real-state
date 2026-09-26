from django.urls import path

from apps.events import views

urlpatterns = [
    path("events/", views.EventListView.as_view(), name="event-list"),
    path(
        "events/complete-past/",
        views.EventCompletePastView.as_view(),
        name="event-complete-past",
    ),
    path("events/<int:event_id>/", views.EventDetailView.as_view(), name="event-detail"),
    path(
        "events/<int:event_id>/cancel/",
        views.EventCancelView.as_view(),
        name="event-cancel",
    ),
    path(
        "events/<int:event_id>/archive/",
        views.EventArchiveView.as_view(),
        name="event-archive",
    ),
    path(
        "events/<int:event_id>/files/",
        views.EventFilesView.as_view(),
        name="event-files",
    ),
    path(
        "events/<int:event_id>/files/<int:attachment_id>/",
        views.EventFileDetailView.as_view(),
        name="event-file-detail",
    ),
]
