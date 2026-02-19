from django.contrib.auth import get_user_model
from django.test import TestCase

from .models import Quote
from subscriptions.models import Currency


class FinanceHubViewsTests(TestCase):
    def setUp(self):
        self.user = get_user_model().objects.create_user(username="finance", password="pwd12345")
        self.currency, _ = Currency.objects.get_or_create(code="EUR", defaults={"name": "Euro"})

    def test_dashboard_requires_login(self):
        response = self.client.get("/finance/")
        self.assertEqual(response.status_code, 302)
        self.assertIn("/accounts/login/", response.url)

    def test_add_quote_creates_record(self):
        self.client.login(username="finance", password="pwd12345")
        response = self.client.post(
            "/finance/quotes/add",
            data={
                "code": "PREV-001",
                "title": "Preventivo sito web",
                "issue_date": "2026-02-19",
                "valid_until": "2026-03-10",
                "currency": self.currency.id,
                "amount_net": "1000.00",
                "tax_amount": "220.00",
                "status": Quote.Status.SENT,
                "note": "Prima versione.",
                "lines-TOTAL_FORMS": "1",
                "lines-INITIAL_FORMS": "0",
                "lines-MIN_NUM_FORMS": "0",
                "lines-MAX_NUM_FORMS": "1000",
                "lines-0-row_order": "1",
                "lines-0-code": "ART-001",
                "lines-0-description": "Sviluppo landing page",
                "lines-0-net_amount": "1000.00",
                "lines-0-gross_amount": "1220.00",
                "lines-0-quantity": "1.00",
                "lines-0-discount": "0.00",
                "lines-0-vat_code": "22",
            },
        )
        self.assertEqual(response.status_code, 302)
        self.assertEqual(response.url, "/finance/quotes/")
        item = Quote.objects.get(owner=self.user, code="PREV-001")
        self.assertEqual(str(item.total_amount), "1220.00")
        self.assertEqual(item.lines.count(), 1)

    def test_lists_are_available_for_logged_user(self):
        self.client.login(username="finance", password="pwd12345")
        for url in ("/finance/quotes/", "/finance/invoices/", "/finance/work-orders/"):
            response = self.client.get(url)
            self.assertEqual(response.status_code, 200, url)
