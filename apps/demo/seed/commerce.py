"""Shared amenities and their bookings, the residence store, and the marketplace."""

from __future__ import annotations

import datetime as dt
from decimal import Decimal
from zoneinfo import ZoneInfo

from apps.amenities.models import Booking
from apps.amenities.services import AmenityService, BookingService
from apps.chat.services import ChatService
from apps.common.exceptions import BusinessRuleViolation
from apps.demo import content, media
from apps.demo.seed.base import Demo, Residence
from apps.marketplace.models import MarketplaceListing
from apps.marketplace.services import ListingService
from apps.store.models import Order
from apps.store.services import OrderLine, OrderService, ProductService

BOOKINGS_PER_AMENITY = 12
ORDERS_PER_RESIDENCE = 30
LISTINGS_PER_RESIDENCE = 16


def seed(demo: Demo) -> None:
    for residence in demo.residences:
        _amenities(demo, residence)
        _bookings(demo, residence)
        _store(demo, residence)
        _marketplace(demo, residence)
        demo.log(f"  {residence.prop.name}: équipements, réservations, boutique, annonces")


# ------------------------------------------------------------------ amenities


def _amenities(demo: Demo, residence: Residence) -> None:
    for index, spec in enumerate(content.AMENITIES):
        data = dict(spec)
        data["opening_time"] = dt.time.fromisoformat(data["opening_time"])
        data["closing_time"] = dt.time.fromisoformat(data["closing_time"])
        for money in ("fee", "security_fee", "hourly_price"):
            if money in data:
                data[money] = Decimal(data[money])
        amenity = AmenityService.create(actor=residence.manager, prop=residence.prop, data=data)
        AmenityService.add_images(
            actor=residence.manager,
            amenity=amenity,
            files=[
                media.png(f"{spec['name']}-{n}.png", (40 + 50 * index, 140, 200 - 30 * n))
                for n in range(2)
            ],
        )
        residence.amenities.append(amenity)


def _slot(demo: Demo, amenity, zone: ZoneInfo) -> tuple[dt.datetime, dt.datetime]:
    """A slot inside the opening hours, on the property's clocks."""
    minutes = demo.rng.randrange(amenity.min_duration_minutes, amenity.max_duration_minutes + 1, 30)
    day = demo.today + dt.timedelta(days=demo.rng.randint(1, min(amenity.max_advance_days - 1, 14)))
    latest = amenity.closing_time.hour * 60 - minutes
    start_minute = demo.rng.randrange(
        amenity.opening_time.hour * 60, max(latest, amenity.opening_time.hour * 60) + 1, 30
    )
    start = dt.datetime.combine(day, dt.time(start_minute // 60, start_minute % 60), tzinfo=zone)
    return start, start + dt.timedelta(minutes=minutes)


def _bookings(demo: Demo, residence: Residence) -> None:
    zone = ZoneInfo(residence.prop.timezone)
    residents = residence.residents
    for amenity in residence.amenities:
        made = []
        for _ in range(BOOKINGS_PER_AMENITY):
            start, end = _slot(demo, amenity, zone)
            try:
                booking = BookingService.book(
                    actor=demo.rng.choice(residents),
                    amenity=amenity,
                    start=start,
                    end=end,
                    party_size=demo.rng.randint(1, min(4, amenity.capacity)),
                    note=demo.rng.choice(
                        ["", "Anniversaire de ma fille.", "Séance avec un coach."]
                    ),
                )
            except BusinessRuleViolation:
                continue  # the slot is taken on an exclusive amenity
            made.append(booking)
        for index, booking in enumerate(made):
            if amenity.requires_approval and index % 4 != 3:
                BookingService.decide(
                    actor=residence.manager,
                    booking=booking,
                    approve=index % 5 != 0,
                    note="Merci de restituer la salle propre."
                    if index % 5
                    else "Salle indisponible (travaux).",
                )
            if index % 3 == 0:  # a third took place in the past
                shift = dt.timedelta(days=demo.rng.randint(16, 90))
                Booking.objects.filter(pk=booking.pk).update(
                    start_datetime=booking.start_datetime - shift,
                    end_datetime=booking.end_datetime - shift,
                    created_at=booking.start_datetime - shift - dt.timedelta(days=5),
                )
            elif index % 7 == 1:
                booking.refresh_from_db()
                if booking.status in ("PENDING", "CONFIRMED"):
                    BookingService.cancel(
                        actor=booking.booker, booking=booking, reason="Empêchement."
                    )
        if made and demo.chance(0.5):
            first = made[-1]
            room = ChatService.open_room(actor=first.booker, kind="booking", object_id=first.pk)
            ChatService.post(
                actor=first.booker, room=room, body="Bonjour, peut-on arriver 15 minutes plus tôt ?"
            )
            ChatService.post(actor=residence.manager, room=room, body="Oui, la salle sera ouverte.")
    BookingService.complete_past(prop=residence.prop)


# ------------------------------------------------------------------ store


def _store(demo: Demo, residence: Residence) -> None:
    for index, (name, category, price) in enumerate(content.PRODUCTS):
        product = ProductService.create(
            actor=demo.admin,
            prop=residence.prop,
            data={
                "name": name,
                "category": category,
                "price": Decimal(price),
                "stock_quantity": demo.rng.randint(20, 120),
                "sku": f"SKU-{residence.prop.pk}-{index + 1:03d}",
                "description": f"{name}, livré à votre porte par la conciergerie.",
            },
        )
        if index % 3 == 0:
            ProductService.add_images(
                actor=demo.admin, product=product, files=[media.png("produit.png", (230, 170, 60))]
            )
        residence.products.append(product)
    homes = [
        (unit, person)
        for unit in residence.occupied_units()
        for person in residence.occupants[unit.pk]
    ]
    for index in range(ORDERS_PER_RESIDENCE):
        unit, person = demo.rng.choice(homes)
        products = demo.rng.sample(residence.products, k=demo.rng.randint(1, 4))
        order = OrderService.place(
            actor=person,
            prop=residence.prop,
            unit=unit,
            lines=[OrderLine(p.pk, demo.rng.randint(1, 3)) for p in products],
            delivery_instructions=demo.rng.choice(["", "Laisser à la loge.", "Sonner deux fois."]),
            customer_note="",
        )
        outcome = index % 6
        if outcome in (1, 2, 3):
            OrderService.confirm(actor=demo.admin, order=order, note="Préparation en cours.")
        if outcome in (2, 3):
            OrderService.deliver(actor=demo.admin, order=order, note="Remis en main propre.")
        if outcome == 4:
            OrderService.cancel(actor=person, order=order, reason="Commande passée par erreur.")
        Order.objects.filter(pk=order.pk).update(created_at=demo.days_ago(0, 60))
        if index == 0:
            room = ChatService.open_room(actor=person, kind="order", object_id=order.pk)
            ChatService.post(actor=person, room=room, body="Pouvez-vous livrer avant 18h ?")


# ------------------------------------------------------------------ marketplace


def _marketplace(demo: Demo, residence: Residence) -> None:
    for index in range(LISTINGS_PER_RESIDENCE):
        category, title, description, price = content.LISTINGS[index % len(content.LISTINGS)]
        seller = demo.rng.choice(residence.residents)
        listing = ListingService.publish(
            actor=seller,
            prop=residence.prop,
            data={
                "category": category,
                "title": title,
                "description": description,
                "price": Decimal(price) if price else None,
                "currency": "MAD",
                "is_negotiable": demo.chance(0.5),
                "location": residence.prop.city,
                "contact_phone": seller.phone,
            },
            images=[
                media.png(f"annonce-{n}.png", (150, 100 + 30 * n, 180))
                for n in range(demo.rng.randint(1, 3))
            ],
        )
        MarketplaceListing.objects.filter(pk=listing.pk).update(published_at=demo.days_ago(0, 90))
        if index % 5 == 3:
            ListingService.mark_sold(actor=seller, listing=listing)
        elif index % 7 == 5:
            ListingService.archive(actor=seller, listing=listing)
