"""What every step of the demo shares: the random source, the people, the residences."""

from __future__ import annotations

import datetime as dt
import random
import unicodedata
from dataclasses import dataclass, field

from django.contrib.auth import get_user_model
from django.contrib.auth.hashers import make_password
from django.utils import timezone

from apps.accounts.enums import Gender, StructuralRole
from apps.demo import content

User = get_user_model()

EMAIL_DOMAIN = "demo.urbis.test"
PASSWORD = "Demo@2026!"


def slug(value: str) -> str:
    ascii_only = unicodedata.normalize("NFKD", value).encode("ascii", "ignore").decode()
    return "".join(c for c in ascii_only.lower().replace(" ", "-") if c.isalnum() or c in ".-")


@dataclass
class Residence:
    """One property of the demo, with the people working and living there."""

    prop: object
    syndicat: object
    syndic: object = None
    buildings: list = field(default_factory=list)
    units: list = field(default_factory=list)
    managers: list = field(default_factory=list)
    maintenance: list = field(default_factory=list)
    security: dict = field(default_factory=dict)  # building id -> agent
    cleaning: dict = field(default_factory=dict)  # building id -> agent
    owners: list = field(default_factory=list)
    tenants: list = field(default_factory=list)
    occupants: dict = field(default_factory=dict)  # unit id -> owners and tenants
    leases: list = field(default_factory=list)
    amenities: list = field(default_factory=list)
    products: list = field(default_factory=list)

    @property
    def manager(self):
        return self.managers[0]

    @property
    def residents(self) -> list:
        return list(dict.fromkeys([*self.owners, *self.tenants]))

    def occupied_units(self) -> list:
        return [unit for unit in self.units if self.occupants.get(unit.pk)]


class Demo:
    """The shared state of one demo run."""

    def __init__(self, seed: int, log):
        self.rng = random.Random(seed)
        self.log = log
        self.now = timezone.now()
        self.today = timezone.localdate()
        self.password_hash = make_password(PASSWORD)  # hashed once: hashing is slow on purpose
        self.admin = None
        self.syndics: list = []
        self.providers: list = []
        self.residences: list[Residence] = []
        self._emails: set[str] = set()

    # ----------------------------------------------------------------- people
    def person(
        self, role: str = StructuralRole.STANDARD, *, email_hint: str | None = None, **extra
    ):
        """A new account holding `role`, able to log in with the demo password."""
        female = self.rng.random() < 0.5
        first = self.rng.choice(content.FIRST_NAMES_FEMALE if female else content.FIRST_NAMES_MALE)
        last = self.rng.choice(content.LAST_NAMES)
        email = self._unique_email(email_hint or f"{slug(first)}.{slug(last)}")
        return User.objects.create(
            email=email,
            password=self.password_hash,
            first_name=first,
            last_name=last,
            phone=f"+212 6{self.rng.randint(10, 99)} {self.rng.randint(10, 99)} "
            f"{self.rng.randint(10, 99)} {self.rng.randint(10, 99)}",
            gender=Gender.FEMALE if female else Gender.MALE,
            preferred_language="fr" if self.rng.random() < 0.85 else "en",
            role=role,
            date_joined=self.now - dt.timedelta(days=self.rng.randint(30, 900)),
            password_changed_at=self.now,
            **extra,
        )

    def _unique_email(self, local: str) -> str:
        candidate, n = f"{local}@{EMAIL_DOMAIN}", 1
        while candidate in self._emails:
            n += 1
            candidate = f"{local}{n}@{EMAIL_DOMAIN}"
        self._emails.add(candidate)
        return candidate

    # ------------------------------------------------------------------ dates
    def days_ago(self, low: int, high: int) -> dt.datetime:
        return self.now - dt.timedelta(
            days=self.rng.randint(low, high), minutes=self.rng.randint(0, 600)
        )

    def date_ago(self, low: int, high: int) -> dt.date:
        return self.today - dt.timedelta(days=self.rng.randint(low, high))

    def chance(self, probability: float) -> bool:
        return self.rng.random() < probability
