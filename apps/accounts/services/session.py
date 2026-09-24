"""The session the backend hands to the client after a successful login.

The payload is the `SessionContext` the frontend expects: credentials, the UI
configuration and the user. The backend fills what it knows; what only the
client can decide (the mode of the app, the step it stands at, the syndicat and
the property it will select) is left null, and every list empty.
"""

from __future__ import annotations

from apps.accounts.enums import StructuralRole
from apps.leasing.models import LeaseMember, LeaseStatus
from apps.properties.models import FEATURE_FLAG_FIELDS, OwnershipStatus, UnitOwnership


class SessionService:
    @staticmethod
    def configure(*, user, access_token: str | None, refresh_token: str | None) -> dict:
        ownerships = SessionService._ownerships(user)
        tenancies = SessionService._tenancies(user)
        return {
            "credentials": {
                "access_token": access_token,
                "refresh_token": refresh_token,
            },
            "ui_config": SessionService._empty_ui_config(),
            "user": {
                "id": user.pk,
                "email": user.email,
                "first_name": user.first_name,
                "last_name": user.last_name,
                "full_name": user.get_full_name(),
                "phone": user.phone,
                "gender": user.gender,
                "preferred_language": user.preferred_language,
                "role": SessionService._role(user.role),
                "assets": {
                    "user_status": {
                        "is_owner": bool(ownerships),
                        "is_tenant": bool(tenancies),
                    },
                    "ownerships": ownerships,
                    "tenancies": tenancies,
                },
            },
        }

    @staticmethod
    def _empty_ui_config() -> dict:
        """Nothing is selected yet: the client walks the UI configuration path."""
        return {
            "app_mode": None,
            "step": None,
            "syndicat": {"id": None, "name": None, "logo_url": None},
            "property": {
                "id": None,
                "name": None,
                "logo_url": None,
                "features": dict.fromkeys(FEATURE_FLAG_FIELDS.values(), False),
            },
        }

    @staticmethod
    def _role(role: str) -> dict:
        """The label of the role and one flag per role, exactly one of them true."""
        return {
            "label": StructuralRole(role).label,
            **{f"is_{value}": role == value for value in StructuralRole.values},
        }

    @staticmethod
    def _ownerships(user) -> list[dict]:
        rows = UnitOwnership.objects.filter(
            owner=user, status=OwnershipStatus.ACTIVE
        ).select_related("unit")
        return [
            {
                "unit_id": row.unit_id,
                "unit_number": row.unit.number,
                "ownership_share": (
                    None if row.ownership_share is None else str(row.ownership_share)
                ),
            }
            for row in rows
        ]

    @staticmethod
    def _tenancies(user) -> list[dict]:
        rows = LeaseMember.objects.filter(
            user=user, left_at__isnull=True, lease__status=LeaseStatus.ACTIVE
        ).select_related("lease__unit")
        return [
            {
                "lease_id": row.lease_id,
                "unit_id": row.lease.unit_id,
                "unit_number": row.lease.unit.number,
                "is_signatory": row.is_signatory,
            }
            for row in rows
        ]
