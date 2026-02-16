from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("archibald", "0002_rename_archibald_ar_owner__f6cfa7_idx_archibald_a_owner_i_db268a_idx_and_more"),
    ]

    operations = [
        migrations.AddField(
            model_name="archibaldmessage",
            name="is_favorite",
            field=models.BooleanField(default=False),
        ),
    ]
