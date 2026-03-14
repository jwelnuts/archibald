from decimal import Decimal

from django.contrib.auth import get_user_model
from django.test import TestCase

from income.models import IncomeSource
from projects.models import Category, Project
from subscriptions.models import Account, Currency

from .models import Transaction


class TransactionsUnifiedFlowTests(TestCase):
    def setUp(self):
        self.user = get_user_model().objects.create_user(username="tx_user", password="test1234")
        self.client.login(username="tx_user", password="test1234")

        self.currency, _ = Currency.objects.get_or_create(code="EUR", defaults={"name": "Euro"})
        self.account = Account.objects.create(
            owner=self.user,
            name="Conto principale",
            kind=Account.Kind.BANK,
            currency=self.currency,
            opening_balance=Decimal("0.00"),
            is_active=True,
        )

    def test_dashboard_is_available(self):
        response = self.client.get("/transactions/")
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Transactions Hub")
        self.assertContains(response, "Inserimento rapido")

    def test_create_expense_via_dashboard_quick_form(self):
        response = self.client.post(
            "/transactions/?tx_type=OUT",
            {
                "tx_type": Transaction.Type.EXPENSE,
                "date": "2026-03-06",
                "amount": "22.40",
                "currency": self.currency.id,
                "account": self.account.id,
                "payee_name": "Quick Supplier",
                "source_choice": "",
                "source_name": "",
                "project_choice": "",
                "project_name": "",
                "category_choice": "",
                "category_name": "",
                "note": "Inserimento rapido dashboard",
            },
        )
        self.assertEqual(response.status_code, 302)
        self.assertEqual(response.url, "/transactions/?tx_type=OUT")
        tx = Transaction.objects.get(owner=self.user, note="Inserimento rapido dashboard")
        self.assertEqual(tx.tx_type, Transaction.Type.EXPENSE)
        self.assertEqual(str(tx.amount), "22.40")
        self.assertEqual(tx.payee.name, "Quick Supplier")

    def test_create_expense_via_htmx_partial_form(self):
        response = self.client.post(
            "/transactions/partials/form",
            {
                "tx_type": Transaction.Type.EXPENSE,
                "date": "2026-03-01",
                "amount": "45.90",
                "currency": self.currency.id,
                "account": self.account.id,
                "payee_name": "Fornitore Test",
                "note": "Spesa operativa",
            },
            HTTP_HX_REQUEST="true",
        )

        self.assertEqual(response.status_code, 204)
        self.assertEqual(response.headers.get("HX-Trigger"), "transactions:refresh")

        tx = Transaction.objects.get(owner=self.user, tx_type=Transaction.Type.EXPENSE)
        self.assertEqual(str(tx.amount), "45.90")
        self.assertEqual(tx.payee.name, "Fornitore Test")

    def test_create_income_with_new_source_via_htmx_partial_form(self):
        response = self.client.post(
            "/transactions/partials/form",
            {
                "tx_type": Transaction.Type.INCOME,
                "date": "2026-03-02",
                "amount": "880.00",
                "currency": self.currency.id,
                "account": self.account.id,
                "source_choice": "__new__",
                "source_name": "Cliente Delta",
                "note": "Saldo fattura",
            },
            HTTP_HX_REQUEST="true",
        )

        self.assertEqual(response.status_code, 204)

        tx = Transaction.objects.get(owner=self.user, tx_type=Transaction.Type.INCOME)
        self.assertEqual(str(tx.amount), "880.00")
        self.assertEqual(tx.income_source.name, "Cliente Delta")
        self.assertTrue(IncomeSource.objects.filter(owner=self.user, name="Cliente Delta").exists())

    def test_create_with_new_project_and_category_placeholders(self):
        response = self.client.post(
            "/transactions/partials/form",
            {
                "tx_type": Transaction.Type.EXPENSE,
                "date": "2026-03-04",
                "amount": "120.00",
                "currency": self.currency.id,
                "account": self.account.id,
                "project_choice": "__new__",
                "project_name": "Sito cliente",
                "category_choice": "__new__",
                "category_name": "Servizi",
                "note": "Movimento con creazione rapida",
            },
            HTTP_HX_REQUEST="true",
        )

        self.assertEqual(response.status_code, 204)
        tx = Transaction.objects.get(owner=self.user, note="Movimento con creazione rapida")
        self.assertIsNotNone(tx.project)
        self.assertIsNotNone(tx.category)
        self.assertTrue(tx.project.name.startswith("Nuovo"))
        self.assertIn("Sito cliente", tx.project.name)
        self.assertTrue(tx.category.name.startswith("Nuovo"))
        self.assertIn("Servizi", tx.category.name)
        self.assertTrue(Project.objects.filter(owner=self.user, id=tx.project.id).exists())
        self.assertTrue(Category.objects.filter(owner=self.user, id=tx.category.id).exists())

    def test_delete_transaction_via_htmx_partial(self):
        tx = Transaction.objects.create(
            owner=self.user,
            tx_type=Transaction.Type.EXPENSE,
            date="2026-03-03",
            amount=Decimal("19.90"),
            currency=self.currency,
            account=self.account,
            note="Da eliminare",
        )

        response = self.client.post(
            f"/transactions/partials/delete?id={tx.id}",
            HTTP_HX_REQUEST="true",
        )

        self.assertEqual(response.status_code, 204)
        self.assertFalse(Transaction.objects.filter(id=tx.id, owner=self.user).exists())

    def test_board_partial_supports_legacy_type_filter_param(self):
        Transaction.objects.create(
            owner=self.user,
            tx_type=Transaction.Type.INCOME,
            date="2026-03-01",
            amount=Decimal("100.00"),
            currency=self.currency,
            account=self.account,
            note="entrata visibile",
        )
        Transaction.objects.create(
            owner=self.user,
            tx_type=Transaction.Type.EXPENSE,
            date="2026-03-01",
            amount=Decimal("30.00"),
            currency=self.currency,
            account=self.account,
            note="uscita nascosta",
        )

        response = self.client.get("/transactions/partials/board?type=IN")

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "entrata visibile")
        self.assertNotContains(response, "uscita nascosta")

    def test_form_contains_plus_nuovo_options(self):
        response = self.client.get("/transactions/partials/form?tx_type=OUT")
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "+Nuovo", count=2)
