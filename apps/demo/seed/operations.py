"""Daily operations: service requests and their rounds, work orders, visitors,
short-term rentals, and the conversations around requests."""

from __future__ import annotations

import datetime as dt

from apps.chat.services import ChatService
from apps.demo import content, media
from apps.demo.seed.base import Demo, Residence
from apps.properties.models import UnitType
from apps.service_requests.models import RequesterNotice, ServiceRequest
from apps.service_requests.services import Feedback, RoundService, ServiceRequestService
from apps.short_term_rental.models import ShortTermRental, ShortTermRentalStatus
from apps.short_term_rental.services import ShortTermRentalMemberInput, ShortTermRentalService
from apps.visitors.models import Visitor
from apps.visitors.services import VisitorService
from apps.work_orders.models import WorkOrder
from apps.work_orders.services import WorkOrderService

# How the requests of a residence are spread over their lifecycle.
REQUEST_OUTCOMES = (
    ["closed"] * 16
    + ["open"] * 7
    + ["in_progress"] * 7
    + ["resolved"] * 5
    + ["cancelled"] * 3
    + ["reopened"] * 2
)
VISITORS_PER_RESIDENCE = 80
RENTALS_PER_RESIDENCE = 12


def seed(demo: Demo) -> None:
    for residence in demo.residences:
        requests = _service_requests(demo, residence)
        _work_orders(demo, residence, requests)
        _visitors(demo, residence)
        _short_term_rentals(demo, residence)
        demo.log(
            f"  {residence.prop.name}: demandes, ordres de travail, visiteurs, locations courtes"
        )


# ------------------------------------------------------------------ service requests


def _service_requests(demo: Demo, residence: Residence) -> list:
    occupied = residence.occupied_units()
    created = []
    for outcome in REQUEST_OUTCOMES:
        unit = demo.rng.choice(occupied)
        requester = demo.rng.choice(residence.occupants[unit.pk])
        category = demo.rng.choice(list(content.SERVICE_REQUESTS))
        title, description = demo.rng.choice(content.SERVICE_REQUESTS[category])
        whole_property = category in ("common_areas", "security", "suggestion", "information")
        sr = ServiceRequestService.submit(
            actor=requester,
            prop=residence.prop,
            unit=None if whole_property else unit,
            title=title,
            description=description,
            category=category,
            priority=demo.rng.choices(["LOW", "MEDIUM", "HIGH", "URGENT"], weights=[20, 50, 22, 8])[
                0
            ],
            files=[media.png("photo.png", (120, 110, 100))] if demo.chance(0.4) else [],
        )
        _drive(demo, residence, sr, requester, outcome)
        age = {"closed": (20, 200), "cancelled": (10, 120), "resolved": (3, 20)}.get(
            outcome, (0, 12)
        )
        submitted = demo.days_ago(*age)
        ServiceRequest.objects.filter(pk=sr.pk).update(created_at=submitted)
        if demo.chance(0.3):
            _conversation(demo, residence, sr, requester)
        created.append(sr)
    return created


def _drive(demo: Demo, residence: Residence, sr, requester, outcome: str) -> None:
    if outcome == "open":
        return
    if outcome == "cancelled":
        ServiceRequestService.cancel(actor=requester, sr=sr, reason="Problème résolu entre-temps.")
        return
    resolver = demo.rng.choice(residence.maintenance)
    RoundService.assign(actor=residence.manager, sr=sr, resolvers=[resolver])
    if outcome == "in_progress":
        return
    RoundService.resolve(
        actor=resolver,
        sr=sr,
        note=demo.rng.choice(["Joint remplacé.", "Pièce changée et testée.", "Réglage effectué."]),
        files=[media.png("apres-intervention.png", (90, 150, 110))] if demo.chance(0.5) else [],
    )
    if outcome == "resolved":
        return
    if outcome == "reopened":
        RoundService.give_feedback(
            actor=requester,
            sr=sr,
            feedback=Feedback(notice=RequesterNotice.NOT_DONE, comment="Le problème est revenu."),
        )
        RoundService.assign(
            actor=residence.manager, sr=sr, resolvers=[demo.rng.choice(residence.maintenance)]
        )
        return
    RoundService.give_feedback(
        actor=requester,
        sr=sr,
        feedback=Feedback(
            notice=RequesterNotice.DONE,
            rating=demo.rng.choices([3, 4, 5], weights=[15, 40, 45])[0],
            comment=demo.rng.choice(["Merci, intervention rapide.", "Très bien.", ""]),
        ),
    )


def _conversation(demo: Demo, residence: Residence, sr, requester) -> None:
    room = ChatService.open_room(actor=requester, kind="service_request", object_id=sr.pk)
    speakers = [requester, residence.manager]
    for index, line in enumerate(content.CHAT_LINES[: demo.rng.randint(2, 6)]):
        ChatService.post(actor=speakers[index % 2], room=room, body=line)


# ------------------------------------------------------------------ work orders


def _work_orders(demo: Demo, residence: Residence, requests: list) -> None:
    follow_ups = [sr for sr in requests if sr.status != "CANCELLED"][:6]
    specs = [*content.WORK_ORDERS, *content.WORK_ORDERS[:4]]
    for index, (category, title, description) in enumerate(specs):
        source = follow_ups[index] if index < len(follow_ups) else None
        building = (
            source.unit.building if source and source.unit else demo.rng.choice(residence.buildings)
        )
        assignee = demo.rng.choice(
            [*residence.maintenance, *demo.providers[:3], residence.cleaning[building.pk]]
        )
        start = demo.now + dt.timedelta(days=demo.rng.randint(-40, 30))
        wo = WorkOrderService.create(
            actor=residence.manager,
            prop=residence.prop,
            title=source.title if source else title,
            building=building,
            unit=source.unit if source else None,
            service_request=source,
            assignee=assignee,
            data={
                "description": description,
                "category": "corrective" if source else category,
                "priority": demo.rng.choice(["LOW", "MEDIUM", "HIGH"]),
                "scheduled_start": start,
                "scheduled_end": start + dt.timedelta(hours=demo.rng.randint(2, 8)),
                "due_date": (start + dt.timedelta(days=7)).date(),
            },
            files=[media.pdf("devis.pdf", f"Devis — {title}", ["Main d'œuvre et fournitures"])]
            if index % 4 == 0
            else [],
        )
        for action in demo.rng.choice(
            [[], ["start"], ["start", "complete"], ["start", "complete"], ["hold"], ["cancel"]]
        ):
            WorkOrderService.transition(
                actor=residence.manager,
                wo=wo,
                action=action,
                note={
                    "complete": "Travaux réceptionnés.",
                    "cancel": "Reporté au prochain budget.",
                    "hold": "En attente de pièces.",
                }.get(action, ""),
            )
        WorkOrder.objects.filter(pk=wo.pk).update(created_at=start - dt.timedelta(days=5))


# ------------------------------------------------------------------ visitors


def _visitors(demo: Demo, residence: Residence) -> None:
    occupied = residence.occupied_units()
    for _ in range(VISITORS_PER_RESIDENCE):
        unit = demo.rng.choice(occupied)
        guard = residence.security[unit.building_id]
        admitted = demo.chance(0.93)
        visitor = VisitorService.register(
            actor=guard,
            unit=unit,
            first_name=demo.rng.choice(content.FIRST_NAMES_MALE + content.FIRST_NAMES_FEMALE),
            last_name=demo.rng.choice(content.LAST_NAMES),
            admitted=admitted,
            denial_reason="" if admitted else "Résident injoignable, visite non confirmée.",
            details={
                "phone": f"+212 6{demo.rng.randint(10, 99)} {demo.rng.randint(100000, 999999)}",
                "visit_reason": demo.rng.choice(content.VISIT_REASONS),
                "vehicle_plate": f"{demo.rng.randint(1000, 99999)}-A-{demo.rng.randint(1, 80)}"
                if demo.chance(0.3)
                else "",
            },
            id_card=media.png("cni.png", (200, 200, 210)) if demo.chance(0.2) else None,
        )
        arrived = demo.now - dt.timedelta(
            days=demo.rng.randint(0, 30), hours=demo.rng.randint(1, 12)
        )
        if not admitted:
            Visitor.objects.filter(pk=visitor.pk).update(created_at=arrived)
            continue
        Visitor.objects.filter(pk=visitor.pk).update(arrived_at=arrived, created_at=arrived)
        visitor.refresh_from_db()
        if arrived < demo.now - dt.timedelta(hours=3) or demo.chance(0.5):
            VisitorService.mark_left(
                actor=guard,
                visitor=visitor,
                left_at=min(arrived + dt.timedelta(minutes=demo.rng.randint(15, 180)), demo.now),
            )


# ------------------------------------------------------------------ short-term rentals


def _short_term_rentals(demo: Demo, residence: Residence) -> None:
    candidates = _declarers(residence, demo.today)
    for index in range(RENTALS_PER_RESIDENCE):
        if not candidates:
            return
        unit, declarer, earliest, latest = candidates.pop(demo.rng.randrange(len(candidates)))
        checkin = max(earliest, demo.today + dt.timedelta(days=demo.rng.randint(2, 30)))
        checkout = checkin + dt.timedelta(days=demo.rng.randint(2, 7))
        if latest is not None and checkout > latest:
            continue
        rental = ShortTermRentalService.declare(
            actor=declarer,
            unit=unit,
            checkin_date=checkin,
            checkout_date=checkout,
            members=[
                ShortTermRentalMemberInput(
                    demo.rng.choice(content.FIRST_NAMES_FEMALE + content.FIRST_NAMES_MALE),
                    demo.rng.choice(content.LAST_NAMES),
                    {
                        "nationality": demo.rng.choice(
                            ["Marocaine", "Française", "Espagnole", "Belge"]
                        ),
                        "id_document_number": f"{demo.rng.choice('ABCDJK')}{demo.rng.randint(100000, 999999)}",
                        "phone": f"+33 6 {demo.rng.randint(10, 99)} {demo.rng.randint(10, 99)} {demo.rng.randint(10, 99)} {demo.rng.randint(10, 99)}",
                    },
                )
                for _ in range(demo.rng.randint(1, 4))
            ],
            notes="Arrivée prévue en fin d'après-midi.",
        )
        _age_rental(demo, residence, rental, index)


def _declarers(residence: Residence, today: dt.date) -> list:
    """Who may declare a rental on which unit, and between which dates: the
    signatory tenant within their lease, or the owner of a unit not rented out."""
    leased = {lease.unit_id: lease for lease in residence.leases}
    options = []
    for unit in residence.units:
        if unit.unit_type != UnitType.APARTMENT or not residence.occupants.get(unit.pk):
            continue
        lease = leased.get(unit.pk)
        if lease is not None:
            signatory = lease.members.filter(is_signatory=True).first()
            options.append((unit, signatory.user, max(lease.start_date, today), lease.end_date))
        else:
            options.append((unit, residence.occupants[unit.pk][0], today, None))
    return options


def _age_rental(demo: Demo, residence: Residence, rental, index: int) -> None:
    """A third already happened, a few are under way, one was cancelled."""
    if index % 3 == 0:
        checkin = demo.date_ago(20, 150)
        ShortTermRental.objects.filter(pk=rental.pk).update(
            checkin_date=checkin,
            checkout_date=checkin + dt.timedelta(days=demo.rng.randint(2, 6)),
            status=ShortTermRentalStatus.COMPLETED,
            checked_in_at=demo.now - dt.timedelta(days=(demo.today - checkin).days),
            completed_at=demo.now - dt.timedelta(days=(demo.today - checkin).days - 2),
        )
    elif index % 5 == 1:
        ShortTermRental.objects.filter(pk=rental.pk).update(
            checkin_date=demo.today - dt.timedelta(days=1),
            checkout_date=demo.today + dt.timedelta(days=demo.rng.randint(1, 4)),
        )
        rental.refresh_from_db()
        ShortTermRentalService.check_in(
            actor=residence.security[rental.unit.building_id], rental=rental
        )
    elif index % 7 == 2:
        ShortTermRentalService.cancel(
            actor=rental.initiated_by, rental=rental, reason="Séjour annulé par les voyageurs."
        )
