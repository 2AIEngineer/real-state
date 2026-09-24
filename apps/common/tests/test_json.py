import datetime as dt
import decimal

from django.utils.translation import gettext_lazy
from rest_framework.renderers import JSONRenderer

from apps.common.json import ORJSONParser, ORJSONRenderer


def test_the_output_is_byte_for_byte_the_one_of_drf():
    data = {
        "at": dt.datetime(2026, 1, 1, 8, 30, tzinfo=dt.UTC),
        "day": dt.date(2026, 1, 2),
        "time": dt.time(10, 0),
        "amount": decimal.Decimal("1.50"),
        "label": gettext_lazy("Résidence"),
        "items": [1, "é", None, True],
        7: "non-string key",
    }

    assert ORJSONRenderer().render(data) == JSONRenderer().render(data)


def test_the_parser_reads_utf8_json():
    class Stream:
        def read(self):
            return '{"name": "Façade"}'.encode()

    assert ORJSONParser().parse(Stream()) == {"name": "Façade"}
