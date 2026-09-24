"""Remove stored blobs that no Attachment row references.

Blobs are written before the business transaction commits; when it rolls
back, the file remains without a row. This command reclaims them.
"""

import datetime as dt

from django.core.files.storage import default_storage
from django.core.management.base import BaseCommand
from django.utils import timezone

from apps.common.models import Attachment

ROOT = "attachments"


def _walk(path: str):
    directories, files = default_storage.listdir(path)
    for name in files:
        yield f"{path}/{name}"
    for directory in directories:
        yield from _walk(f"{path}/{directory}")


class Command(BaseCommand):
    help = "Delete attachment files that are not referenced by the database."

    def add_arguments(self, parser):
        parser.add_argument(
            "--min-age-hours", type=int, default=24, help="Keep files younger than this."
        )
        parser.add_argument("--dry-run", action="store_true")

    def handle(self, *args, min_age_hours: int, dry_run: bool, **options):
        if not default_storage.exists(ROOT):
            self.stdout.write("Nothing stored yet.")
            return
        known = set(Attachment.objects.values_list("file", flat=True))
        threshold = timezone.now() - dt.timedelta(hours=min_age_hours)
        removed = 0
        for name in _walk(ROOT):
            if name in known:
                continue
            try:
                modified = default_storage.get_modified_time(name)
            except (NotImplementedError, OSError):
                continue
            if modified > threshold:
                continue
            removed += 1
            if not dry_run:
                default_storage.delete(name)
        verb = "Would remove" if dry_run else "Removed"
        self.stdout.write(f"{verb} {removed} orphan file(s).")
