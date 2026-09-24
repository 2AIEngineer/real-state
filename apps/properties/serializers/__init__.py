"""Serializers: the shape of inputs and outputs, one module per area.

Views import the package (`from apps.X import serializers as s`) and use `s.Name`.
"""

from apps.properties.serializers.buildings import (  # noqa: F401
    BuildingInputSerializer,
    BuildingSerializer,
    BuildingUpdateSerializer,
    UnitInputSerializer,
    UnitSerializer,
    UnitUpdateSerializer,
)
from apps.properties.serializers.ownership import (  # noqa: F401
    OwnershipAcquirerSerializer,
    OwnershipCoOwnerSerializer,
    OwnershipEndSerializer,
    OwnershipSerializer,
    OwnershipTransferSerializer,
)
from apps.properties.serializers.promoters import (  # noqa: F401
    PromoterChangeSerializer,
    PromoterInputSerializer,
    PromoterSerializer,
    PromoterUpdateSerializer,
)
from apps.properties.serializers.properties import (  # noqa: F401
    PropertyFeaturesSerializer,
    PropertyInputSerializer,
    PropertySerializer,
    PropertyStatisticsSerializer,
    PropertyUpdateSerializer,
)
from apps.properties.serializers.syndicats import (  # noqa: F401
    SyndicatInputSerializer,
    SyndicatSerializer,
    SyndicatUpdateSerializer,
)
from apps.properties.serializers.ui_config import (  # noqa: F401
    UIConfigPropertySerializer,
    UIConfigSearchQueryParamsSerializer,
    UIConfigSyndicatSerializer,
)
