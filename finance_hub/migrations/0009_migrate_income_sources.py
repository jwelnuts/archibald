from django.db import migrations


def migrate_income_sources(apps, schema_editor):
    IncomeSourceOld = apps.get_model("income", "IncomeSource")
    IncomeSourceNew = apps.get_model("finance_hub", "IncomeSource")

    for old in IncomeSourceOld.objects.all():
        IncomeSourceNew.objects.create(
            id=old.id,
            owner_id=old.owner_id,
            name=old.name,
            website=old.website,
            created_at=old.created_at,
            updated_at=old.updated_at,
        )


def reverse_migration(apps, schema_editor):
    pass


class Migration(migrations.Migration):

    dependencies = [
        ('finance_hub', '0008_incomesource'),
    ]

    operations = [
        migrations.RunPython(migrate_income_sources, reverse_migration),
    ]