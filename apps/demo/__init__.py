"""Demo data for development: `python manage.py seed_demo`.

Everything is created through the business services, so the data obeys the
same rules as the application (a unit always has an owner, leases never
overlap, stock is reserved, notifications are written). Dates meant to lie in
the past are shifted afterwards. Never installed in production.
"""
