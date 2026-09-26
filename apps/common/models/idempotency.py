"""The outcome of a POST sent with an `Idempotency-Key`, to answer its retries the same way."""

from django.conf import settings
from django.db import models


class IdempotencyKey(models.Model):
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="idempotency_keys",
    )
    key = models.CharField(max_length=255)
    # Method, path, selection and body of the first request: a retry must match it.
    fingerprint = models.CharField(max_length=64)
    # Empty while the first request is being processed.
    status_code = models.PositiveSmallIntegerField(null=True, blank=True)
    response = models.JSONField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True, db_index=True)

    class Meta:
        constraints = [
            models.UniqueConstraint(
                fields=["user", "key"], name="idempotency_key_per_user"
            )
        ]

    def __str__(self) -> str:
        return f"{self.key} ({self.status_code or 'pending'})"
