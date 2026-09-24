"""Probes for the container platform: is the process up, can it serve requests."""

from django.db import connection
from django.http import JsonResponse
from django.views.decorators.http import require_GET


@require_GET
def liveness(request):
    """The process answers. Never touches a dependency: a database outage must
    not make the platform restart healthy containers."""
    return JsonResponse({"status": "ok"})


@require_GET
def readiness(request):
    """The process can serve: the database answers."""
    try:
        with connection.cursor() as cursor:
            cursor.execute("SELECT 1")
    except Exception:
        return JsonResponse({"status": "unavailable"}, status=503)
    return JsonResponse({"status": "ok"})
