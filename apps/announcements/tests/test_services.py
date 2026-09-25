import datetime as dt

import pytest
from django.utils import timezone

from apps.accounts.enums import PropertyRole
from apps.announcements.models import AnnouncementCategory
from apps.announcements.services import AnnouncementService
from apps.common.exceptions import FeatureDisabled, InvalidInput, NotFound, PermissionDenied
from apps.notifications.models import InboxNotification, RecipientSnapshot
from apps.properties.enums import Feature
from apps.properties.services import PropertyService
from tests import factories as f

pytestmark = pytest.mark.django_db


def publish(world, roles, **kwargs):
    return AnnouncementService.publish(
        actor=kwargs.pop("actor", world.manager),
        prop=world.prop,
        title="Water cut",
        body="Tomorrow 9am-12am.",
        target_roles=roles,
        category=AnnouncementCategory.MAINTENANCE,
        **kwargs,
    )


def visible(world, user):
    return list(AnnouncementService.list_visible(actor=user, prop=world.prop))


class TestTargetRoles:
    def test_only_targeted_roles_see_it(self, world):
        announcement = publish(world, [PropertyRole.TENANT])
        assert visible(world, world.tenant) == [announcement]
        assert visible(world, world.owner) == []
        assert visible(world, world.manager) == [announcement]  # management sees everything

    def test_account_role_counts_only_where_it_applies(self, world):
        """The manager of A is a manager everywhere, but only reached as owner in B."""
        other_prop = f.make_property(syndicat=world.syndicat)
        other_unit = f.make_unit(f.make_building(other_prop), world.admin)
        f.make_owner(other_unit, world.manager, world.admin)
        f.assign_role(other_manager := f.make_user(), "manager", other_prop)
        for_managers, for_entities = (
            AnnouncementService.publish(
                actor=other_manager,
                prop=other_prop,
                title=title,
                body="-",
                target_roles=[role],
                category=AnnouncementCategory.MAINTENANCE,
            )
            for title, role in (("Managers", PropertyRole.MANAGER), ("Owners", PropertyRole.OWNER))
        )
        seen = list(AnnouncementService.list_visible(actor=world.manager, prop=other_prop))
        assert seen == [for_entities] and for_managers not in seen

    def test_building_narrowing(self, world):
        announcement = publish(
            world, [PropertyRole.SECURITY, PropertyRole.OWNER], building=world.other_building
        )
        assert visible(world, world.security) == []  # security is assigned to building A only
        assert visible(world, world.owner) == []  # owns a unit in building A
        other_guard = f.make_user()
        f.assign_role(other_guard, "security", world.other_building)
        assert visible(world, other_guard) == [announcement]

    def test_snapshot_freezes_recipients_and_notifies_them(self, world):
        announcement = publish(world, [PropertyRole.TENANT])
        snapshot = set(
            RecipientSnapshot.objects.filter(object_id=announcement.pk).values_list(
                "user_id", flat=True
            )
        )
        assert snapshot == {world.tenant.pk, world.co_tenant.pk}
        assert InboxNotification.objects.filter(
            notification_type="announcement.created", user=world.tenant
        ).exists()

    def test_archiving_notifies_the_snapshot_not_the_current_role_holders(self, world):
        announcement = publish(world, [PropertyRole.TENANT])
        newcomer = f.make_user()
        f.make_lease(world.other_unit, [newcomer], world.admin)
        AnnouncementService.archive(actor=world.manager, announcement=announcement)
        archived = InboxNotification.objects.filter(notification_type="announcement.archived")
        assert set(archived.values_list("user_id", flat=True)) >= {
            world.tenant.pk,
            world.co_tenant.pk,
        }
        assert not archived.filter(user=newcomer).exists()
        with pytest.raises(NotFound):
            AnnouncementService.get_visible(
                actor=world.tenant, prop=world.prop, announcement_id=announcement.pk
            )

    def test_scheduled_and_expired_are_hidden_from_owners_and_tenants(self, world):
        now = timezone.now()
        publish(world, [PropertyRole.TENANT], published_at=now + dt.timedelta(days=1))
        publish(
            world,
            [PropertyRole.TENANT],
            published_at=now - dt.timedelta(days=5),
            expires_at=now - dt.timedelta(days=1),
        )
        assert visible(world, world.tenant) == []
        assert len(visible(world, world.manager)) == 1  # scheduled one; expired hidden by default


class TestRules:
    def test_owners_and_tenants_cannot_publish(self, world):
        with pytest.raises(PermissionDenied):
            publish(world, [PropertyRole.TENANT], actor=world.owner)

    def test_target_roles_are_frozen(self, world):
        announcement = publish(world, [PropertyRole.TENANT])
        with pytest.raises(InvalidInput):
            AnnouncementService.update(
                actor=world.manager, announcement=announcement, changes={"target_roles": ["owner"]}
            )

    def test_feature_gating(self, world):
        PropertyService.set_features(
            actor=world.admin, prop=world.prop, features={Feature.ANNOUNCEMENTS: False}
        )
        with pytest.raises(FeatureDisabled):
            publish(world, [PropertyRole.TENANT])

    def test_attachments(self, world):
        from apps.common.attachments.rules import EntityType
        from apps.common.attachments.service import AttachmentService

        announcement = publish(world, [PropertyRole.TENANT], files=[f.pdf()])
        assert AttachmentService.count(EntityType.ANNOUNCEMENT, announcement.pk) == 1
