from django.conf import settings
from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    dependencies = [
        ("ai_lab", "0001_initial"),
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
    ]

    operations = [
        migrations.CreateModel(
            name="ArchibaldPersonaConfig",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("created_at", models.DateTimeField(auto_now_add=True)),
                ("updated_at", models.DateTimeField(auto_now=True)),
                ("preset", models.CharField(blank=True, default="", max_length=64)),
                ("owner", models.OneToOneField(on_delete=django.db.models.deletion.CASCADE, related_name="archibald_persona_config", to=settings.AUTH_USER_MODEL)),
            ],
            options={"db_table": "ai_lab_archibaldpersonaconfig"},
        ),
    ]
