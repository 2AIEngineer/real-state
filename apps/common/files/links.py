"""Links to stored files that work as they are: in an `<img src>`, an `<iframe>`, a download.

The client never sends a header nor fetches anything first: the URL carries its
own signature.

- A **public** file (see `rules.py`) has a link that never changes nor expires.
- A **private** file has a link personal to the reader, valid for a bounded
  time. The expiry is rounded up to a time window, so the link stays the same
  for the whole window: the browser caches the file, and two API calls in a row
  hand out the same URL. Any later API response carries a fresh link, so a
  client that renders what the API returns never handles expiry itself.

A link names the attachment, the reader and the end of validity, signed with
the project's secret: it cannot be forged, and it stops working when it expires
or when the reader's account is deactivated.
"""

from __future__ import annotations

import time
from dataclasses import dataclass

from django.conf import settings
from django.core import signing
from django.urls import reverse

from apps.common.files.rules import RULES
from apps.common.models import Attachment

_signer = signing.Signer(salt="apps.common.files.links")


@dataclass(frozen=True)
class FileLink:
    attachment_id: int
    reader_id: int | None = None  # None: public file
    expires_at: int | None = None  # epoch seconds; None: public file

    @property
    def is_public(self) -> bool:
        return self.reader_id is None


def window_seconds() -> int:
    return int(settings.FILES["LINK_WINDOW_HOURS"]) * 3600


def expiry_for(now: float) -> int:
    """End of validity of a link issued at `now`: between one and two windows ahead."""
    window = window_seconds()
    return (int(now) // window + 2) * window


def issue(attachment: Attachment, reader) -> FileLink:
    if RULES[attachment.entity_type].public or reader is None or not reader.is_authenticated:
        return FileLink(attachment.pk)
    return FileLink(attachment.pk, reader.pk, expiry_for(time.time()))


def token_of(link: FileLink) -> str:
    if link.is_public:
        return _signer.sign(str(link.attachment_id))
    return _signer.sign(f"{link.attachment_id}.{link.reader_id}.{link.expires_at}")


def path_of(attachment: Attachment, reader) -> str:
    return reverse("file", kwargs={"token": token_of(issue(attachment, reader))})


class InvalidLink(Exception):
    pass


class ExpiredLink(Exception):
    pass


def read(token: str, *, now: float | None = None) -> FileLink:
    """The link a token stands for; raises `InvalidLink` or `ExpiredLink`."""
    try:
        parts = [int(part) for part in _signer.unsign(token).split(".")]
    except (signing.BadSignature, ValueError):
        raise InvalidLink from None
    if len(parts) == 1:
        return FileLink(parts[0])
    if len(parts) != 3:
        raise InvalidLink
    link = FileLink(*parts)
    if link.expires_at <= (time.time() if now is None else now):
        raise ExpiredLink
    return link
