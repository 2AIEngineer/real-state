"""Abstract bases inherited across the project."""

from django.db import models


class TimeStampedModel(models.Model):
    created_at = models.DateTimeField(auto_now_add=True, db_index=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        abstract = True


class ArchivableQuerySet(models.QuerySet):
    def not_archived(self):
        """Rows still on air (not archived)."""
        return self.filter(archived_at__isnull=True)


class ArchivableModel(models.Model):
    """Broadcasts that can be taken off air without being erased.

    Archiving keeps the row: the audit trail stays, and the people already
    notified can be told it was retracted. Erasing it for good is a separate,
    explicitly named operation (`delete`). Queries opt in with
    `.not_archived()` rather than going through a hidden manager.
    """

    archived_at = models.DateTimeField(null=True, blank=True, db_index=True)
    archived_by = models.ForeignKey(
        "accounts.User",
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name="+",
    )

    objects = ArchivableQuerySet.as_manager()

    class Meta:
        abstract = True
