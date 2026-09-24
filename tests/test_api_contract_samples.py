"""Capture real API responses to check the TypeScript/Zod contracts against them.

Skipped unless CONTRACT_SAMPLES names the output file:

    CONTRACT_SAMPLES=api-contracts/tests/samples.json pytest tests/test_api_contract_samples.py
    cd api-contracts && npm test

Every GET endpoint of the schema is called on a world holding one record of
each kind; each JSON answer is stored with its method, path and status, and
the Node test parses it with the matching `endpoints[...].response` schema.
"""

import datetime as dt
import json
import os
import re
from decimal import Decimal

import pytest
from django.utils import timezone
from drf_spectacular.generators import SchemaGenerator

from apps.accounts.enums import PropertyRole
from apps.amenities.services import AmenityService, BookingService
from apps.announcements.models import AnnouncementCategory
from apps.announcements.services import AnnouncementService
from apps.chat.services import ChatService
from apps.events.services import EventService
from apps.library.services import DocumentService, FolderService
from apps.marketplace.models import ListingCategory
from apps.marketplace.services import ListingService
from apps.properties.models import UnitOwnership
from apps.service_requests.models import ServiceRequestCategory
from apps.service_requests.services import ServiceRequestService
from apps.short_term_rental.services import ShortTermRentalMemberInput, ShortTermRentalService
from apps.store.services import OrderLine, OrderService, ProductService
from apps.surveys.services import QuestionInput, SurveyService
from apps.visitors.services import VisitorService
from apps.work_orders.services import WorkOrderService
from tests import factories as f

pytestmark = pytest.mark.django_db
OUTPUT = os.environ.get("CONTRACT_SAMPLES")

# The two configuration pages only answer at their own step; every other
# endpoint gets the "dashboard" default the `api` fixture applies.
STEP_OF_PATH = {
    "/api/v1/ui-config/syndicats/": "syndicat",
    "/api/v1/ui-config/properties/": "property",
}


def _seed(world) -> dict:
    """One record of each kind, and the ids used to fill the URLs."""
    now = timezone.now()
    announcement = AnnouncementService.publish(
        actor=world.manager,
        prop=world.prop,
        title="Water cut",
        body="Tomorrow.",
        target_roles=[PropertyRole.TENANT],
        category=AnnouncementCategory.MAINTENANCE,
        files=[f.pdf()],
    )
    event = EventService.create(
        actor=world.manager,
        prop=world.prop,
        title="BBQ",
        start_at=now + dt.timedelta(days=3),
        end_at=now + dt.timedelta(days=3, hours=3),
        target_roles=[PropertyRole.OWNER, PropertyRole.TENANT],
    )
    amenity = AmenityService.create(
        actor=world.manager,
        prop=world.prop,
        data={
            "name": "Gym",
            "requires_approval": False,
            "min_duration_minutes": 30,
            "max_duration_minutes": 180,
        },
    )
    start = (now + dt.timedelta(days=1)).replace(hour=10, minute=0, second=0, microsecond=0)
    booking = BookingService.book(
        actor=world.tenant, amenity=amenity, start=start, end=start + dt.timedelta(hours=1)
    )
    request = ServiceRequestService.submit(
        actor=world.tenant,
        prop=world.prop,
        unit=world.unit,
        title="Leak",
        description="Kitchen sink",
        category=ServiceRequestCategory.PLUMBING,
        files=[f.png()],
    )
    ServiceRequestService.assign(actor=world.manager, sr=request, resolvers=[world.maintenance])
    room = ChatService.open_room(actor=world.tenant, kind="service_request", object_id=request.pk)
    message = ChatService.post(actor=world.tenant, room=room, body="Still leaking")
    work_order = WorkOrderService.create(actor=world.manager, prop=world.prop, title="Repaint hall")
    visitor = VisitorService.register(
        actor=world.security, unit=world.unit, first_name="Sam", last_name="Lee"
    )
    rental = ShortTermRentalService.declare(
        actor=world.tenant,
        unit=world.unit,
        checkin_date=timezone.localdate() + dt.timedelta(days=2),
        checkout_date=timezone.localdate() + dt.timedelta(days=4),
        members=[ShortTermRentalMemberInput("Ana", "Diaz")],
    )
    survey = SurveyService.create_draft(
        actor=world.manager,
        prop=world.prop,
        title="Lobby",
        target_roles=[PropertyRole.OWNER],
        questions=[QuestionInput("Repaint the lobby?", ["Yes", "No"])],
    )
    folder = FolderService.create(
        actor=world.manager, prop=world.prop, en_name="Rules", fr_name="Règles"
    )
    document = DocumentService.publish(
        actor=world.manager,
        folder=folder,
        title="Bylaws",
        target_roles=[PropertyRole.OWNER],
        upload=f.pdf(),
    )
    listing = ListingService.publish(
        actor=world.tenant,
        prop=world.prop,
        images=[f.png()],
        data={
            "category": ListingCategory.VARIOUS_OFFER,
            "title": "Bike",
            "description": "Good",
            "price": Decimal("50.00"),
        },
    )
    product = ProductService.create(
        actor=world.admin,
        prop=world.prop,
        data={"name": "Water pack", "price": Decimal("4.50"), "stock_quantity": 10},
    )
    order = OrderService.place(
        actor=world.tenant, prop=world.prop, lines=[OrderLine(product.pk, 2)], unit=world.unit
    )
    return {
        "syndicat_id": world.syndicat.pk,
        "property_id": world.prop.pk,
        "building_id": world.building.pk,
        "unit_id": world.unit.pk,
        "lease_id": world.lease.pk,
        "member_id": world.lease.members.first().pk,
        "user_id": world.tenant.pk,
        "promoter_id": world.prop.promoter_id,
        "ownership_id": UnitOwnership.objects.filter(unit=world.unit).first().pk,
        "announcement_id": announcement.pk,
        "event_id": event.pk,
        "amenity_id": amenity.pk,
        "booking_id": booking.pk,
        "request_id": request.pk,
        "room_id": room.pk,
        "message_id": message.pk,
        "work_order_id": work_order.pk,
        "visitor_id": visitor.pk,
        "short_term_rental_id": rental.pk,
        "short_term_rental_member_id": rental.members.first().pk,
        "survey_id": survey.pk,
        "folder_id": folder.pk,
        "document_id": document.pk,
        "listing_id": listing.pk,
        "product_id": product.pk,
        "order_id": order.pk,
        # Query window of the amenity schedule.
        "start": start.isoformat(),
        "end": (start + dt.timedelta(days=2)).isoformat(),
    }


def _fill(path: str, ids: dict) -> str | None:
    names = re.findall(r"{(\w+)}", path)
    if any(name not in ids for name in names):
        return None
    return re.sub(r"{(\w+)}", lambda m: str(ids[m.group(1)]), path)


@pytest.mark.skipif(not OUTPUT, reason="set CONTRACT_SAMPLES=<file> to capture API samples")
def test_capture_api_samples(api, world):
    ids = _seed(world)
    schema = SchemaGenerator().get_schema(request=None, public=True)
    samples, skipped = [], []
    for path, methods in schema["paths"].items():
        operation = methods.get("get")
        url = _fill(path, ids) if operation else None
        if url is None:
            continue
        query = {
            p["name"]: ids[p["name"]]
            for p in operation.get("parameters", [])
            if p["in"] == "query" and p.get("required") and p["name"] in ids
        }
        # Owners and tenants see what the admin sees for their own records;
        # the admin reaches every endpoint.
        client = api(
            world.admin, syndicat=world.syndicat, prop=world.prop, step=STEP_OF_PATH.get(path)
        )
        response = client.get(url, query)
        if response.status_code == 200 and response["Content-Type"].startswith("application/json"):
            samples.append({"method": "GET", "path": path, "status": 200, "body": response.json()})
        else:
            skipped.append(f"{path} -> {response.status_code}")
    # Logging in answers with the session; the tokens are not worth keeping.
    login = api().post(
        "/api/v1/auth/token/",
        {"email": world.tenant.email, "password": "Str0ng-Passw0rd!"},
        format="json",
    )
    session = login.json()
    session["credentials"] = dict.fromkeys(session["credentials"], "<redacted>")
    samples.append(
        {"method": "POST", "path": "/api/v1/auth/token/", "status": 200, "body": session}
    )
    with open(OUTPUT, "w") as handle:
        json.dump({"samples": samples, "skipped": skipped}, handle, indent=1, default=str)
    assert len(samples) > 50
