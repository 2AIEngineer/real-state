from django.conf import settings
from django.urls import include, path, re_path
from django.views.static import serve
from drf_spectacular.views import SpectacularAPIView, SpectacularSwaggerView

API_MODULES = [
    "apps.accounts.urls",
    "apps.properties.urls",
    "apps.leasing.urls",
    "apps.notifications.urls",
    "apps.announcements.urls",
    "apps.service_requests.urls",
    "apps.work_orders.urls",
    "apps.events.urls",
    "apps.amenities.urls",
    "apps.store.urls",
    "apps.library.urls",
    "apps.short_term_rental.urls",
    "apps.surveys.urls",
    "apps.marketplace.urls",
    "apps.visitors.urls",
    "apps.chat.urls",
]

urlpatterns = [path("api/v1/", include(module)) for module in API_MODULES]


def serve_media(request, path):
    """Files kept on the server's disk, at the URL the serializers hand out.

    With a storage service (Azure) that URL points at the service instead and
    this route is not registered. The stored names are random, so a URL cannot
    be guessed from the record it belongs to.
    """
    return serve(request, path, document_root=settings.MEDIA_ROOT)


if settings.STORAGES["default"]["BACKEND"].endswith("FileSystemStorage"):
    urlpatterns += [re_path(r"^media/(?P<path>.*)$", serve_media)]

if settings.DEBUG:
    urlpatterns += [
        path("api/schema/", SpectacularAPIView.as_view(), name="schema"),
        path("api/docs/", SpectacularSwaggerView.as_view(url_name="schema"), name="docs"),
    ]
