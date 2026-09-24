from django.contrib.postgres.operations import BtreeGistExtension
from django.db import migrations


class Migration(migrations.Migration):
    """GiST support for scalar columns, required by the exclusion constraints
    preventing overlapping leases, exclusive bookings and short stays."""

    initial = True
    dependencies: list = []
    operations = [BtreeGistExtension()]
