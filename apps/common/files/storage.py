"""Azure Blob storage for attachments: a private container, read through short SAS URLs.

The container is never public. A file is read through the signed link of
`links.py`, which redirects to a SAS URL expiring with that link; the SAS also
fixes the `Content-Type` and `Content-Disposition` the blob is served with, so
a stored file is always shown as the format it was detected as.
"""

from __future__ import annotations

import datetime as dt
from functools import lru_cache

from azure.storage.blob import BlobSasPermissions, generate_blob_sas
from storages.backends.azure_storage import AzureStorage


class AzureFileStorage(AzureStorage):
    def signed_url(
        self, name: str, *, expires_at: int, content_type: str, content_disposition: str
    ) -> str:
        """A read-only SAS URL valid until `expires_at` (epoch seconds).

        The same inputs give the same URL, so a redirect to it can be cached.
        """
        expiry = dt.datetime.fromtimestamp(expires_at, tz=dt.UTC)
        sas = generate_blob_sas(
            self.account_name,
            self.azure_container,
            self._get_valid_path(name),
            account_key=self.account_key,
            user_delegation_key=None if self.account_key else self._delegation_key(expires_at),
            permission=BlobSasPermissions(read=True),
            expiry=expiry,
            content_type=content_type,
            content_disposition=content_disposition,
        )
        return f"{self.client.get_blob_client(self._get_valid_path(name)).url}?{sas}"

    def _delegation_key(self, expires_at: int):
        # One key per link window (managed identity, no account key): asking
        # Azure AD for a key on every read would cost a round trip each time.
        return _cached_delegation_key(self, expires_at)


@lru_cache(maxsize=8)
def _cached_delegation_key(storage: AzureFileStorage, expires_at: int):
    expiry = dt.datetime.fromtimestamp(expires_at, tz=dt.UTC)
    return storage.get_user_delegation_key(expiry)
