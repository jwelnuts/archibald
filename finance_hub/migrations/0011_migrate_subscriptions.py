from django.db import migrations


def migrate_subscriptions_data(apps, schema_editor):
    CurrencyOld = apps.get_model("subscriptions", "Currency")
    TagOld = apps.get_model("subscriptions", "Tag")
    AccountOld = apps.get_model("subscriptions", "Account")
    SubscriptionOld = apps.get_model("subscriptions", "Subscription")
    SubscriptionOccurrenceOld = apps.get_model("subscriptions", "SubscriptionOccurrence")

    CurrencyNew = apps.get_model("finance_hub", "Currency")
    TagNew = apps.get_model("finance_hub", "Tag")
    AccountNew = apps.get_model("finance_hub", "Account")
    SubscriptionNew = apps.get_model("finance_hub", "Subscription")
    SubscriptionOccurrenceNew = apps.get_model("finance_hub", "SubscriptionOccurrence")

    for old in CurrencyOld.objects.all():
        CurrencyNew.objects.get_or_create(
            code=old.code,
            defaults={"name": old.name, "symbol": old.symbol}
        )

    for old in TagOld.objects.all():
        TagNew.objects.create(
            id=old.id,
            owner_id=old.owner_id,
            name=old.name,
            created_at=old.created_at,
            updated_at=old.updated_at,
        )

    for old in AccountOld.objects.all():
        currency_new = CurrencyNew.objects.filter(code="EUR").first()
        AccountNew.objects.create(
            id=old.id,
            owner_id=old.owner_id,
            name=old.name,
            kind=old.kind,
            currency=currency_new,
            opening_balance=old.opening_balance,
            is_active=old.is_active,
            created_at=old.created_at,
            updated_at=old.updated_at,
        )

    for old in SubscriptionOld.objects.all():
        currency_new = CurrencyNew.objects.filter(code="EUR").first()
        SubscriptionNew.objects.create(
            id=old.id,
            owner_id=old.owner_id,
            name=old.name,
            payee_id=old.payee_id,
            category_id=old.category_id,
            project_id=old.project_id,
            account_id=old.account_id,
            currency=currency_new,
            amount=old.amount,
            start_date=old.start_date,
            next_due_date=old.next_due_date,
            end_date=old.end_date,
            interval=old.interval,
            interval_unit=old.interval_unit,
            status=old.status,
            autopay=old.autopay,
            note=old.note,
            created_at=old.created_at,
            updated_at=old.updated_at,
        )

    for old in SubscriptionOccurrenceOld.objects.all():
        currency_new = CurrencyNew.objects.filter(code="EUR").first()
        SubscriptionOccurrenceNew.objects.create(
            id=old.id,
            owner_id=old.owner_id,
            subscription_id=old.subscription_id,
            due_date=old.due_date,
            amount=old.amount,
            currency=currency_new,
            state=old.state,
            transaction_id=old.transaction_id,
            created_at=old.created_at,
            updated_at=old.updated_at,
        )


def reverse_migration(apps, schema_editor):
    pass


class Migration(migrations.Migration):

    dependencies = [
        ('finance_hub', '0010_subscriptions_base'),
    ]

    operations = [
        migrations.RunPython(migrate_subscriptions_data, reverse_migration),
    ]