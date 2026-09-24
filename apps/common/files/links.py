"""Links to stored files that work as they are: in an `<img src>`, an `<iframe>`, a download.

The client never sends a header, never fetches anything first, and never
handles an expiry: the URL carries its own signature and does not expire.

- A **public** file (see `rules.py`) has one link, the same for everyone.
- A **private** file has a link personal to its reader. It stays valid as long
  as the reader's account does: it stops working when the account is
  deactivated or its password changes (the moments a stolen session is cut,
  see `apps.accounts.services.tokens`), and never on a timer.

A link names the attachment and, for a private file, the reader and the date
of their last password change, all signed with the project's secret: it
cannot be forged nor transferred to another attachment.
"""

from __future__ import annotations

from dataclasses import dataclass

from django.contrib.auth import get_user_model
from django.core import signing
from django.urls import reverse

from apps.common.files.rules import RULES
from apps.common.models import Attachment

_signer = signing.Signer(salt="apps.common.files.links")


@dataclass(frozen=True)
class FileLink:
    attachment_id: int
    reader_id: int | None = None  # None: public file
    password_stamp: int = 0  # the reader's last password change, epoch seconds

    @property
    def is_public(self) -> bool:
        return self.reader_id is None


def _password_stamp(user) -> int:
    changed = getattr(user, "password_changed_at", None)
    return int(changed.timestamp()) if changed else 0


def issue(attachment: Attachment, reader) -> FileLink:
    if RULES[attachment.entity_type].public or reader is None or not reader.is_authenticated:
        return FileLink(attachment.pk)
    return FileLink(attachment.pk, reader.pk, _password_stamp(reader))


def token_of(link: FileLink) -> str:
    if link.is_public:
        return _signer.sign(str(link.attachment_id))
    return _signer.sign(f"{link.attachment_id}.{link.reader_id}.{link.password_stamp}")


def path_of(attachment: Attachment, reader) -> str:
    return reverse("file", kwargs={"token": token_of(issue(attachment, reader))})


class InvalidLink(Exception):
    """Forged, damaged, or revoked (reader deactivated or password changed)."""


def read(token: str) -> FileLink:
    """The link a token stands for, still honoured; raises `InvalidLink` otherwise."""
    try:
        parts = [int(part) for part in _signer.unsign(token).split(".")]
    except (signing.BadSignature, ValueError):
        raise InvalidLink from None
    if len(parts) == 1:
        return FileLink(parts[0])
    if len(parts) != 3:
        raise InvalidLink
    link = FileLink(*parts)
    reader = get_user_model().objects.filter(pk=link.reader_id, is_active=True).first()
    if reader is None or _password_stamp(reader) != link.password_stamp:
        raise InvalidLink
    return link
