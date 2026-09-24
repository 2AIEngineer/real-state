"""Who may do what with events.

Same rules as announcements: people linked to the property read the events
addressed to one of their roles, management organises them, syndics
and admins erase them for good.
"""

from django.db.models import Q

from apps.accounts.services.authorization import AccessService
from apps.accounts.services.visibility import readable_property_or_building_records
from apps.events.models import Event
from apps.properties.models import Property


class EventPolicy:
    @staticmethod
    def visible_filter(user) -> Q:
        """Events addressed to the user (all of them for management)."""
        return readable_property_or_building_records(user)

    @staticmethod
    def can_list(user, prop: Property) -> bool:
        return AccessService.is_staff_or_resident_of_property(user, prop)

    @staticmethod
    def can_view(user, event: Event) -> bool:
        return (
            event.archived_at is None
            and Event.objects.filter(pk=event.pk).filter(EventPolicy.visible_filter(user)).exists()
        )

    @staticmethod
    def can_create(user, prop: Property) -> bool:
        return AccessService.manages_property(user, prop)

    @staticmethod
    def can_update(user, event: Event) -> bool:
        """Editing, rescheduling and the attached files."""
        return AccessService.manages_property(user, event.property)

    @staticmethod
    def can_cancel(user, event: Event) -> bool:
        return AccessService.manages_property(user, event.property)

    @staticmethod
    def can_archive(user, event: Event) -> bool:
        return AccessService.manages_property(user, event.property)

    @staticmethod
    def can_delete(user, event: Event) -> bool:
        return AccessService.manages_syndicat(user, event.property.syndicat)
