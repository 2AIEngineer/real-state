from django.urls import path

from apps.common.files.views import FileView

urlpatterns = [path("files/<str:token>/", FileView.as_view(), name="file")]
