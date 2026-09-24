"""JSON in and out of the API with orjson.

Same output as DRF's `JSONRenderer` (compact UTF-8, and the same encoding of
the types orjson leaves to us: `datetime` with a `Z`, `Decimal`, lazy strings…),
produced about ten times faster. On a typical page the gain is a fraction of a
millisecond: most of a request is spent in the database and the serializers.
"""

from __future__ import annotations

import orjson
from rest_framework.exceptions import ParseError
from rest_framework.parsers import BaseParser
from rest_framework.renderers import BaseRenderer
from rest_framework.utils.encoders import JSONEncoder

_OPTIONS = orjson.OPT_PASSTHROUGH_DATETIME | orjson.OPT_NON_STR_KEYS
_fallback = JSONEncoder().default


class ORJSONRenderer(BaseRenderer):
    media_type = "application/json"
    format = "json"
    charset = None  # JSON is always UTF-8

    def render(self, data, accepted_media_type=None, renderer_context=None) -> bytes:
        if data is None:
            return b""
        return orjson.dumps(data, default=_fallback, option=_OPTIONS)


class ORJSONParser(BaseParser):
    media_type = "application/json"

    def parse(self, stream, media_type=None, parser_context=None):
        try:
            return orjson.loads(stream.read())
        except orjson.JSONDecodeError as exc:
            raise ParseError(f"JSON parse error - {exc}") from exc
