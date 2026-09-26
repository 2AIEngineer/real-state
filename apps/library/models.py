from django.conf import settings
from django.contrib.postgres.fields import ArrayField
from django.db import models
from django.db.models import Q
from django.db.models.functions import Lower

from apps.accounts.enums import PropertyRole
from apps.common.models import TimeStampedModel


class Folder(TimeStampedModel):
    property = models.ForeignKey(
        "properties.Property", on_delete=models.CASCADE, related_name="library_folders"
    )
    parent_folder = models.ForeignKey(
        "self",
        null=True,
        blank=True,
        on_delete=models.CASCADE,
        related_name="subfolders",
    )
    en_name = models.CharField(max_length=160)
    fr_name = models.CharField(max_length=160)
    description = models.TextField(blank=True)
    is_system = models.BooleanField(
        default=False,
        help_text="Created with the property as a starting point; editable and deletable like any.",
    )
    created_by = models.ForeignKey(
        settings.AUTH_USER_MODEL, null=True, on_delete=models.SET_NULL, related_name="+"
    )

    class Meta:
        ordering = ["property_id", "en_name", "id"]
        constraints = [
            models.UniqueConstraint(
                "property",
                "parent_folder",
                Lower("en_name"),
                nulls_distinct=False,
                name="folder_en_name_per_parent",
            ),
            models.UniqueConstraint(
                "property",
                "parent_folder",
                Lower("fr_name"),
                nulls_distinct=False,
                name="folder_fr_name_per_parent",
            ),
            models.CheckConstraint(
                condition=~Q(parent_folder=models.F("id")),
                name="folder_not_its_own_parent",
            ),
        ]

    def __str__(self) -> str:
        return self.en_name


class LibraryDocument(TimeStampedModel):
    """A published document; its file is an attachment of type `library_document`."""

    folder = models.ForeignKey(Folder, on_delete=models.CASCADE, related_name="documents")
    property = models.ForeignKey(
        "properties.Property",
        on_delete=models.CASCADE,
        related_name="library_documents",
    )
    title = models.CharField(max_length=200)
    description = models.TextField(blank=True)
    target_roles = ArrayField(models.CharField(max_length=16, choices=PropertyRole.choices))
    created_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="+",
    )

    class Meta:
        ordering = ["-created_at", "-id"]
        constraints = [
            models.CheckConstraint(
                condition=Q(target_roles__len__gt=0),
                name="library_document_has_target_roles",
            )
        ]
        indexes = [models.Index(fields=["property", "folder"])]

    def __str__(self) -> str:
        return self.title
