"""HTTP translation of errors: one uniform error envelope for every failure.

{"error": {"code": "...", "message": "...", "details": {...}}}
"""

from __future__ import annotations

import logging

from django.core.exceptions import PermissionDenied as DjangoPermissionDenied
from django.db import IntegrityError
from django.db.models import ProtectedError
from django.http import Http404
from rest_framework import exceptions as drf_exceptions
from rest_framework import status
from rest_framework.response import Response
from rest_framework.views import exception_handler as drf_exception_handler

from apps.common.db import constraint_name_of, describe_protected
from apps.common.exceptions import DomainError

logger = logging.getLogger(__name__)


def _envelope(code: str, message: str, details=None, field=None) -> dict:
    error = {"code": code, "message": message}
    if field:
        error["field"] = field
    if details:
        error["details"] = details
    return {"error": error}


def exception_handler(exc, context):
    if isinstance(exc, DomainError):
        return Response({"error": exc.as_dict()}, status=exc.status_code)

    if isinstance(exc, ProtectedError):
        # Safety net: a delete service should have wrapped this in `deleting()`.
        blockers = describe_protected(exc)
        logger.warning("Unguarded protected delete: %s", blockers)
        return Response(
            _envelope(
                "resource_in_use", "This resource is still used by other records.", details=blockers
            ),
            status=status.HTTP_409_CONFLICT,
        )

    if isinstance(exc, IntegrityError):
        # Services translate the constraints they know about; anything reaching
        # this point is an unexpected constraint violation (usually a race).
        constraint = constraint_name_of(exc)
        logger.warning("Unhandled integrity error on constraint %s", constraint, exc_info=exc)
        return Response(
            _envelope(
                "conflict",
                "The request conflicts with existing data.",
                details={"constraint": constraint} if constraint else None,
            ),
            status=status.HTTP_409_CONFLICT,
        )

    if isinstance(exc, Http404):
        exc = drf_exceptions.NotFound()
    elif isinstance(exc, DjangoPermissionDenied):
        exc = drf_exceptions.PermissionDenied()

    response = drf_exception_handler(exc, context)
    if response is None:
        logger.exception("Unhandled API error", exc_info=exc)
        return Response(
            _envelope("server_error", "An internal error occurred."),
            status=status.HTTP_500_INTERNAL_SERVER_ERROR,
        )

    if isinstance(exc, drf_exceptions.ValidationError):
        response.data = _envelope("invalid", "Invalid input.", details=response.data)
    else:
        detail = response.data.get("detail") if isinstance(response.data, dict) else response.data
        code = getattr(detail, "code", None) or getattr(exc, "default_code", "error")
        response.data = _envelope(str(code), str(detail))
    return response
