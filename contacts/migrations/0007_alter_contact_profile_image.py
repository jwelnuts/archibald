from django.db import migrations, models

import common.upload_paths


class Migration(migrations.Migration):

    dependencies = [
        ("contacts", "0006_contactdeliveryaddress"),
    ]

    operations = [
        migrations.AlterField(
            model_name="contact",
            name="profile_image",
            field=models.FileField(blank=True, null=True, upload_to=common.upload_paths.contact_profile_image_upload_to),
        ),
    ]
