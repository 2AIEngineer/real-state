"""Who may do what in conversations.

A conversation belongs to a context (service request, booking or order) and
its participants are those of the context: the person who initiated it, the
people who run it (the property management, or platform administrators for
store orders) and, for service requests, the assigned maintenance staff.
"""

from django.db.models import Q

from apps.accounts.services.authorization import AccessService
from apps.chat.contexts import RoomContext
from apps.chat.models import ChatMessage


class ChatPolicy:
    @staticmethod
    def visible_rooms_filter(user) -> Q:
        managed = AccessService.managed_property_ids(user)
        visible = (
            Q(service_request__requester=user)
            | Q(booking__booker=user)
            | Q(order__orderer=user)
            | Q(service_request__property_id__in=managed)
            | Q(booking__amenity__property_id__in=managed)
            | Q(service_request__assignments__resolver=user)
        )
        if AccessService.is_platform_admin(user):
            visible |= Q(order__isnull=False)
        return visible

    @staticmethod
    def is_moderator(user, ctx: RoomContext) -> bool:
        """Who runs the conversation: store admins for orders, management otherwise."""
        if ctx.kind == "order":
            return AccessService.is_platform_admin(user)
        return AccessService.manages_property(user, ctx.prop)

    @staticmethod
    def can_participate(user, ctx: RoomContext) -> bool:
        """Open, read and post in the conversation."""
        if not user.is_active:
            return False
        return (
            ctx.initiator.pk == user.pk
            or ChatPolicy.is_moderator(user, ctx)
            or (
                ctx.kind == "service_request" and ctx.obj.assignments.filter(resolver=user).exists()
            )
        )

    @staticmethod
    def can_edit_message(user, message: ChatMessage) -> bool:
        return message.sender_id == user.pk

    @staticmethod
    def can_delete_message(user, message: ChatMessage, ctx: RoomContext) -> bool:
        return message.sender_id == user.pk or ChatPolicy.is_moderator(user, ctx)
