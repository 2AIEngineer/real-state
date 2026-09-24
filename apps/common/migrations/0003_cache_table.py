"""The cache table (throttling counters): shared by every process, kept in PostgreSQL."""

from django.core.management import call_command
from django.db import migrations


def create_cache_table(apps, schema_editor):
    call_command("createcachetable", verbosity=0)


class Migration(migrations.Migration):
    dependencies = [("common", "0002_initial")]

    operations = [migrations.RunPython(create_cache_table, migrations.RunPython.noop)]
