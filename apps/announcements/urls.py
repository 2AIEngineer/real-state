from django.urls import path

from apps.announcements import views

urlpatterns = [
    path(
        "announcements/", views.AnnouncementListView.as_view(), name="announcement-list"
    ),
    path(
        "announcements/<int:announcement_id>/",
        views.AnnouncementDetailView.as_view(),
        name="announcement-detail",
    ),
    path(
        "announcements/<int:announcement_id>/archive/",
        views.AnnouncementArchiveView.as_view(),
        name="announcement-archive",
    ),
    path(
        "announcements/<int:announcement_id>/files/",
        views.AnnouncementFilesView.as_view(),
        name="announcement-files",
    ),
    path(
        "announcements/<int:announcement_id>/files/<int:attachment_id>/",
        views.AnnouncementFileDetailView.as_view(),
        name="announcement-file-detail",
    ),
]
