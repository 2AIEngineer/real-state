"""The platform and the referential: staff, promoters, syndicats, properties, buildings, units."""

from __future__ import annotations

import datetime as dt
from decimal import Decimal

from apps.accounts.enums import StructuralRole
from apps.accounts.models import ProviderProfile, UserBuilding, UserProperty, UserSyndicat
from apps.common.attachments.rules import EntityType
from apps.common.attachments.service import AttachmentService
from apps.demo import content, media
from apps.demo.seed.base import Demo, Residence
from apps.properties.models import UnitOwnership, UnitType
from apps.properties.services import (
    BuildingService,
    PromoterService,
    PropertyService,
    SyndicatService,
    UnitService,
)

UNITS_PER_FLOOR = 5
FLOORS = 10  # ground floor + 9: 50 units per building
DELIVERY = dt.date(2019, 6, 1)  # when the promoter handed the units over

PROVIDERS = [
    ("Hydro Services Maroc", "plumbing", "Plomberie, recherche de fuites, débouchage."),
    ("Électro Plus", "electricity", "Électricité générale et tableaux électriques."),
    ("Clim Confort", "hvac", "Installation et entretien de climatisation."),
    ("Ascenseurs du Sud", "elevator", "Maintenance et dépannage d'ascenseurs 24h/24."),
    ("Net & Brillant", "cleaning", "Nettoyage des parties communes et vitrerie."),
    ("Serrurerie Rapide", "locksmith", "Ouverture de portes, blindage, badges."),
]


def seed(demo: Demo) -> None:
    demo.admin = demo.person(StructuralRole.ADMIN, email_hint="admin", is_staff=True)
    _providers(demo)
    promoters = [
        PromoterService.create(
            actor=demo.admin,
            representative_email=f"representant.{index}@promoteurs.demo.urbis.test",
            data=data,
        )
        for index, data in enumerate(content.PROMOTERS, start=1)
    ]
    for index, spec in enumerate(content.SYNDICATS):
        _syndicat(demo, spec, promoters[index % len(promoters)], color=(34 + 60 * index, 90, 160))


def _providers(demo: Demo) -> None:
    for company, service, description in PROVIDERS:
        provider = demo.person(StructuralRole.PROVIDER)
        ProviderProfile.objects.create(
            user=provider,
            company_name=company,
            service_type=service,
            service_description=description,
            address="Zone industrielle, Casablanca",
            business_phone=provider.phone,
            registration_number=f"RC {demo.rng.randint(10000, 99999)}",
        )
        demo.providers.append(provider)


def _syndicat(demo: Demo, spec: dict, promoter, *, color) -> None:
    data = {k: v for k, v in spec.items() if k != "properties"}
    syndicat = SyndicatService.create(actor=demo.admin, data=data)
    AttachmentService.attach_one(
        entity_type=EntityType.SYNDICAT_LOGO,
        entity_id=syndicat.pk,
        upload=media.png("logo-syndic.png", color),
        uploaded_by=demo.admin,
    )
    syndic = demo.person(StructuralRole.SYNDIC)
    UserSyndicat.objects.create(user=syndic, syndicat=syndicat, granted_by=demo.admin)
    demo.syndics.append(syndic)
    for index, prop_spec in enumerate(spec["properties"]):
        _property(
            demo, syndicat, syndic, promoter, prop_spec, color=(color[0], 120 + 50 * index, 90)
        )


def _property(demo: Demo, syndicat, syndic, promoter, spec: dict, *, color) -> None:
    prop = PropertyService.create(
        actor=demo.admin,
        syndicat=syndicat,
        promoter=promoter,
        data={
            "name": spec["name"],
            "description": spec["description"],
            "address": spec["address"],
            "city": spec["city"],
            "country": "Maroc",
            "contact_email": f"loge.{spec['city'].lower()}{len(demo.residences) + 1}@demo.urbis.test",
            "contact_phone": f"+212 5{demo.rng.randint(20, 39)} {demo.rng.randint(10, 99)} "
            f"{demo.rng.randint(10, 99)} {demo.rng.randint(10, 99)}",
            "timezone": "Africa/Casablanca",
        },
    )
    AttachmentService.attach_one(
        entity_type=EntityType.PROPERTY_LOGO,
        entity_id=prop.pk,
        upload=media.png("logo-residence.png", color),
        uploaded_by=demo.admin,
    )
    residence = Residence(prop=prop, syndicat=syndicat, syndic=syndic)
    demo.residences.append(residence)
    for name in spec["buildings"]:
        building = BuildingService.create(
            actor=demo.admin,
            prop=prop,
            data={
                "name": name,
                "address": spec["address"],
                "floors_count": FLOORS,
                "description": f"{name} : {FLOORS} niveaux, deux ascenseurs, local vélos.",
            },
        )
        residence.buildings.append(building)
        _units(demo, residence, building)
    _staff(demo, residence)
    demo.log(f"  {prop.name}: {len(residence.units)} lots")


def _units(demo: Demo, residence: Residence, building) -> None:
    code = building.name.split()[-1][0].upper()
    for floor in range(FLOORS):
        for position in range(1, UNITS_PER_FLOOR + 1):
            unit_type, area, rooms = _unit_profile(demo, floor, position)
            unit = UnitService.create(
                actor=demo.admin,
                building=building,
                data={
                    "number": f"{code}{floor}{position:02d}",
                    "label": {
                        UnitType.COMMERCIAL: "Local commercial",
                        UnitType.OFFICE: "Bureau",
                    }.get(unit_type, f"Appartement T{rooms}"),
                    "floor": floor,
                    "unit_type": unit_type,
                    "area_sqm": area,
                    "rooms_count": rooms,
                },
            )
            residence.units.append(unit)
    # The promoter held every unit from the delivery, not from today.
    UnitOwnership.objects.filter(unit__building=building).update(start_date=DELIVERY)


def _unit_profile(demo: Demo, floor: int, position: int) -> tuple[str, Decimal, int]:
    if floor == 0 and position == 1:
        return UnitType.COMMERCIAL, Decimal(demo.rng.randint(60, 140)), 1
    if floor == 0 and position == 2:
        return UnitType.OFFICE, Decimal(demo.rng.randint(35, 70)), 2
    rooms = demo.rng.choices([1, 2, 3, 4, 5], weights=[10, 30, 35, 18, 7])[0]
    return UnitType.APARTMENT, Decimal(25 + rooms * demo.rng.randint(20, 28)), rooms


def _staff(demo: Demo, residence: Residence) -> None:
    managers = 2 if len(demo.residences) == 1 else 1
    for _ in range(managers):
        manager = demo.person(StructuralRole.MANAGER)
        UserProperty.objects.create(user=manager, property=residence.prop, granted_by=demo.admin)
        residence.managers.append(manager)
    for _ in range(2):
        agent = demo.person(StructuralRole.MAINTENANCE)
        UserProperty.objects.create(user=agent, property=residence.prop, granted_by=demo.admin)
        residence.maintenance.append(agent)
    for building in residence.buildings:
        for role, bucket in (
            (StructuralRole.SECURITY, residence.security),
            (StructuralRole.CLEANING, residence.cleaning),
        ):
            agent = demo.person(role)
            UserBuilding.objects.create(user=agent, building=building, granted_by=demo.admin)
            bucket[building.pk] = agent
