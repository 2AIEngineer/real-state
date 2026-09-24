"""What the people a document is addressed to are told about it."""

from __future__ import annotations

from apps.library.models import LibraryDocument
from apps.notifications.models import NotificationCategory
from apps.notifications.services import NotificationIntent, NotificationService


def document_published(document: LibraryDocument, *, recipients, actor) -> None:
    NotificationService.notify(
        NotificationIntent(
            event_type="library.document_published",
            category=NotificationCategory.LIBRARY,
            title=f"Nouveau document — {document.property.name}",
            body=(
                f"Le document « {document.title} » a été ajouté "
                f"à la bibliothèque ({document.folder.fr_name})."
            ),
            bcc=recipients,
            target=document,
            exclude=[actor],
            data={"document_id": document.pk, "property_id": document.property_id},
            action_path=f"/library/documents/{document.pk}",
        )
    )
