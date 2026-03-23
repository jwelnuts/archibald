from django.conf import settings
from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    dependencies = [
        ("core", "0006_davexternalaccount_davmanagedcalendar_and_more"),
    ]

    operations = [
        migrations.CreateModel(
            name="DavTeam",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("created_at", models.DateTimeField(auto_now_add=True)),
                ("updated_at", models.DateTimeField(auto_now=True)),
                ("name", models.CharField(max_length=120)),
                ("slug", models.CharField(max_length=120)),
                ("is_active", models.BooleanField(default=True)),
                (
                    "owner",
                    models.ForeignKey(
                        on_delete=django.db.models.deletion.CASCADE,
                        related_name="davteams",
                        to=settings.AUTH_USER_MODEL,
                    ),
                ),
            ],
            options={
                "indexes": [models.Index(fields=["owner", "is_active", "slug"], name="core_davtea_owner_i_460f26_idx")],
                "unique_together": {("owner", "slug")},
            },
        ),
    ]
