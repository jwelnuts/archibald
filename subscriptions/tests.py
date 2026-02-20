from datetime import date
from decimal import Decimal

from django.contrib.auth import get_user_model
from django.test import TestCase

from transactions.models import Transaction

from .models import Account, Currency, Subscription, SubscriptionOccurrence


class SubscriptionPaymentsTests(TestCase):
    def setUp(self):
        self.user = get_user_model().objects.create_user(username="subs_user", password="test1234")
        self.other_user = get_user_model().objects.create_user(username="other_subs_user", password="test1234")
        self.currency, _ = Currency.objects.get_or_create(code="EUR", defaults={"name": "Euro"})
        self.account = Account.objects.create(
            owner=self.user,
            name="Conto Principale",
            kind=Account.Kind.BANK,
            currency=self.currency,
            opening_balance=Decimal("0.00"),
            is_active=True,
        )
        self.subscription = Subscription.objects.create(
            owner=self.user,
            name="Netflix",
            account=self.account,
            currency=self.currency,
            amount=Decimal("15.99"),
            start_date=date(2026, 1, 1),
            next_due_date=date(2026, 2, 1),
            interval=1,
            interval_unit=Subscription.IntervalUnit.MONTH,
            status=Subscription.Status.ACTIVE,
        )

    def test_pay_existing_occurrence_creates_transaction_and_marks_paid(self):
        occurrence = SubscriptionOccurrence.objects.create(
            owner=self.user,
            subscription=self.subscription,
            due_date=date(2026, 2, 1),
            amount=Decimal("15.99"),
            currency=self.currency,
            state=SubscriptionOccurrence.State.PLANNED,
        )
        self.client.login(username="subs_user", password="test1234")
        response = self.client.post(
            "/subs/api/pay",
            {
                "occurrence_id": occurrence.id,
                "account_id": self.account.id,
            },
        )
        self.assertEqual(response.status_code, 302)
        self.assertEqual(response.url, "/subs/")

        occurrence.refresh_from_db()
        self.assertEqual(occurrence.state, SubscriptionOccurrence.State.PAID)
        self.assertIsNotNone(occurrence.transaction_id)
        tx = occurrence.transaction
        self.assertEqual(tx.tx_type, Transaction.Type.EXPENSE)
        self.assertEqual(tx.amount, Decimal("15.99"))
        self.assertEqual(tx.account_id, self.account.id)
        self.assertEqual(tx.source_subscription_id, self.subscription.id)

    def test_pay_from_subscription_fallback_creates_occurrence_then_marks_paid(self):
        self.client.login(username="subs_user", password="test1234")
        response = self.client.post(
            "/subs/api/pay",
            {
                "subscription_id": self.subscription.id,
                "due_date": "2026-02-01",
                "account_id": self.account.id,
            },
        )
        self.assertEqual(response.status_code, 302)
        self.assertEqual(response.url, "/subs/")

        occurrence = SubscriptionOccurrence.objects.get(
            owner=self.user,
            subscription=self.subscription,
            due_date=date(2026, 2, 1),
        )
        self.assertEqual(occurrence.state, SubscriptionOccurrence.State.PAID)
        self.assertIsNotNone(occurrence.transaction_id)
        self.assertTrue(
            Transaction.objects.filter(
                owner=self.user,
                source_subscription=self.subscription,
                tx_type=Transaction.Type.EXPENSE,
            ).exists()
        )

    def test_pay_rejects_account_from_another_user(self):
        other_account = Account.objects.create(
            owner=self.other_user,
            name="Conto Altro",
            kind=Account.Kind.BANK,
            currency=self.currency,
            opening_balance=Decimal("0.00"),
            is_active=True,
        )
        occurrence = SubscriptionOccurrence.objects.create(
            owner=self.user,
            subscription=self.subscription,
            due_date=date(2026, 2, 1),
            amount=Decimal("15.99"),
            currency=self.currency,
            state=SubscriptionOccurrence.State.PLANNED,
        )
        self.client.login(username="subs_user", password="test1234")
        response = self.client.post(
            "/subs/api/pay",
            {
                "occurrence_id": occurrence.id,
                "account_id": other_account.id,
            },
        )
        self.assertEqual(response.status_code, 404)
        occurrence.refresh_from_db()
        self.assertEqual(occurrence.state, SubscriptionOccurrence.State.PLANNED)
        self.assertFalse(Transaction.objects.filter(owner=self.user).exists())
