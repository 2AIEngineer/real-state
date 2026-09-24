"""What people are told about changes in the property referential."""

from __future__ import annotations

import datetime as dt

from apps.accounts.services.directory import UserDirectory
from apps.notifications.models import NotificationCategory
from apps.notifications.services import NotificationIntent, NotificationService
from apps.properties.models import Property, Syndicat, Unit, UnitOwnership


def syndicat_created(syndicat: Syndicat, *, actor) -> None:
    NotificationService.notify(
        NotificationIntent(
            event_type="syndicat.created",
            category=NotificationCategory.PROPERTY,
            title="Nouveau syndicat créé",
            body=f"Le syndicat « {syndicat.name} » a été créé par {actor.get_full_name()}.",
            target=syndicat,
            exclude=[actor],
        )
    )


def property_created(prop: Property, *, actor) -> None:
    NotificationService.notify(
        NotificationIntent(
            event_type="property.created",
            category=NotificationCategory.PROPERTY,
            title="Nouvelle propriété créée",
            body=(
                f"La propriété « {prop.name} » ({prop.syndicat.name}) "
                f"a été créée par {actor.get_full_name()}."
            ),
            target=prop,
            exclude=[actor],
        )
    )


def _ownership_changed(unit: Unit, users, *, title: str, body: str, target) -> None:
    NotificationService.notify(
        NotificationIntent(
            event_type="ownership.changed",
            category=NotificationCategory.PROPERTY,
            title=title,
            body=body,
            to=[user for user in users if not user.is_technical_account],
            bcc=UserDirectory.management(unit.building.property),
            target=target,
            include_platform_admins=False,
        )
    )


def unit_transferred(unit: Unit, *, owners, effective_date: dt.date) -> None:
    _ownership_changed(
        unit,
        owners,
        title=f"Changement de propriétaire — lot {unit.number}",
        body=(
            f"La propriété du lot {unit.number} a été transférée "
            f"à compter du {effective_date:%d/%m/%Y}."
        ),
        target=unit,
    )


def co_owner_added(unit: Unit, ownership: UnitOwnership) -> None:
    _ownership_changed(
        unit,
        [ownership.owner],
        title=f"Copropriété — lot {unit.number}",
        body=f"Vous êtes enregistré(e) comme copropriétaire du lot {unit.number}.",
        target=ownership,
    )


def ownership_ended(unit: Unit, ownership: UnitOwnership, *, end_date: dt.date) -> None:
    _ownership_changed(
        unit,
        [ownership.owner],
        title=f"Fin de propriété — lot {unit.number}",
        body=f"Votre propriété du lot {unit.number} a pris fin le {end_date:%d/%m/%Y}.",
        target=ownership,
    )
