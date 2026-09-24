"""HTTP endpoints, one module per resource. `urls.py` reads them from here."""

from apps.amenities.views.amenities import (  # noqa: F401
    AmenityDetailView,
    AmenityImageDetailView,
    AmenityImagesView,
    AmenityListView,
    AmenityScheduleView,
)
from apps.amenities.views.bookings import (  # noqa: F401
    BookingCancelView,
    BookingDecisionView,
    BookingDetailView,
    BookingListView,
)
