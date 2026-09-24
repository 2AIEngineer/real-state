"""Test data builders. They go through services wherever a business invariant
is involved (unit => promoter ownership, lease => members) so tests never
start from a state the application could not produce."""

from __future__ import annotations

import datetime as dt
import itertools
from decimal import Decimal

from django.contrib.auth import get_user_model
from django.core.files.uploadedfile import SimpleUploadedFile

from apps.accounts.enums import StructuralRole
from apps.accounts.models import UserBuilding, UserProperty, UserSyndicat
from apps.leasing.services import LeaseService, MemberInput
from apps.properties.models import Building, Promoter, Property, Syndicat
from apps.properties.services import Acquirer, OwnershipService, UnitService

User = get_user_model()
_seq = itertools.count(1)

PNG_BYTES = (
    b"\x89PNG\r\n\x1a\n\x00\x00\x00\rIHDR\x00\x00\x00\x01\x00\x00\x00\x01\x08\x06\x00\x00\x00\x1f\x15\xc4\x89"
    b"\x00\x00\x00\rIDATx\x9cc\xf8\x0f\x00\x00\x01\x01\x00\x05\x18\xd8N\x00\x00\x00\x00IEND\xaeB`\x82"
)
PDF_BYTES = b"%PDF-1.4\n1 0 obj<<>>endobj\ntrailer<<>>\n%%EOF\n"


def png(name: str = "photo.png") -> SimpleUploadedFile:
    return SimpleUploadedFile(name, PNG_BYTES, content_type="image/png")


def pdf(name: str = "doc.pdf") -> SimpleUploadedFile:
    return SimpleUploadedFile(name, PDF_BYTES, content_type="application/pdf")


def fake_exe(name: str = "photo.png") -> SimpleUploadedFile:
    return SimpleUploadedFile(name, b"MZ\x90\x00" + b"\x00" * 64, content_type="image/png")


def make_user(email: str | None = None, **extra):
    n = next(_seq)
    extra.setdefault("first_name", f"First{n}")
    extra.setdefault("last_name", f"Last{n}")
    return User.objects.create_user(
        email=email or f"user{n}@example.test", password="Str0ng-Passw0rd!", **extra
    )


def assign_role(user, role: str, target=None):
    """Give `user` its role and, when a target is given, the matching assignment.

    Bypasses the services on purpose: it builds fixtures, the rules are tested
    against the assignment services and `RoleService` directly.
    """
    if user.role != role:
        user.role = role
        user.save(update_fields=["role"])
    if target is None:
        return None
    model, field = {
        Syndicat: (UserSyndicat, "syndicat"),
        Property: (UserProperty, "property"),
        Building: (UserBuilding, "building"),
    }[type(target)]
    return model.objects.create(user=user, **{field: target})


def make_admin():
    user = make_user()
    assign_role(user, StructuralRole.ADMIN)
    return user


def make_syndicat(**extra) -> Syndicat:
    return Syndicat.objects.create(name=extra.pop("name", f"Syndicat {next(_seq)}"), **extra)


def make_promoter(**extra) -> Promoter:
    n = next(_seq)
    rep = User.objects.create_user(
        email=f"promoter{n}@example.test",
        first_name=f"Promoter {n}",
        last_name="",
        is_technical_account=True,
    )
    return Promoter.objects.create(
        name=extra.pop("name", f"Promoter {n}"), representative_user=rep, **extra
    )


def make_property(syndicat=None, promoter=None, **extra) -> Property:
    return Property.objects.create(
        syndicat=syndicat or make_syndicat(),
        promoter=promoter or make_promoter(),
        name=extra.pop("name", f"Residence {next(_seq)}"),
        **extra,
    )


def make_building(prop, **extra) -> Building:
    return Building.objects.create(
        property=prop, name=extra.pop("name", f"Bloc {next(_seq)}"), **extra
    )


def make_unit(building, actor, **extra):
    return UnitService.create(
        actor=actor,
        building=building,
        data={"number": extra.pop("number", f"A{next(_seq)}"), **extra},
    )


def make_owner(
    unit, user, actor, effective_date: dt.date | None = None, share: Decimal | None = None
):
    return OwnershipService.transfer(
        actor=actor,
        unit=unit,
        acquirers=[Acquirer(user=user, share=share)],
        effective_date=effective_date or dt.date.today(),
    )[0]


def make_lease(unit, users, actor, start: dt.date | None = None, end: dt.date | None = None):
    start = start or dt.date.today() - dt.timedelta(days=30)
    members = [MemberInput(user=u, is_signatory=(i == 0)) for i, u in enumerate(users)]
    return LeaseService.create(
        actor=actor, unit=unit, start_date=start, end_date=end, members=members
    )
