"""Who lives there: unit sales, co-ownership, leases past, running and upcoming, inspections."""

from __future__ import annotations

import datetime as dt
from decimal import Decimal

from apps.demo import media
from apps.demo.seed.base import Demo, Residence
from apps.leasing.models import CheckPhase, ComponentCondition, LeaseTerminationReason
from apps.leasing.services import LeaseComponentStateService, LeaseService, MemberInput
from apps.notifications.services import PushTokenService
from apps.properties.models import UnitType
from apps.properties.services import Acquirer, OwnershipService

SOLD = 0.85  # share of units sold by the promoter
CO_OWNED = 0.10  # share of sales to two buyers
SECOND_UNIT = 0.08  # share of sales to someone who already owns in the residence
RENTED = 0.40  # share of sold apartments rented out
FORMER_LEASE = 0.15  # share of apartments that had a lease before
ROOMS = ["Entrée", "Séjour", "Cuisine", "Chambre principale", "Salle de bain", "Compteurs"]


def seed(demo: Demo) -> None:
    for residence in demo.residences:
        _sales(demo, residence)
        _leases(demo, residence)
        _devices(demo, residence)
        demo.log(
            f"  {residence.prop.name}: {len(residence.owners)} propriétaires, "
            f"{len(residence.tenants)} locataires, {len(residence.leases)} baux"
        )


def _sales(demo: Demo, residence: Residence) -> None:
    for unit in residence.units:
        if not demo.chance(SOLD):
            continue  # still held by the promoter
        if residence.owners and demo.chance(SECOND_UNIT):
            buyers = [demo.rng.choice(residence.owners)]
        elif demo.chance(CO_OWNED):
            buyers = [demo.person(), demo.person()]
        else:
            buyers = [demo.person()]
        shares = [Decimal("100")] if len(buyers) == 1 else [Decimal("50"), Decimal("50")]
        OwnershipService.transfer(
            actor=demo.admin,
            unit=unit,
            acquirers=[Acquirer(user=b, share=s) for b, s in zip(buyers, shares, strict=True)],
            effective_date=demo.date_ago(60, 2200),
            reference=f"Acte n° {demo.rng.randint(1000, 9999)}/{demo.rng.randint(2019, 2025)}",
        )
        for buyer in buyers:
            if buyer not in residence.owners:
                residence.owners.append(buyer)
        residence.occupants.setdefault(unit.pk, []).extend(buyers)


def _leases(demo: Demo, residence: Residence) -> None:
    apartments = [u for u in residence.units if u.unit_type == UnitType.APARTMENT]
    for unit in apartments:
        sold = unit.pk in residence.occupants
        if demo.chance(FORMER_LEASE):
            _former_lease(demo, residence, unit)
        if sold and demo.chance(RENTED):
            _running_lease(demo, residence, unit)
        elif not sold and demo.chance(0.1):
            _running_lease(demo, residence, unit, upcoming=True)


def _members(demo: Demo) -> list[MemberInput]:
    count = demo.rng.choices([1, 2, 3], weights=[45, 40, 15])[0]
    members = []
    for index in range(count):
        extras = {
            "emergency_contact_name": demo.rng.choice(
                ["Mme Alaoui", "M. Bennani", "Mme Tazi", "M. Martin"]
            ),
            "emergency_contact_phone": f"+212 6{demo.rng.randint(10, 99)} {demo.rng.randint(100000, 999999)}",
            "emergency_contact_relation": demo.rng.choice(["Parent", "Frère", "Sœur", "Ami"]),
        }
        if demo.chance(0.4):
            extras["vehicles_info"] = [
                {
                    "plate": f"{demo.rng.randint(10000, 99999)}-{demo.rng.choice('ABDEH')}-{demo.rng.randint(1, 80)}",
                    "model": demo.rng.choice(
                        ["Dacia Logan", "Renault Clio", "Peugeot 208", "Toyota Yaris"]
                    ),
                }
            ]
        if demo.chance(0.2):
            extras["pets_info"] = [{"kind": demo.rng.choice(["Chat", "Chien"]), "name": "Milo"}]
        members.append(MemberInput(user=demo.person(), is_signatory=index == 0, extras=extras))
    return members


def _running_lease(demo: Demo, residence: Residence, unit, *, upcoming: bool = False) -> None:
    if upcoming:
        start = demo.today + dt.timedelta(days=demo.rng.randint(5, 45))
    else:
        start = demo.date_ago(30, 900)
    years = demo.rng.choice([1, 2, 3, None])
    end = start.replace(year=start.year + years) if years else None
    if end is not None and end <= demo.today + dt.timedelta(days=20):
        end = demo.today + dt.timedelta(days=demo.rng.randint(20, 400))
    members = _members(demo)
    lease = LeaseService.create(
        actor=residence.manager,
        unit=unit,
        start_date=start,
        end_date=end,
        members=members,
        contract_reference=f"BAIL-{residence.prop.pk}-{unit.number}-{start.year}",
        notes="Dépôt de garantie : deux mois de loyer.",
    )
    residence.leases.append(lease)
    tenants = [m.user for m in members]
    residence.tenants.extend(tenants)
    residence.occupants.setdefault(unit.pk, []).extend(tenants)
    if not upcoming and demo.chance(0.35):
        _inspection(demo, residence, lease, CheckPhase.IN, start)


def _former_lease(demo: Demo, residence: Residence, unit) -> None:
    start = demo.date_ago(1300, 2100)
    end = start + dt.timedelta(days=demo.rng.randint(330, 720))
    lease = LeaseService.create(
        actor=residence.manager,
        unit=unit,
        start_date=start,
        end_date=end,
        members=_members(demo),
        contract_reference=f"BAIL-{residence.prop.pk}-{unit.number}-{start.year}",
    )
    _inspection(demo, residence, lease, CheckPhase.IN, start)
    _inspection(demo, residence, lease, CheckPhase.OUT, end)
    LeaseService.terminate(
        actor=residence.manager,
        lease=lease,
        effective_date=end,
        reason=demo.rng.choice(
            [LeaseTerminationReason.TERM_REACHED, LeaseTerminationReason.TENANT_NOTICE]
        ),
    )


def _inspection(demo: Demo, residence: Residence, lease, phase: str, on: dt.date) -> None:
    for room in demo.rng.sample(ROOMS, k=demo.rng.randint(3, len(ROOMS))):
        good = demo.chance(0.85 if phase == CheckPhase.IN else 0.7)
        LeaseComponentStateService.record(
            actor=residence.manager,
            lease=lease,
            name=room,
            state=ComponentCondition.GOOD if good else ComponentCondition.BAD,
            on_check=phase,
            on_check_date=on,
            description=""
            if good
            else demo.rng.choice(
                ["Traces sur les murs", "Joint de silicone à refaire", "Rayure sur le parquet"]
            ),
            files=[] if good else [media.png(f"{room}.png", (180, 120, 90))],
        )


def _devices(demo: Demo, residence: Residence) -> None:
    for index, user in enumerate(residence.residents):
        if demo.chance(0.6):
            PushTokenService.register(
                user=user,
                device_id=f"device-{user.pk}",
                expo_push_token=f"ExponentPushToken[demo{user.pk:06d}{index}]",
                platform=demo.rng.choice(["ios", "android"]),
            )
