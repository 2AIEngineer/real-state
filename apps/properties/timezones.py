"""The local time of a property.

A property is somewhere on Earth: "today", opening hours and the times written
in notifications are those of its own time zone (`Property.timezone`, an IANA
name such as `Africa/Casablanca` or `America/Montreal`), never the server's.
Instants are stored in UTC; only the reading of a date or a clock time is local.
"""

from __future__ import annotations

import datetime as dt
from functools import lru_cache
from zoneinfo import ZoneInfo, available_timezones

from django.conf import settings
from django.utils import timezone


def default_time_zone() -> str:
    """Time zone given to a new property unless its creator picks one."""
    return settings.TIME_ZONE


@lru_cache(maxsize=1)
def known_time_zones() -> frozenset[str]:
    return frozenset(available_timezones())


def is_known(name: str) -> bool:
    return name in known_time_zones()


def zone_of(prop) -> ZoneInfo:
    return ZoneInfo(prop.timezone)


def local(prop, value: dt.datetime) -> dt.datetime:
    """An instant, read on the clocks of the property."""
    return timezone.localtime(value, zone_of(prop))


def today(prop) -> dt.date:
    """The current date where the property is."""
    return local(prop, timezone.now()).date()
