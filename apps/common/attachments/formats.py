"""Recognising what a file really is, from its bytes."""

from __future__ import annotations

import hashlib
import mimetypes

import filetype
from django.core.files.uploadedfile import UploadedFile

from apps.common.attachments.rules import TEXT

_ALIASES = {"image/jpg": "image/jpeg"}


def detect_mime_type(upload: UploadedFile) -> str | None:
    """The real type, from the magic numbers; the client's claim is never trusted."""
    upload.seek(0)
    head = upload.read(8192)
    upload.seek(0)
    kind = filetype.guess(head)
    if kind is not None:
        return _ALIASES.get(kind.mime, kind.mime)
    # Plain-text formats have no signature: accept them by extension only when
    # the content decodes as text.
    guessed, _ = mimetypes.guess_type(upload.name or "")
    if guessed in TEXT:
        try:
            head.decode("utf-8")
        except UnicodeDecodeError:
            return None
        return guessed
    return None


def sha256_of(upload: UploadedFile) -> str:
    digest = hashlib.sha256()
    upload.seek(0)
    for chunk in upload.chunks():
        digest.update(chunk)
    upload.seek(0)
    return digest.hexdigest()
