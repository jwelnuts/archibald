from django.db import migrations


class Migration(migrations.Migration):

    dependencies = [
        ("archibald", "0005_archibald_openai_state"),
    ]

    operations = [
        migrations.DeleteModel(name="ArchibaldMessage"),
        migrations.DeleteModel(name="ArchibaldThread"),
    ]