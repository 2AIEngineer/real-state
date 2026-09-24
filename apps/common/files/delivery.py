"""Answering a signed link: the file itself, or a redirect to where it is stored."""

from __future__ import annotations

import time
from urllib.parse import quote

from django.http import FileResponse, HttpResponse, HttpResponseRedirect

from apps.common.files.links import FileLink, expiry_for
from apps.common.files.rules import SHOWN_INLINE
from apps.common.models import Attachment


def content_disposition(attachment: Attachment) -> str:
    """Images, PDF and text open in the browser; office files are downloaded."""
    kind = "inline" if attachment.mime_type in SHOWN_INLINE else "attachment"
    return f"{kind}; filename*=UTF-8''{quote(attachment.original_filename)}"


def respond(attachment: Attachment, link: FileLink) -> HttpResponse:
    now = int(time.time())
    expires_at = link.expires_at or expiry_for(now)
    storage = attachment.file.storage
    disposition = content_disposition(attachment)

    if hasattr(storage, "signed_url"):
        response: HttpResponse = HttpResponseRedirect(
            storage.signed_url(
                attachment.file.name,
                expires_at=expires_at,
                content_type=attachment.mime_type,
                content_disposition=disposition,
            )
        )
    else:
        response = FileResponse(attachment.file.open("rb"), content_type=attachment.mime_type)
        response["Content-Disposition"] = disposition

    # Stored names are random and never rewritten: the content behind a link
    # never changes, so the browser keeps it for as long as the link is valid.
    scope = "public" if link.is_public else "private"
    response["Cache-Control"] = f"{scope}, max-age={max(expires_at - now, 0)}"
    return response
