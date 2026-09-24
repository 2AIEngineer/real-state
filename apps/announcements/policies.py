"""Who may do what with announcements.

Everyone linked to a property reads the announcements addressed to one of
their roles. The property management writes them; only syndics and
admins erase them for good.
"""

from django.db.models import Q

from apps.accounts.services.authorization import AccessService
from apps.accounts.services.visibility import readable_property_or_building_records
from apps.announcements.models import Announcement
from apps.properties.models import Property


class AnnouncementPolicy:
    @staticmethod
    def visible_filter(user) -> Q:
        """Announcements addressed to the user (all of them for management)."""
        return readable_property_or_building_records(user)

    @staticmethod
    def can_list(user, prop: Property) -> bool:
        return AccessService.is_staff_or_resident_of_property(user, prop)

    @staticmethod
    def can_see_unpublished(user, prop: Property) -> bool:
        """Scheduled and expired announcements are shown to management only."""
        return AccessService.manages_property(user, prop)

    @staticmethod
    def can_view(user, announcement: Announcement) -> bool:
        return (
            announcement.archived_at is None
            and Announcement.objects.filter(pk=announcement.pk)
            .filter(AnnouncementPolicy.visible_filter(user))
            .exists()
        )

    @staticmethod
    def can_publish(user, prop: Property) -> bool:
        return AccessService.manages_property(user, prop)

    @staticmethod
    def can_update(user, announcement: Announcement) -> bool:
        """Editing the text and the attached files."""
        return AccessService.manages_property(user, announcement.property)

    @staticmethod
    def can_archive(user, announcement: Announcement) -> bool:
        return AccessService.manages_property(user, announcement.property)

    @staticmethod
    def can_delete(user, announcement: Announcement) -> bool:
        return AccessService.manages_syndicat(user, announcement.property.syndicat)
