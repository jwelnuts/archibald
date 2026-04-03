from django.db import migrations, models

import common.upload_paths


class Migration(migrations.Migration):

    dependencies = [
        ("transactions", "0004_transaction_attachment"),
    ]

    operations = [
        migrations.AlterField(
            model_name="transaction",
            name="attachment",
            field=models.FileField(blank=True, null=True, upload_to=common.upload_paths.transaction_attachment_upload_to),
        ),
    ]
