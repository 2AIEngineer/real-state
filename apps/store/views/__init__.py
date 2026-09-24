"""HTTP endpoints, one module per resource. `urls.py` reads them from here."""

from apps.store.views.orders import (  # noqa: F401
    OrderCancelView,
    OrderConfirmView,
    OrderDeliverView,
    OrderDetailView,
    OrderListView,
)
from apps.store.views.products import (  # noqa: F401
    ProductDetailView,
    ProductImageDetailView,
    ProductImagesView,
    ProductListView,
)
