"""Per-property activation of the feature modules (SaaS plan gating)."""

from __future__ import annotations

from apps.common.exceptions import BusinessRuleViolation, FeatureDisabled
from apps.properties.enums import Feature
from apps.properties.models import FEATURE_FLAG_FIELDS, Property


class FeatureGate:
    @staticmethod
    def is_enabled(prop: Property, feature: str) -> bool:
        return bool(getattr(prop, FEATURE_FLAG_FIELDS[feature]))

    @staticmethod
    def require(prop: Property, feature: str) -> None:
        if not prop.is_active:
            raise BusinessRuleViolation("This property is inactive.", code="property_inactive")
        if not FeatureGate.is_enabled(prop, feature):
            raise FeatureDisabled(
                f"The '{Feature(feature).label}' module is not enabled for this property."
            )
