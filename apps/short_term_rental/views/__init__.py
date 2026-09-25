"""HTTP endpoints, one module per resource. `urls.py` reads them from here."""

from apps.short_term_rental.views.members import (  # noqa: F401
    MemberDetailView,
    MemberIdCardView,
    MemberListView,
)
from apps.short_term_rental.views.rentals import (  # noqa: F401
    CancelView,
    CheckInView,
    CompleteView,
    RescheduleView,
    ShortTermRentalCompletePastView,
    ShortTermRentalDetailView,
    ShortTermRentalListView,
)
