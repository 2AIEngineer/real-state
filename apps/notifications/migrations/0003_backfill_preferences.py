from django.db import migrations

# Frozen copy of the role defaults at the time of this migration.
FEATURES = (
    "service_request_enabled",
    "announcements_enabled",
    "events_enabled",
    "bookings_enabled",
    "store_enabled",
    "library_enabled",
    "short_term_rental_enabled",
    "surveys_enabled",
    "marketplace_enabled",
    "visitors_enabled",
    "chat_enabled",
)
DISABLED_BY_ROLE = {
    "syndic": {"store_enabled"},
    "manager": {"store_enabled"},
    "security": set(FEATURES),
    "cleaning": set(FEATURES),
    "provider": set(FEATURES),
}


def backfill(apps, schema_editor):
    User = apps.get_model("accounts", "User")
    NotificationPreference = apps.get_model("notifications", "NotificationPreference")
    missing = User.objects.filter(notification_preference__isnull=True).values_list("pk", "role")
    NotificationPreference.objects.bulk_create(
        [
            NotificationPreference(
                user_id=pk,
                **{name: name not in DISABLED_BY_ROLE.get(role, ()) for name in FEATURES},
            )
            for pk, role in missing.iterator()
        ],
        batch_size=1000,
        ignore_conflicts=True,
    )


class Migration(migrations.Migration):
    dependencies = [("notifications", "0002_user_deletion")]

    operations = [migrations.RunPython(backfill, migrations.RunPython.noop)]
