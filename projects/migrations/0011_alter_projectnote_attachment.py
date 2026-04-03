from django.db import migrations, models

import common.upload_paths


class Migration(migrations.Migration):

    dependencies = [
        ("projects", "0010_subproject_and_subprojectactivity"),
    ]

    operations = [
        migrations.AlterField(
            model_name="projectnote",
            name="attachment",
            field=models.FileField(blank=True, null=True, upload_to=common.upload_paths.project_note_attachment_upload_to),
        ),
    ]
