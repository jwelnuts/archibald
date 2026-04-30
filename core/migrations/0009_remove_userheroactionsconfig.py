# Generated manually on 2026-04-30

from django.db import migrations


class Migration(migrations.Migration):

    dependencies = [
        ('core', '0008_rename_core_davcal_owner_i_f6be42_idx_core_davcal_owner_i_e922b1_idx_and_more'),
    ]

    operations = [
        migrations.DeleteModel(
            name='UserHeroActionsConfig',
        ),
    ]
