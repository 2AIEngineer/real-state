"""Deletion policy, module by module.

Configuration and content can be removed while unused; anything carrying
history is refused with `resource_in_use` (or a more precise code) and keeps
its deactivate/cancel path instead.
"""

import datetime as dt
from decimal import Decimal

import pytest
from django.utils import timezone

from apps.amenities.services import AmenityService, BookingService
from apps.common.exceptions import BusinessRuleViolation, NotFound, PermissionDenied
from apps.common.files.rules import EntityType
from apps.common.models import Attachment
from apps.leasing.models import CheckPhase, ComponentCondition
from apps.leasing.services import LeaseComponentStateService
from apps.library.models import Folder
from apps.marketplace.models import ListingCategory
from apps.marketplace.services import ListingService
from apps.properties.models import Building, Promoter, Property, Syndicat, Unit, UnitOwnership
from apps.properties.services import (
    Acquirer,
    BuildingService,
    OwnershipService,
    PromoterService,
    PropertyService,
    SyndicatService,
    UnitService,
)
from apps.store.models import Product
from apps.store.services import OrderLine, OrderService, ProductService
from apps.surveys.models import Survey
from apps.surveys.services import ParticipationService, QuestionInput, SurveyService
from apps.visitors.models import Visitor
from apps.visitors.services import VisitorService
from tests import factories as f

pytestmark = pytest.mark.django_db
TODAY = dt.date.today()


class TestReferential:
    def test_empty_building_is_deleted(self, world):
        building = f.make_building(world.prop, name="Empty")
        BuildingService.delete(actor=world.manager, building=building)
        assert not Building.objects.filter(pk=building.pk).exists()

    def test_building_with_units_is_refused(self, world):
        with pytest.raises(BusinessRuleViolation) as exc:
            BuildingService.delete(actor=world.manager, building=world.building)
        assert exc.value.code == "resource_in_use" and "Units" in exc.value.details

    def test_unit_never_used_is_deleted_with_its_promoter_ownership(self, world):
        unit = f.make_unit(world.building, world.manager, number="TMP")
        UnitService.delete(actor=world.manager, unit=unit)
        assert not Unit.objects.filter(pk=unit.pk).exists()
        assert not UnitOwnership.objects.filter(unit_id=unit.pk).exists()

    def test_unit_that_was_sold_keeps_its_ledger(self, world):
        with pytest.raises(BusinessRuleViolation) as exc:
            UnitService.delete(actor=world.manager, unit=world.unit)
        assert exc.value.code == "unit_has_ownership_history"

    def test_unit_with_a_lease_is_refused(self, world):
        unit = f.make_unit(world.building, world.manager, number="LEASED")
        f.make_lease(unit, [f.make_user()], world.manager)
        with pytest.raises(BusinessRuleViolation) as exc:
            UnitService.delete(actor=world.manager, unit=unit)
        assert exc.value.code == "unit_has_leases"

    def test_property_deletion_takes_its_default_library_folders(self, world):
        prop = PropertyService.create(
            actor=world.admin,
            syndicat=world.syndicat,
            promoter=f.make_promoter(),
            data={"name": "Ghost"},
        )
        assert Folder.objects.filter(property=prop).count() == 6
        PropertyService.delete(actor=world.admin, prop=prop)
        assert not Property.objects.filter(pk=prop.pk).exists()
        assert not Folder.objects.filter(property_id=prop.pk).exists()

    def test_property_with_buildings_is_refused(self, world):
        with pytest.raises(BusinessRuleViolation) as exc:
            PropertyService.delete(actor=world.admin, prop=world.prop)
        assert exc.value.code == "resource_in_use"

    def test_only_admins_delete_a_property(self, world):
        with pytest.raises(PermissionDenied):
            PropertyService.delete(actor=world.syndic, prop=world.prop)

    def test_empty_syndicat_is_deleted(self, world):
        syndicat = f.make_syndicat()
        SyndicatService.delete(actor=world.admin, syndicat=syndicat)
        assert not Syndicat.objects.filter(pk=syndicat.pk).exists()

    def test_syndicat_with_properties_is_refused(self, world):
        with pytest.raises(BusinessRuleViolation) as exc:
            SyndicatService.delete(actor=world.admin, syndicat=world.syndicat)
        assert exc.value.code == "resource_in_use" and "Properties" in exc.value.details

    def test_promoter_deletion_takes_its_technical_account(self, world):
        promoter = f.make_promoter()
        representative = promoter.representative_user
        PromoterService.delete(actor=world.admin, promoter=promoter)
        assert not Promoter.objects.filter(pk=promoter.pk).exists()
        assert not type(representative).objects.filter(pk=representative.pk).exists()

    def test_promoter_of_a_property_is_refused(self, world):
        with pytest.raises(BusinessRuleViolation):
            PromoterService.delete(actor=world.admin, promoter=world.prop.promoter)


class TestFeatureModules:
    def test_amenity_without_booking_is_deleted_with_its_images(self, world):
        amenity = AmenityService.create(
            actor=world.manager, prop=world.prop, data={"name": "Sauna"}
        )
        AmenityService.add_images(actor=world.manager, amenity=amenity, files=[f.png()])
        AmenityService.delete(actor=world.manager, amenity=amenity)
        assert not Attachment.objects.filter(
            entity_type=EntityType.AMENITY, entity_id=amenity.pk
        ).exists()

    def test_booked_amenity_is_refused_and_points_to_deactivation(self, world):
        amenity = AmenityService.create(
            actor=world.manager, prop=world.prop, data={"name": "Gym", "requires_approval": False}
        )
        start = timezone.now() + dt.timedelta(days=1)
        BookingService.book(
            actor=world.tenant, amenity=amenity, start=start, end=start + dt.timedelta(hours=1)
        )
        with pytest.raises(BusinessRuleViolation) as exc:
            AmenityService.delete(actor=world.manager, amenity=amenity)
        assert exc.value.code == "resource_in_use" and "inactive" in exc.value.message

    def test_product_never_ordered_is_deleted(self, world):
        product = ProductService.create(
            actor=world.admin, prop=world.prop, data={"name": "Mug", "price": Decimal("2")}
        )
        ProductService.delete(actor=world.admin, product=product)
        assert not Product.objects.filter(pk=product.pk).exists()

    def test_ordered_product_is_refused(self, world):
        product = ProductService.create(
            actor=world.admin,
            prop=world.prop,
            data={"name": "Mug", "price": Decimal("2"), "stock_quantity": 3},
        )
        OrderService.place(actor=world.tenant, prop=world.prop, lines=[OrderLine(product.pk, 1)])
        with pytest.raises(BusinessRuleViolation):
            ProductService.delete(actor=world.admin, product=product)

    def test_survey_without_answer_is_deleted(self, world):
        survey = SurveyService.create_draft(
            actor=world.manager,
            prop=world.prop,
            title="S",
            target_roles=["owner"],
            questions=[QuestionInput("Q", ["A", "B"])],
        )
        SurveyService.delete(actor=world.manager, survey=survey)
        assert not Survey.objects.filter(pk=survey.pk).exists()

    def test_answered_survey_is_refused(self, world):
        survey = SurveyService.create_draft(
            actor=world.manager,
            prop=world.prop,
            title="S",
            target_roles=["owner"],
            questions=[QuestionInput("Q", ["A", "B"])],
        )
        SurveyService.publish(actor=world.manager, survey=survey)
        question = survey.questions.get()
        ParticipationService.respond(
            actor=world.owner, survey=survey, answers={question.pk: question.options.first().pk}
        )
        with pytest.raises(BusinessRuleViolation) as exc:
            SurveyService.delete(actor=world.manager, survey=survey)
        assert exc.value.code == "survey_has_responses"

    def test_seller_deletes_their_listing_but_not_someone_elses(self, world):
        listing = ListingService.publish(
            actor=world.tenant,
            data={"category": ListingCategory.VARIOUS_OFFER, "title": "Bike", "description": "d"},
            images=[f.png()],
            prop=world.prop,
        )
        with pytest.raises(PermissionDenied):
            ListingService.delete(actor=world.owner, listing=listing)
        ListingService.delete(actor=world.tenant, listing=listing)
        assert not Attachment.objects.filter(
            entity_type=EntityType.MARKETPLACE_LISTING, entity_id=listing.pk
        ).exists()

    def test_visitor_entry_is_deleted_by_management_only(self, world):
        visitor = VisitorService.register(
            actor=world.security, unit=world.unit, first_name="A", last_name="B"
        )
        with pytest.raises(PermissionDenied):
            VisitorService.delete(actor=world.security, visitor=visitor)
        VisitorService.delete(actor=world.manager, visitor=visitor)
        assert not Visitor.objects.filter(pk=visitor.pk).exists()

    def test_inspection_line_is_deleted(self, world):
        component = LeaseComponentStateService.record(
            actor=world.manager,
            lease=world.lease,
            name="Oven",
            state=ComponentCondition.GOOD,
            on_check=CheckPhase.IN,
            on_check_date=TODAY,
            files=[f.png()],
        )
        LeaseComponentStateService.delete(actor=world.manager, component=component)
        assert not world.lease.lease_component_states.exists()
        assert not Attachment.objects.filter(
            entity_type=EntityType.LEASE_COMPONENT_STATE, entity_id=component.pk
        ).exists()


def test_delete_over_http_returns_204_then_404(api, world):
    client = api(world.manager, world.syndicat, world.prop)
    building = f.make_building(world.prop, name="Temp")
    assert client.delete(f"/api/v1/buildings/{building.pk}/").status_code == 204
    assert client.delete(f"/api/v1/buildings/{building.pk}/").status_code == 404


def test_delete_in_use_over_http_is_409(api, world):
    response = api(world.manager, world.syndicat, world.prop).delete(
        f"/api/v1/buildings/{world.building.pk}/"
    )
    assert response.status_code == 409 and response.json()["error"]["code"] == "resource_in_use"


class TestTransactionalRecords:
    """Records kept for their history can still be erased for good: demo data
    must not pollute a production database forever."""

    def test_service_request_takes_its_rounds_conversation_and_notifications(self, world):
        from apps.chat.models import ChatMessage, ChatRoom
        from apps.chat.services import ChatService
        from apps.notifications.models import InboxNotification
        from apps.service_requests.models import ServiceRequest, ServiceRequestCategory
        from apps.service_requests.services import RoundService, ServiceRequestService

        sr = ServiceRequestService.submit(
            actor=world.tenant,
            prop=world.prop,
            unit=world.unit,
            title="Demo",
            description="d",
            category=ServiceRequestCategory.OTHER,
            files=[f.png()],
        )
        RoundService.assign(actor=world.manager, sr=sr, resolvers=[world.maintenance])
        RoundService.resolve(actor=world.maintenance, sr=sr, files=[f.png()])
        room = ChatService.open_room(actor=world.tenant, kind="service_request", object_id=sr.pk)
        ChatService.post(actor=world.tenant, room=room, media=f.pdf())
        assert InboxNotification.objects.filter(
            object_id=sr.pk, content_type__model="servicerequest"
        ).exists()

        ServiceRequestService.delete(actor=world.manager, sr=sr)
        assert not ServiceRequest.objects.filter(pk=sr.pk).exists()
        assert not ChatRoom.objects.filter(pk=room.pk).exists() and not ChatMessage.objects.exists()
        assert not InboxNotification.objects.filter(
            object_id=sr.pk, content_type__model="servicerequest"
        ).exists()
        assert not Attachment.objects.filter(
            entity_type__in=[
                EntityType.SERVICE_REQUEST,
                EntityType.SERVICE_REQUEST_RESOLUTION,
                EntityType.CHAT_MESSAGE,
            ]
        ).exists()

    def test_lease_deletion_takes_members_and_inspections(self, world):
        from apps.leasing.models import Lease, LeaseMember
        from apps.leasing.services import LeaseService

        LeaseComponentStateService.record(
            actor=world.manager,
            lease=world.lease,
            name="Door",
            state=ComponentCondition.GOOD,
            on_check=CheckPhase.IN,
            on_check_date=TODAY,
            files=[f.png()],
        )
        LeaseService.delete(actor=world.syndic, lease=world.lease)
        assert not Lease.objects.filter(pk=world.lease.pk).exists()
        assert not LeaseMember.objects.filter(lease_id=world.lease.pk).exists()
        assert not Attachment.objects.filter(entity_type=EntityType.LEASE_COMPONENT_STATE).exists()

    def test_lease_with_a_short_term_rental_is_refused_first(self, world):
        from apps.leasing.services import LeaseService
        from apps.short_term_rental.services import (
            ShortTermRentalMemberInput,
            ShortTermRentalService,
        )

        rental = ShortTermRentalService.declare(
            actor=world.tenant,
            unit=world.unit,
            checkin_date=TODAY + dt.timedelta(days=1),
            checkout_date=TODAY + dt.timedelta(days=3),
            members=[ShortTermRentalMemberInput("A", "B")],
        )
        with pytest.raises(BusinessRuleViolation) as exc:
            LeaseService.delete(actor=world.syndic, lease=world.lease)
        assert exc.value.code == "resource_in_use"
        ShortTermRentalService.delete(actor=world.manager, rental=rental)
        LeaseService.delete(actor=world.syndic, lease=world.lease)

    def test_manager_cannot_delete_a_lease(self, world):
        from apps.leasing.services import LeaseService

        with pytest.raises(PermissionDenied):
            LeaseService.delete(actor=world.manager, lease=world.lease)

    def test_order_deletion_puts_the_stock_back(self, world):
        from apps.store.models import Order
        from apps.store.services import OrderLine, OrderService, ProductService

        product = ProductService.create(
            actor=world.admin,
            prop=world.prop,
            data={"name": "Demo", "price": Decimal("5"), "stock_quantity": 10},
        )
        order = OrderService.place(
            actor=world.tenant, prop=world.prop, lines=[OrderLine(product.pk, 4)]
        )
        assert Product.objects.get(pk=product.pk).stock_quantity == 6
        OrderService.delete(actor=world.admin, order=order)
        assert not Order.objects.filter(pk=order.pk).exists()
        assert Product.objects.get(pk=product.pk).stock_quantity == 10

    def test_booking_and_work_order_deletion(self, world):
        from apps.amenities.models import Booking
        from apps.amenities.services import AmenityService, BookingService
        from apps.work_orders.models import WorkOrder
        from apps.work_orders.services import WorkOrderService

        amenity = AmenityService.create(
            actor=world.manager,
            prop=world.prop,
            data={"name": "Demo room", "requires_approval": False},
        )
        start = timezone.now() + dt.timedelta(days=2)
        booking = BookingService.book(
            actor=world.tenant, amenity=amenity, start=start, end=start + dt.timedelta(hours=1)
        )
        BookingService.delete(actor=world.manager, booking=booking)
        assert not Booking.objects.filter(pk=booking.pk).exists()

        wo = WorkOrderService.create(
            actor=world.manager, prop=world.prop, title="Demo", files=[f.png()]
        )
        WorkOrderService.delete(actor=world.manager, wo=wo)
        assert not WorkOrder.objects.filter(pk=wo.pk).exists()
        assert not Attachment.objects.filter(entity_type=EntityType.WORK_ORDER).exists()

    def test_short_term_rental_deletion_takes_member_documents(self, world):
        from apps.short_term_rental.models import ShortTermRental, ShortTermRentalMember
        from apps.short_term_rental.services import (
            ShortTermRentalMemberInput,
            ShortTermRentalMemberService,
            ShortTermRentalService,
        )

        rental = ShortTermRentalService.declare(
            actor=world.tenant,
            unit=world.unit,
            checkin_date=TODAY + dt.timedelta(days=5),
            checkout_date=TODAY + dt.timedelta(days=7),
            members=[ShortTermRentalMemberInput("A", "B")],
        )
        ShortTermRentalMemberService.set_id_card(
            actor=world.tenant, member=rental.members.get(), upload=f.png()
        )
        assert Attachment.objects.filter(
            entity_type=EntityType.SHORT_TERM_RENTAL_MEMBER_ID_CARD
        ).exists()
        ShortTermRentalService.delete(actor=world.manager, rental=rental)
        assert (
            not ShortTermRental.objects.filter(pk=rental.pk).exists()
            and not ShortTermRentalMember.objects.exists()
        )
        assert not Attachment.objects.filter(
            entity_type=EntityType.SHORT_TERM_RENTAL_MEMBER_ID_CARD
        ).exists()

    def test_announcement_archiving_then_deletion(self, world):
        from apps.announcements.models import Announcement
        from apps.announcements.services import AnnouncementService
        from apps.notifications.models import InboxNotification, RecipientSnapshot

        announcement = AnnouncementService.publish(
            actor=world.manager,
            prop=world.prop,
            title="Demo",
            body="b",
            target_roles=["tenant"],
            category="general",
            files=[f.pdf()],
        )
        AnnouncementService.archive(actor=world.manager, announcement=announcement)
        assert Announcement.objects.filter(pk=announcement.pk).exists()  # kept for the audit trail

        with pytest.raises(PermissionDenied):
            AnnouncementService.delete(actor=world.manager, announcement=announcement)
        AnnouncementService.delete(actor=world.syndic, announcement=announcement)
        assert not Announcement.objects.filter(pk=announcement.pk).exists()
        assert not RecipientSnapshot.objects.filter(
            object_id=announcement.pk, content_type__model="announcement"
        ).exists()
        assert not InboxNotification.objects.filter(
            object_id=announcement.pk, content_type__model="announcement"
        ).exists()
        assert not Attachment.objects.filter(entity_type=EntityType.ANNOUNCEMENT).exists()

    def test_chat_message_deletion(self, world):
        from apps.chat.models import ChatMessage
        from apps.chat.services import ChatService
        from apps.service_requests.services import RoundService, ServiceRequestService

        sr = ServiceRequestService.submit(
            actor=world.tenant, prop=world.prop, title="d", description="d", category="other"
        )
        RoundService.assign(actor=world.manager, sr=sr, resolvers=[world.maintenance])
        room = ChatService.open_room(actor=world.tenant, kind="service_request", object_id=sr.pk)
        message = ChatService.post(actor=world.tenant, room=room, body="oops", media=f.png())

        with pytest.raises(NotFound):  # not a participant at all
            ChatService.delete_message(actor=world.co_tenant, message=message)
        with pytest.raises(PermissionDenied):  # participant, but not the sender
            ChatService.delete_message(actor=world.maintenance, message=message)
        ChatService.delete_message(actor=world.tenant, message=message)
        assert not ChatMessage.objects.filter(pk=message.pk).exists()
        assert not Attachment.objects.filter(entity_type=EntityType.CHAT_MESSAGE).exists()


def test_archive_then_delete_over_http(api, world):
    from apps.announcements.services import AnnouncementService

    announcement = AnnouncementService.publish(
        actor=world.manager,
        prop=world.prop,
        title="Demo",
        body="b",
        target_roles=["tenant"],
        category="general",
    )
    client = api(world.syndic, world.syndicat, world.prop)
    # Taking it off air keeps the record; DELETE erases it.
    assert client.post(f"/api/v1/announcements/{announcement.pk}/archive/").status_code == 200
    assert client.delete(f"/api/v1/announcements/{announcement.pk}/").status_code == 204
    assert client.delete(f"/api/v1/announcements/{announcement.pk}/").status_code == 404


class TestOwnershipLedger:
    def test_a_line_recorded_by_mistake_is_erased(self, world):
        buyer = f.make_user()
        OwnershipService.transfer(
            actor=world.manager, unit=world.unit, acquirers=[Acquirer(buyer)], effective_date=TODAY
        )
        mistake = UnitOwnership.objects.get(unit=world.unit, owner=buyer)
        OwnershipService.delete(actor=world.syndic, ownership=mistake)
        assert not UnitOwnership.objects.filter(pk=mistake.pk).exists()
        # The unit is never left without an owner.
        assert UnitOwnership.objects.filter(
            unit=world.unit, status="ACTIVE", is_promoter_default=True
        ).exists()

    def test_managers_do_not_erase_the_ledger(self, world):
        ownership = UnitOwnership.objects.filter(unit=world.unit, owner=world.owner).first()
        with pytest.raises(PermissionDenied):
            OwnershipService.delete(actor=world.manager, ownership=ownership)


def test_inspections_are_read_through_their_lease(api, world):
    client = api(world.manager, world.syndicat, world.prop)
    created = client.post(
        f"/api/v1/leases/{world.lease.pk}/lease-component-states/",
        {"name": "Oven", "state": "GOOD", "on_check": "IN", "on_check_date": str(TODAY)},
        format="json",
    )
    assert created.status_code == 201
    lease_component_state_id = created.json()["id"]
    other_lease = f.make_lease(world.other_unit, [f.make_user()], world.manager)

    # The same id under another lease does not exist.
    assert (
        client.patch(
            f"/api/v1/leases/{other_lease.pk}/lease-component-states/{lease_component_state_id}/",
            {"state": "BAD"},
            format="json",
        ).status_code
        == 404
    )
    assert (
        client.patch(
            f"/api/v1/leases/{world.lease.pk}/lease-component-states/{lease_component_state_id}/",
            {"state": "BAD"},
            format="json",
        ).status_code
        == 200
    )
    assert (
        client.delete(
            f"/api/v1/leases/{world.lease.pk}/lease-component-states/{lease_component_state_id}/"
        ).status_code
        == 204
    )
