"""Real-estate referential: syndicats, promoters, properties, buildings, units and the ownership ledger."""

from apps.properties.services.buildings import BuildingService
from apps.properties.services.features import FeatureGate
from apps.properties.services.ownership import Acquirer, OwnershipService
from apps.properties.services.promoters import PromoterService
from apps.properties.services.properties import PropertyService
from apps.properties.services.statistics import PropertyStatistics
from apps.properties.services.syndicats import SyndicatService
from apps.properties.services.units import UnitService

__all__ = [
    "Acquirer",
    "BuildingService",
    "FeatureGate",
    "OwnershipService",
    "PromoterService",
    "PropertyService",
    "PropertyStatistics",
    "SyndicatService",
    "UnitService",
]
