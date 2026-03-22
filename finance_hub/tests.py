from datetime import date, timedelta
from decimal import Decimal

from django.contrib.auth import get_user_model
from django.test import TestCase
from django.utils import timezone

from contacts.models import Contact, ContactDeliveryAddress
from projects.models import Customer
from .models import PaymentMethod, Quote, ShippingMethod, VatCode
from subscriptions.models import Currency


class FinanceHubViewsTests(TestCase):
    def setUp(self):
        self.user = get_user_model().objects.create_user(username="finance", password="pwd12345")
        self.currency, _ = Currency.objects.get_or_create(code="EUR", defaults={"name": "Euro"})
        self.vat_22 = VatCode.objects.create(
            owner=self.user,
            code="22",
            description="IVA ordinaria",
            rate=Decimal("22.00"),
            is_active=True,
        )

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
                "vat_code": self.vat_22.id,
                "amount_net": "1000.00",
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
                "lines-0-quantity": "1.00",
                "lines-0-discount": "0.00",
            },
        )
        self.assertEqual(response.status_code, 302)
        self.assertEqual(response.url, "/finance/quotes/")
        item = Quote.objects.get(owner=self.user, code="PREV-001")
        self.assertEqual(str(item.total_amount), "1220.00")
        self.assertEqual(str(item.tax_amount), "220.00")
        self.assertEqual(item.vat_code_id, self.vat_22.id)
        self.assertEqual(item.lines.count(), 1)

    def test_add_quote_can_select_delivery_address(self):
        self.client.login(username="finance", password="pwd12345")
        customer = Customer.objects.create(owner=self.user, name="Cliente Consegne")
        payment_method = PaymentMethod.objects.create(owner=self.user, name="Bonifico bancario", is_active=True)
        shipping_method = ShippingMethod.objects.create(owner=self.user, name="Corriere espresso", is_active=True)
        contact = Contact.objects.create(
            owner=self.user,
            display_name=customer.name,
            entity_type=Contact.EntityType.COMPANY,
            role_customer=True,
        )
        delivery_address = ContactDeliveryAddress.objects.create(
            owner=self.user,
            contact=contact,
            label="Magazzino Centrale",
            recipient_name="Ricezione merci",
            line1="Via Logistica 10",
            postal_code="20100",
            city="Milano",
            province="MI",
            country="Italia",
            is_default=True,
            is_active=True,
        )

        response = self.client.post(
            "/finance/quotes/add",
            data={
                "code": "PREV-DEL-001",
                "title": "Preventivo con destinazione",
                "customer": customer.id,
                "delivery_address": delivery_address.id,
                "payment_method": payment_method.id,
                "shipping_method": shipping_method.id,
                "issue_date": "2026-03-22",
                "valid_until": "2026-04-10",
                "currency": self.currency.id,
                "vat_code": self.vat_22.id,
                "amount_net": "250.00",
                "status": Quote.Status.SENT,
                "note": "",
                "lines-TOTAL_FORMS": "1",
                "lines-INITIAL_FORMS": "0",
                "lines-MIN_NUM_FORMS": "0",
                "lines-MAX_NUM_FORMS": "1000",
                "lines-0-row_order": "1",
                "lines-0-code": "ART-DEL",
                "lines-0-description": "Merce pronta",
                "lines-0-net_amount": "250.00",
                "lines-0-quantity": "1.00",
                "lines-0-discount": "0.00",
            },
        )

        self.assertEqual(response.status_code, 302)
        quote = Quote.objects.get(owner=self.user, code="PREV-DEL-001")
        self.assertEqual(quote.customer_id, customer.id)
        self.assertEqual(quote.delivery_address_id, delivery_address.id)
        self.assertEqual(quote.payment_method_id, payment_method.id)
        self.assertEqual(quote.shipping_method_id, shipping_method.id)

    def test_lists_are_available_for_logged_user(self):
        self.client.login(username="finance", password="pwd12345")
        for url in ("/finance/quotes/", "/finance/invoices/", "/finance/work-orders/", "/finance/vat-codes/"):
            response = self.client.get(url)
            self.assertEqual(response.status_code, 200, url)

    def test_share_link_issues_public_token(self):
        self.client.login(username="finance", password="pwd12345")
        quote = Quote.objects.create(
            owner=self.user,
            code="PREV-SHARE-001",
            title="Preventivo condivisibile",
            issue_date=date(2026, 3, 22),
            valid_until=date(2026, 4, 22),
            currency=self.currency,
            vat_code=self.vat_22,
            amount_net=Decimal("100.00"),
            status=Quote.Status.SENT,
        )

        response = self.client.get(f"/finance/quotes/share?id={quote.id}")
        self.assertEqual(response.status_code, 200)
        quote.refresh_from_db()
        self.assertTrue(quote.public_access_token)
        self.assertContains(response, f"/finance/quotes/confirm/{quote.public_access_token}")

    def test_public_confirmation_updates_quote_signature(self):
        customer = Customer.objects.create(owner=self.user, name="Cliente Public", email="old@example.com")
        contact = Contact.objects.create(
            owner=self.user,
            display_name=customer.name,
            entity_type=Contact.EntityType.COMPANY,
            role_customer=True,
        )
        delivery = ContactDeliveryAddress.objects.create(
            owner=self.user,
            contact=contact,
            label="Sede",
            line1="Via Uno 1",
            city="Milano",
            country="Italia",
            is_active=True,
        )
        quote = Quote.objects.create(
            owner=self.user,
            code="PREV-SIGN-001",
            title="Preventivo firma",
            customer=customer,
            delivery_address=delivery,
            issue_date=date(2026, 3, 22),
            valid_until=date(2026, 4, 22),
            currency=self.currency,
            vat_code=self.vat_22,
            amount_net=Decimal("200.00"),
            status=Quote.Status.SENT,
        )
        token = quote.issue_public_access()

        response = self.client.post(
            f"/finance/quotes/confirm/{token}",
            data={
                "signer_name": "Mario Rossi",
                "customer_name": "Cliente Public SRL",
                "customer_email": "new@example.com",
                "customer_phone": "+39 3331234567",
                "customer_notes": "Aggiornato dal cliente",
                "delivery_label": "Magazzino",
                "delivery_recipient_name": "Ufficio acquisti",
                "delivery_line1": "Via Nuova 10",
                "delivery_line2": "Scala B",
                "delivery_postal_code": "20100",
                "delivery_city": "Milano",
                "delivery_province": "MI",
                "delivery_country": "Italia",
                "decision": "approve",
            },
        )
        self.assertEqual(response.status_code, 200)
        quote.refresh_from_db()
        quote.customer.refresh_from_db()
        quote.delivery_address.refresh_from_db()
        self.assertEqual(quote.status, Quote.Status.APPROVED)
        self.assertEqual(quote.customer_signed_name, "Mario Rossi")
        self.assertIsNotNone(quote.customer_signed_at)
        self.assertEqual(quote.customer.name, "Cliente Public SRL")
        self.assertEqual(quote.customer.email, "new@example.com")
        self.assertEqual(quote.delivery_address.label, "Magazzino")
        self.assertEqual(quote.delivery_address.line1, "Via Nuova 10")
        self.assertEqual(quote.customer_decision_note, "")

    def test_public_reject_requires_reason(self):
        quote = Quote.objects.create(
            owner=self.user,
            code="PREV-REJECT-001",
            title="Preventivo rifiutabile",
            issue_date=date(2026, 3, 22),
            valid_until=date(2026, 4, 22),
            currency=self.currency,
            vat_code=self.vat_22,
            amount_net=Decimal("120.00"),
            status=Quote.Status.SENT,
        )
        token = quote.issue_public_access()

        response = self.client.post(
            f"/finance/quotes/confirm/{token}",
            data={
                "signer_name": "Mario Rossi",
                "customer_name": "Cliente Public",
                "decision": "reject",
                "reject_reason": "",
            },
        )
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Inserisci la motivazione del rifiuto.")
        quote.refresh_from_db()
        self.assertEqual(quote.status, Quote.Status.SENT)
        self.assertIsNone(quote.customer_signed_at)

    def test_public_reject_stores_reason(self):
        quote = Quote.objects.create(
            owner=self.user,
            code="PREV-REJECT-002",
            title="Preventivo rifiutabile",
            issue_date=date(2026, 3, 22),
            valid_until=date(2026, 4, 22),
            currency=self.currency,
            vat_code=self.vat_22,
            amount_net=Decimal("120.00"),
            status=Quote.Status.SENT,
        )
        token = quote.issue_public_access()

        response = self.client.post(
            f"/finance/quotes/confirm/{token}",
            data={
                "signer_name": "Mario Rossi",
                "customer_name": "Cliente Public",
                "decision": "reject",
                "reject_reason": "Prezzo non in linea con il budget.",
            },
        )
        self.assertEqual(response.status_code, 200)
        quote.refresh_from_db()
        self.assertEqual(quote.status, Quote.Status.REJECTED)
        self.assertEqual(quote.customer_decision_note, "Prezzo non in linea con il budget.")
        self.assertEqual(quote.customer_signed_name, "Mario Rossi")
        self.assertIsNotNone(quote.customer_signed_at)

    def test_quote_pdf_download_works_for_owner_and_public(self):
        self.client.login(username="finance", password="pwd12345")
        quote = Quote.objects.create(
            owner=self.user,
            code="PREV-PDF-001",
            title="Preventivo PDF",
            issue_date=date(2026, 3, 22),
            valid_until=date(2026, 4, 22),
            currency=self.currency,
            vat_code=self.vat_22,
            amount_net=Decimal("300.00"),
            status=Quote.Status.SENT,
        )
        token = quote.issue_public_access()

        owner_pdf = self.client.get(f"/finance/quotes/pdf?id={quote.id}")
        self.assertEqual(owner_pdf.status_code, 200)
        self.assertEqual(owner_pdf["Content-Type"], "application/pdf")
        self.assertTrue(owner_pdf.content.startswith(b"%PDF-1.4"))

        public_pdf = self.client.get(f"/finance/quotes/confirm/{token}/pdf")
        self.assertEqual(public_pdf.status_code, 200)
        self.assertEqual(public_pdf["Content-Type"], "application/pdf")

    def test_public_link_expiration_blocks_access(self):
        quote = Quote.objects.create(
            owner=self.user,
            code="PREV-EXP-001",
            title="Preventivo scaduto",
            issue_date=date(2026, 3, 22),
            valid_until=date(2026, 4, 22),
            currency=self.currency,
            vat_code=self.vat_22,
            amount_net=Decimal("80.00"),
            status=Quote.Status.SENT,
            public_access_token="expired-token-demo",
            public_access_expires_at=timezone.now() - timedelta(hours=2),
        )

        response = self.client.get(f"/finance/quotes/confirm/{quote.public_access_token}")
        self.assertEqual(response.status_code, 410)
