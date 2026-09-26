"""The business objects a conversation can be about, and the people around them.

Chat sits above the modules it talks about: each kind of context is one entry
of `CONTEXTS`, which says how to reach the object's property and initiator and
who forms the staff side. Adding a kind of conversation means adding an entry
here (and the matching one-to-one field on `ChatRoom`).
"""

from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass
from operator import attrgetter

from django.db.models import Model

from apps.accounts.services.directory import UserDirectory
from apps.amenities.models import Booking
from apps.chat.models import ChatRoom
from apps.common.exceptions import InvalidInput
from apps.service_requests.models import ServiceRequest
from apps.store.models import Order


@dataclass(frozen=True)
class RoomContext:
    kind: str
    obj: Model
    prop: object
    initiator: object
    label: str


def _management(ctx: RoomContext) -> list:
    return list(UserDirectory.management_and_admins(ctx.prop))


def _management_and_resolvers(ctx: RoomContext) -> list:
    staff = {user.pk: user for user in _management(ctx)}
    sr = ctx.obj
    for assignment in sr.assignments.filter(
        resolution_round=sr.current_round
    ).select_related("resolver"):
        staff.setdefault(assignment.resolver_id, assignment.resolver)
    return list(staff.values())


def _platform_admins(ctx: RoomContext) -> list:
    return list(UserDirectory.platform_admins())  # the store is run by platform admins


@dataclass(frozen=True)
class ContextSpec:
    kind: str  # also the name of the one-to-one field on ChatRoom
    model: type[Model]
    initiator: str  # attribute of the object holding who started it
    property_path: str  # where to find the property, from the object
    label: str  # how people call it ("demande")
    staff: Callable[[RoomContext], list]  # the staff side of the conversation

    @property
    def select_related(self) -> tuple[str, ...]:
        """What to load with a room to describe its context without further queries."""
        property_path = self.property_path.replace(".", "__")
        return (f"{self.kind}__{self.initiator}", f"{self.kind}__{property_path}")

    def describe(self, obj: Model) -> RoomContext:
        return RoomContext(
            kind=self.kind,
            obj=obj,
            prop=attrgetter(self.property_path)(obj),
            initiator=getattr(obj, self.initiator),
            label=f"{self.label} #{obj.pk}",
        )


CONTEXTS: dict[str, ContextSpec] = {
    spec.kind: spec
    for spec in (
        ContextSpec(
            "service_request",
            ServiceRequest,
            "requester",
            "property",
            "demande",
            _management_and_resolvers,
        ),
        ContextSpec(
            "booking", Booking, "booker", "amenity.property", "réservation", _management
        ),
        ContextSpec(
            "order", Order, "orderer", "property", "commande", _platform_admins
        ),
    )
}
CONTEXT_KINDS = tuple(CONTEXTS)


def context_of(room: ChatRoom) -> RoomContext:
    """The context a room belongs to (exactly one of its one-to-one fields is set)."""
    for spec in CONTEXTS.values():
        if getattr(room, f"{spec.kind}_id"):
            return spec.describe(getattr(room, spec.kind))
    raise ValueError(f"Room #{room.pk} has no context.")


def load_context(kind: str, object_id: int) -> RoomContext | None:
    """The context of `kind` for an object id; None when there is no such object."""
    spec = CONTEXTS.get(kind)
    if spec is None:
        raise InvalidInput("Unknown conversation context.", field="context_type")
    related = tuple({spec.initiator, spec.property_path.replace(".", "__")})
    obj = spec.model.objects.select_related(*related).filter(pk=object_id).first()
    return spec.describe(obj) if obj is not None else None


def staff_of(ctx: RoomContext) -> list:
    """The staff side of the conversation."""
    return CONTEXTS[ctx.kind].staff(ctx)
