from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("ai_lab", "0002_archibaldpersonaconfig"),
    ]

    operations = [
        migrations.AddField(
            model_name="archibaldpersonaconfig",
            name="psych_accountability_nudge",
            field=models.BooleanField(default=False),
        ),
    ]
