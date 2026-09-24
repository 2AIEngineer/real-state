from django.urls import path

from apps.library import views

urlpatterns = [
    path("library/folders/", views.FolderListView.as_view(), name="folder-list"),
    path(
        "library/folders/<int:folder_id>/", views.FolderDetailView.as_view(), name="folder-detail"
    ),
    path("library/documents/", views.DocumentListView.as_view(), name="document-list"),
    path(
        "library/documents/<int:document_id>/",
        views.DocumentDetailView.as_view(),
        name="document-detail",
    ),
    path(
        "library/documents/<int:document_id>/file/",
        views.DocumentFileView.as_view(),
        name="document-file",
    ),
]
