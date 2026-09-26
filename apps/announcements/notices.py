"""What the people an announcement is addressed to are told about it."""

from __future__ import annotations

from apps.announcements.models import Announcement, AnnouncementPriority
from apps.notifications.models import NotificationCategory, Severity
from apps.notifications.services import (
    NotificationIntent,
    NotificationService,
    SnapshotService,
)

PRIORITY_SEVERITY = {
    AnnouncementPriority.NORMAL: Severity.INFO,
    AnnouncementPriority.IMPORTANT: Severity.WARNING,
    AnnouncementPriority.URGENT: Severity.CRITICAL,
}


def published(announcement: Announcement, *, recipients, actor) -> None:
    NotificationService.notify(
        NotificationIntent(
            event_type="announcement.created",
            category=NotificationCategory.ANNOUNCEMENT,
            title=f"[{announcement.property.name}] {announcement.title}",
            body=announcement.body[:280],
            bcc=recipients,
            target=announcement,
            severity=PRIORITY_SEVERITY[announcement.priority],
            exclude=[actor],
            data={
                "announcement_id": announcement.pk,
                "property_id": announcement.property_id,
            },
            action_path=f"/announcements/{announcement.pk}",
        )
    )


def archived(announcement: Announcement, *, actor) -> None:
    NotificationService.notify(
        NotificationIntent(
            event_type="announcement.archived",
            category=NotificationCategory.ANNOUNCEMENT,
            title=f"[{announcement.property.name}] Annonce retirée",
            body=f"L'annonce « {announcement.title} » a été retirée.",
            bcc=SnapshotService.recipients(announcement),
            target=announcement,
            exclude=[actor],
            data={
                "announcement_id": announcement.pk,
                "property_id": announcement.property_id,
            },
        )
    )
