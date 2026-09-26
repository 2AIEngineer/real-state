"""Who may do what with work orders.

Management of the property creates, edits, cancels and deletes work
orders. The assignee sees the ones given to them, moves them through their
lifecycle (start, complete...) and adds files.
"""

from django.db.models import Q

from apps.accounts.services.authorization import AccessService
from apps.properties.models import Property
from apps.work_orders.models import WorkOrder


class WorkOrderPolicy:
    @staticmethod
    def visible_filter(user) -> Q:
        return Q(property_id__in=AccessService.managed_property_ids(user)) | Q(
            assignee=user
        )

    @staticmethod
    def can_view(user, wo: WorkOrder) -> bool:
        return wo.assignee_id == user.pk or AccessService.manages_property(
            user, wo.property
        )

    @staticmethod
    def can_create(user, prop: Property) -> bool:
        return AccessService.manages_property(user, prop)

    @staticmethod
    def can_update(user, wo: WorkOrder) -> bool:
        return AccessService.manages_property(user, wo.property)

    @staticmethod
    def can_progress(user, wo: WorkOrder) -> bool:
        """Start, complete, reopen... every transition except cancel."""
        return wo.assignee_id == user.pk or AccessService.manages_property(
            user, wo.property
        )

    @staticmethod
    def can_cancel(user, wo: WorkOrder) -> bool:
        return AccessService.manages_property(user, wo.property)

    @staticmethod
    def can_add_files(user, wo: WorkOrder) -> bool:
        return wo.assignee_id == user.pk or AccessService.manages_property(
            user, wo.property
        )

    @staticmethod
    def can_delete(user, wo: WorkOrder) -> bool:
        return AccessService.manages_property(user, wo.property)
