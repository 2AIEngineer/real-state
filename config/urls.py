from django.conf import settings
from django.urls import include, path, re_path
from django.views.static import serve
from drf_spectacular.views import SpectacularAPIView, SpectacularSwaggerView

from apps.common import health

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


def serve_media(request, path):
    """Files on the local disk (development), at the URL the serializers hand out."""
    return serve(request, path, document_root=settings.MEDIA_ROOT)


urlpatterns = [
    path("healthz/", health.liveness, name="healthz"),
    path("readyz/", health.readiness, name="readyz"),
    *(path("api/v1/", include(module)) for module in API_MODULES),
]

if settings.STORAGES["default"]["BACKEND"].endswith("FileSystemStorage"):
    # With Azure Blob the URL points at the storage and this route is not registered.
    urlpatterns += [re_path(r"^media/(?P<path>.*)$", serve_media)]

if settings.DEBUG:
    urlpatterns += [
        path("api/schema/", SpectacularAPIView.as_view(), name="schema"),
        path("api/docs/", SpectacularSwaggerView.as_view(url_name="schema"), name="docs"),
    ]
