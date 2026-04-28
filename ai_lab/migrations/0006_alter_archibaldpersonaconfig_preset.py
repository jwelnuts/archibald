from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("ai_lab", "0005_archibaldpersonaconfig_bias_all_or_nothing_and_more"),
    ]

    operations = [
        migrations.AlterField(
            model_name="archibaldpersonaconfig",
            name="preset",
            field=models.CharField(blank=True, default="default", max_length=64),
        ),
    ]
