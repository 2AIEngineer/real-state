"""Every account is born with its notification preferences, whatever creates it
(account service, management commands, Django admin, demo seed)."""

from django.conf import settings
from django.db.models.signals import post_save
from django.dispatch import receiver

from apps.notifications.services.preferences import PreferenceService


@receiver(post_save, sender=settings.AUTH_USER_MODEL, dispatch_uid="notification_preferences")
def create_notification_preferences(sender, instance, created, raw=False, **kwargs) -> None:
    if created and not raw:
        PreferenceService.create_for(instance)
