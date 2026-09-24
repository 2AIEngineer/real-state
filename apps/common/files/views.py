"""The one route that reads a stored file, from a signed link."""

from __future__ import annotations

from django.contrib.auth import get_user_model
from django.http import Http404, HttpResponse
from drf_spectacular.utils import extend_schema
from rest_framework.permissions import AllowAny
from rest_framework.views import APIView

from apps.common.exceptions import PermissionDenied
from apps.common.files import delivery, links
from apps.common.models import Attachment


@extend_schema(exclude=True)  # never called by name: clients open the `url` of an attachment
class FileView(APIView):
    """Opens a file from the `url` of an attachment. No header needed: the link is signed."""

    authentication_classes: list = []
    permission_classes = [AllowAny]

    def get(self, request, token: str) -> HttpResponse:
        try:
            link = links.read(token)
        except links.InvalidLink:
            raise Http404 from None
        except links.ExpiredLink:
            raise PermissionDenied(
                "This link has expired: reload the page to get a new one.", code="link_expired"
            ) from None
        if not link.is_public and not _reader_is_active(link.reader_id):
            raise Http404
        attachment = Attachment.objects.filter(pk=link.attachment_id).first()
        if attachment is None:
            raise Http404
        return delivery.respond(attachment, link)


def _reader_is_active(reader_id: int) -> bool:
    return get_user_model().objects.filter(pk=reader_id, is_active=True).exists()
