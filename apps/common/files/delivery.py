"""Answering a signed link: the file itself, or a redirect to where it is stored."""

from __future__ import annotations

import time
from urllib.parse import quote

from django.http import FileResponse, HttpResponse, HttpResponseRedirect

from apps.common.files.links import FileLink
from apps.common.files.rules import SHOWN_INLINE
from apps.common.models import Attachment

# The storage URL a link redirects to (Azure SAS) is internal and short-lived:
# the browser follows it at once. Its expiry is rounded to the hour so the same
# redirect is handed out for a while and the browser can cache it.
STORAGE_URL_WINDOW = 3600
# Stored names are random and never rewritten: what a link points to never changes.
FILE_MAX_AGE = 7 * 24 * 3600


def content_disposition(attachment: Attachment) -> str:
    """Images, PDF and text open in the browser; office files are downloaded."""
    kind = "inline" if attachment.mime_type in SHOWN_INLINE else "attachment"
    return f"{kind}; filename*=UTF-8''{quote(attachment.original_filename)}"


def respond(attachment: Attachment, link: FileLink) -> HttpResponse:
    storage = attachment.file.storage
    disposition = content_disposition(attachment)
    scope = "public" if link.is_public else "private"

    if hasattr(storage, "signed_url"):
        now = int(time.time())
        expires_at = (now // STORAGE_URL_WINDOW + 2) * STORAGE_URL_WINDOW
        response: HttpResponse = HttpResponseRedirect(
            storage.signed_url(
                attachment.file.name,
                expires_at=expires_at,
                content_type=attachment.mime_type,
                content_disposition=disposition,
            )
        )
        # Kept no longer than the storage URL it points to stays valid.
        response["Cache-Control"] = f"{scope}, max-age={expires_at - now - 60}"
        return response

    response = FileResponse(attachment.file.open("rb"), content_type=attachment.mime_type)
    response["Content-Disposition"] = disposition
    response["Cache-Control"] = f"{scope}, max-age={FILE_MAX_AGE}"
    return response
