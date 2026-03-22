from django.conf import settings
from django.db import migrations, models
import django.db.models.deletion
import django.utils.timezone


class Migration(migrations.Migration):

    dependencies = [
        ("core", "0005_davaccount"),
    ]

    operations = [
        migrations.CreateModel(
            name="DavExternalAccount",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("created_at", models.DateTimeField(auto_now_add=True)),
                ("updated_at", models.DateTimeField(auto_now=True)),
                ("label", models.CharField(blank=True, max_length=120)),
                ("dav_username", models.CharField(max_length=150, unique=True)),
                ("password_hash", models.CharField(max_length=255)),
                ("is_active", models.BooleanField(default=True)),
                ("password_rotated_at", models.DateTimeField(default=django.utils.timezone.now)),
                (
                    "owner",
                    models.ForeignKey(
                        on_delete=django.db.models.deletion.CASCADE,
                        related_name="dav_external_accounts",
                        to=settings.AUTH_USER_MODEL,
                    ),
                ),
            ],
            options={
                "indexes": [models.Index(fields=["owner", "is_active", "dav_username"], name="core_davext_owner_i_3ba4e3_idx")],
            },
        ),
        migrations.CreateModel(
            name="DavManagedCalendar",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("created_at", models.DateTimeField(auto_now_add=True)),
                ("updated_at", models.DateTimeField(auto_now=True)),
                ("principal", models.CharField(default="team", max_length=150)),
                ("calendar_slug", models.CharField(max_length=120)),
                ("display_name", models.CharField(blank=True, max_length=120)),
                ("is_active", models.BooleanField(default=True)),
                (
                    "owner",
                    models.ForeignKey(
                        on_delete=django.db.models.deletion.CASCADE,
                        related_name="dav_managed_calendars",
                        to=settings.AUTH_USER_MODEL,
                    ),
                ),
            ],
            options={
                "indexes": [models.Index(fields=["owner", "is_active", "principal", "calendar_slug"], name="core_davman_owner_i_084edd_idx")],
                "unique_together": {("owner", "principal", "calendar_slug")},
            },
        ),
        migrations.CreateModel(
            name="DavCalendarGrant",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("created_at", models.DateTimeField(auto_now_add=True)),
                ("updated_at", models.DateTimeField(auto_now=True)),
                ("access_level", models.CharField(choices=[("ro", "Sola lettura"), ("rw", "Lettura e scrittura")], default="ro", max_length=2)),
                ("is_active", models.BooleanField(default=True)),
                (
                    "calendar",
                    models.ForeignKey(
                        on_delete=django.db.models.deletion.CASCADE,
                        related_name="grants",
                        to="core.davmanagedcalendar",
                    ),
                ),
                (
                    "external_account",
                    models.ForeignKey(
                        on_delete=django.db.models.deletion.CASCADE,
                        related_name="grants",
                        to="core.davexternalaccount",
                    ),
                ),
                (
                    "owner",
                    models.ForeignKey(
                        on_delete=django.db.models.deletion.CASCADE,
                        related_name="dav_calendar_grants",
                        to=settings.AUTH_USER_MODEL,
                    ),
                ),
            ],
            options={
                "indexes": [models.Index(fields=["owner", "is_active", "access_level"], name="core_davcal_owner_i_f6be42_idx")],
                "unique_together": {("owner", "external_account", "calendar")},
            },
        ),
    ]
