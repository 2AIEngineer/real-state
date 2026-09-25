"""Small but real files for the demo: PNG pictures and PDF documents, made in memory."""

from __future__ import annotations

import struct
import zlib

from django.core.files.uploadedfile import SimpleUploadedFile


def _chunk(kind: bytes, data: bytes) -> bytes:
    return struct.pack(">I", len(data)) + kind + data + struct.pack(">I", zlib.crc32(kind + data))


def png(
    name: str, color: tuple[int, int, int], size: tuple[int, int] = (96, 64)
) -> SimpleUploadedFile:
    """A picture shaded from `color` to a lighter tone, so thumbnails are told apart."""
    width, height = size
    rows = []
    for y in range(height):
        shade = y / max(height - 1, 1) * 0.6
        pixel = bytes(int(c + (255 - c) * shade) for c in color)
        rows.append(b"\x00" + pixel * width)
    header = struct.pack(">IIBBBBB", width, height, 8, 2, 0, 0, 0)
    data = (
        b"\x89PNG\r\n\x1a\n"
        + _chunk(b"IHDR", header)
        + _chunk(b"IDAT", zlib.compress(b"".join(rows), 9))
        + _chunk(b"IEND", b"")
    )
    return SimpleUploadedFile(name, data, content_type="image/png")


def _pdf_text(value: str) -> str:
    ascii_only = value.encode("latin-1", "replace").decode("latin-1")
    return ascii_only.replace("\\", "\\\\").replace("(", "\\(").replace(")", "\\)")


def pdf(name: str, title: str, lines: list[str] = ()) -> SimpleUploadedFile:
    """A one-page PDF with a title and a few lines of text."""
    text = ["BT /F1 18 Tf 60 780 Td (" + _pdf_text(title) + ") Tj ET"]
    for index, line in enumerate(lines):
        text.append(f"BT /F1 11 Tf 60 {740 - 18 * index} Td ({_pdf_text(line)}) Tj ET")
    stream = "\n".join(text).encode("latin-1")
    objects = [
        b"<< /Type /Catalog /Pages 2 0 R >>",
        b"<< /Type /Pages /Kids [3 0 R] /Count 1 >>",
        b"<< /Type /Page /Parent 2 0 R /MediaBox [0 0 595 842] /Contents 4 0 R "
        b"/Resources << /Font << /F1 5 0 R >> >> >>",
        b"<< /Length " + str(len(stream)).encode() + b" >>\nstream\n" + stream + b"\nendstream",
        b"<< /Type /Font /Subtype /Type1 /BaseFont /Helvetica /Encoding /WinAnsiEncoding >>",
    ]
    body = b"%PDF-1.4\n"
    offsets = []
    for number, content in enumerate(objects, start=1):
        offsets.append(len(body))
        body += f"{number} 0 obj\n".encode() + content + b"\nendobj\n"
    xref = len(body)
    body += f"xref\n0 {len(objects) + 1}\n0000000000 65535 f \n".encode()
    body += b"".join(f"{offset:010d} 00000 n \n".encode() for offset in offsets)
    body += (
        f"trailer\n<< /Size {len(objects) + 1} /Root 1 0 R >>\nstartxref\n{xref}\n%%EOF\n".encode()
    )
    return SimpleUploadedFile(name, body, content_type="application/pdf")
