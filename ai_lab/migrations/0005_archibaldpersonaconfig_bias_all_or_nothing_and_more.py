from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("ai_lab", "0004_archibaldinstructionstate"),
    ]

    operations = [
        migrations.AddField(
            model_name="archibaldpersonaconfig",
            name="bias_all_or_nothing",
            field=models.BooleanField(default=False),
        ),
    ]
