"""The Azure storage signs read URLs locally: no network is involved."""

import base64
from urllib.parse import parse_qs, urlparse

from apps.common.files.storage import AzureFileStorage

KEY = base64.b64encode(b"k" * 32).decode()
CONNECTION = (
    f"DefaultEndpointsProtocol=https;AccountName=acct;AccountKey={KEY};"
    "EndpointSuffix=core.windows.net"
)


def storage() -> AzureFileStorage:
    return AzureFileStorage(connection_string=CONNECTION, azure_container="files")


def sign(expires_at=2_000_000_000, disposition="inline; filename*=UTF-8''a.pdf"):
    return storage().signed_url(
        "attachments/x.pdf",
        expires_at=expires_at,
        content_type="application/pdf",
        content_disposition=disposition,
    )


def test_the_sas_url_is_read_only_and_fixes_how_the_blob_is_served():
    url = urlparse(sign())
    query = parse_qs(url.query)

    assert url.netloc == "acct.blob.core.windows.net"
    assert url.path == "/files/attachments/x.pdf"
    assert query["sp"] == ["r"] and query["rsct"] == ["application/pdf"]
    assert query["rscd"] == ["inline; filename*=UTF-8''a.pdf"]


def test_the_same_link_window_gives_the_same_url():
    assert sign() == sign()
    assert sign() != sign(expires_at=2_000_003_600)
