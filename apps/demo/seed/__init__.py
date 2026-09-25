"""The demo, built in order: each step relies on what the previous ones created.

| Step          | Creates                                                             |
|---------------|---------------------------------------------------------------------|
| `referential` | admin, providers, promoters, 2 syndicats, 4 properties, 8 buildings, 400 units, staff |
| `residents`   | unit sales and co-ownership, leases (running, past, upcoming), inspections, devices |
| `community`   | announcements, events, surveys and answers, library documents       |
| `commerce`    | amenities and bookings, store products and orders, marketplace listings |
| `operations`  | service requests and rounds, work orders, visitors, short-term rentals, chats |
"""

from django.db import connection

from apps.demo.seed import commerce, community, operations, referential, residents
from apps.demo.seed.base import PASSWORD, Demo

STEPS = [
    ("Référentiel et personnel", referential.seed),
    ("Propriétaires et locataires", residents.seed),
    ("Vie de la résidence", community.seed),
    ("Équipements, boutique, petites annonces", commerce.seed),
    ("Demandes, travaux, visiteurs, locations courtes", operations.seed),
]


def run(*, seed: int, log) -> Demo:
    demo = Demo(seed=seed, log=log)
    for label, step in STEPS:
        log(f"— {label}")
        step(demo)
        # The whole demo is one transaction, which autovacuum cannot see: refresh
        # the planner statistics by hand, or queries on the new rows crawl.
        with connection.cursor() as cursor:
            cursor.execute("ANALYZE")
    return demo


__all__ = ["PASSWORD", "Demo", "run"]
