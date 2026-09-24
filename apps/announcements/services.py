"""Announcements addressed to target roles, with a frozen recipient snapshot.

The target roles (and optional building) are fixed at publication:
the snapshot records who was told, and deletion warns the same people.
"""

from __future__ import annotations

import datetime as dt

from django.db import transaction
from django.db.models import Q, QuerySet
from django.utils import timezone

from apps.announcements import notices
from apps.announcements.audit import AnnouncementAudit
from apps.announcements.models import Announcement, AnnouncementPriority
from apps.announcements.policies import AnnouncementPolicy
from apps.common.db import apply_changes, deleting
from apps.common.exceptions import InvalidInput, NotFound, PermissionDenied
from apps.common.files.rules import EntityType
from apps.common.files.service import AttachmentService
from apps.common.services.audit import AuditService
from apps.notifications.services import SnapshotService, delete_notification_traces
from apps.properties.enums import Feature
from apps.properties.models import Building, Property
from apps.properties.services import FeatureGate

EDITABLE_FIELDS = ("title", "body", "category", "priority", "expires_at")


class AnnouncementService:
    @staticmethod
    def list_visible(
        *,
        actor,
        prop: Property,
        include_expired: bool = False,
        category: str | None = None,
    ) -> QuerySet[Announcement]:
        if not AnnouncementPolicy.can_list(actor, prop):
            raise PermissionDenied("You have no link with this property.")
        FeatureGate.require(prop, Feature.ANNOUNCEMENTS)
        qs = (
            Announcement.objects.not_archived()
            .filter(property=prop)
            .filter(AnnouncementPolicy.visible_filter(actor))
            .select_related("created_by", "building")
        )
        now = timezone.now()
        sees_unpublished = AnnouncementPolicy.can_see_unpublished(actor, prop)
        if not sees_unpublished:
            qs = qs.filter(published_at__lte=now)
        if not include_expired or not sees_unpublished:
            qs = qs.filter(Q(expires_at__isnull=True) | Q(expires_at__gt=now))
        if category:
            qs = qs.filter(category=category)
        return qs

    @staticmethod
    def get_visible(*, actor, announcement_id: int) -> Announcement:
        announcement = (
            Announcement.objects.not_archived()
            .filter(pk=announcement_id)
            .filter(AnnouncementPolicy.visible_filter(actor))
            .select_related("property", "building", "created_by")
            .first()
        )
        if announcement is None:
            raise NotFound("Announcement not found.")
        return announcement

    @staticmethod
    def get_manageable(*, actor, announcement_id: int) -> Announcement:
        """Lookup for management actions, archived records included.

        A archived announcement is out of everyone's feed but must stay reachable
        for the people who may erase it for good.
        """
        announcement = (
            Announcement.objects.select_related("property").filter(pk=announcement_id).first()
        )
        if announcement is None or not AnnouncementPolicy.can_update(actor, announcement):
            raise NotFound("Announcement not found.")
        return announcement

    @staticmethod
    @transaction.atomic
    def publish(
        *,
        actor,
        prop: Property,
        title: str,
        body: str,
        target_roles: list[str],
        category: str,
        priority: str = AnnouncementPriority.NORMAL,
        building: Building | None = None,
        published_at: dt.datetime | None = None,
        expires_at: dt.datetime | None = None,
        files=(),
    ) -> Announcement:
        if not AnnouncementPolicy.can_publish(actor, prop):
            raise PermissionDenied("Only the property management can publish announcements.")
        FeatureGate.require(prop, Feature.ANNOUNCEMENTS)
        roles = SnapshotService.validate_target_roles(target_roles)
        if building is not None and building.property_id != prop.pk:
            raise InvalidInput("The building belongs to another property.", field="building_id")
        published_at = published_at or timezone.now()
        if expires_at and expires_at <= published_at:
            raise InvalidInput("The expiry must follow the publication.", field="expires_at")
        announcement = Announcement.objects.create(
            property=prop,
            building=building,
            title=title.strip(),
            body=body,
            category=category,
            priority=priority,
            target_roles=roles,
            published_at=published_at,
            expires_at=expires_at,
            created_by=actor,
        )
        AttachmentService.attach(
            entity_type=EntityType.ANNOUNCEMENT,
            entity_id=announcement.pk,
            files=list(files),
            uploaded_by=actor,
        )
        recipients = SnapshotService.freeze(
            target=announcement, prop=prop, target_roles=roles, building=building
        )
        AuditService.record(
            actor=actor,
            action=AnnouncementAudit.PUBLISHED,
            target=announcement,
            property_id=prop.pk,
        )
        notices.published(announcement, recipients=recipients, actor=actor)
        return announcement

    @staticmethod
    @transaction.atomic
    def update(*, actor, announcement: Announcement, changes: dict) -> Announcement:
        """Editorial corrections only: the target roles are frozen at publication."""
        if not AnnouncementPolicy.can_update(actor, announcement):
            raise PermissionDenied("Only the property management can edit announcements.")
        if "target_roles" in changes or "building" in changes:
            raise InvalidInput(
                "The target roles of a published announcement cannot change.",
                field="target_roles",
            )
        fields = apply_changes(announcement, changes, EDITABLE_FIELDS)
        if announcement.expires_at and announcement.expires_at <= announcement.published_at:
            raise InvalidInput("The expiry must follow the publication.", field="expires_at")
        if fields:
            announcement.save(update_fields=[*fields, "updated_at"])
            AuditService.record(
                actor=actor,
                action=AnnouncementAudit.UPDATED,
                target=announcement,
                property_id=announcement.property_id,
                metadata={"fields": fields},
            )
        return announcement

    @staticmethod
    @transaction.atomic
    def add_files(*, actor, announcement: Announcement, files) -> list:
        if not AnnouncementPolicy.can_update(actor, announcement):
            raise PermissionDenied("Only the property management can edit announcements.")
        return AttachmentService.attach(
            entity_type=EntityType.ANNOUNCEMENT,
            entity_id=announcement.pk,
            files=list(files),
            uploaded_by=actor,
        )

    @staticmethod
    @transaction.atomic
    def remove_file(*, actor, announcement: Announcement, attachment_id: int) -> None:
        if not AnnouncementPolicy.can_update(actor, announcement):
            raise PermissionDenied("Only the property management can edit announcements.")
        AttachmentService.delete(
            attachment=AttachmentService.get(
                entity_type=EntityType.ANNOUNCEMENT,
                entity_id=announcement.pk,
                attachment_id=attachment_id,
            )
        )

    @staticmethod
    @transaction.atomic
    def delete(*, actor, announcement) -> None:
        """Permanent removal, files and delivered notifications included.

        The soft delete keeps the announcement for the audit trail; this one
        is for records created by mistake or for a demonstration.
        """
        if not AnnouncementPolicy.can_delete(actor, announcement):
            raise PermissionDenied(
                "Only administrators and syndics can permanently delete this record."
            )
        AuditService.record(
            actor=actor,
            action=AnnouncementAudit.DELETED,
            target=announcement,
            property_id=announcement.property_id,
            metadata={"title": announcement.title},
        )
        with deleting("announcement"):
            AttachmentService.delete_for_entity(EntityType.ANNOUNCEMENT, announcement.pk)
            delete_notification_traces(announcement)
            announcement.delete()

    @staticmethod
    @transaction.atomic
    def archive(*, actor, announcement: Announcement) -> None:
        if not AnnouncementPolicy.can_archive(actor, announcement):
            raise PermissionDenied("Only the property management can archive announcements.")
        announcement.archived_at = timezone.now()
        announcement.archived_by = actor
        announcement.save(update_fields=["archived_at", "archived_by", "updated_at"])
        AuditService.record(
            actor=actor,
            action=AnnouncementAudit.ARCHIVED,
            target=announcement,
            property_id=announcement.property_id,
        )
        notices.archived(announcement, actor=actor)
