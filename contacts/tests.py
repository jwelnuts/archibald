from decimal import Decimal

from django.contrib.auth import get_user_model
from django.test import TestCase

from core.models import Payee
from income.models import IncomeSource
from projects.models import Customer

from .models import Contact, ContactPriceList, ContactPriceListItem, ContactToolbox


class ContactsViewsTests(TestCase):
    def setUp(self):
        self.user = get_user_model().objects.create_user(username="contacts_user", password="pwd12345")

    def test_dashboard_requires_login(self):
        response = self.client.get("/contacts/")
        self.assertEqual(response.status_code, 302)
        self.assertIn("/accounts/login/", response.url)

    def test_add_contact_creates_contact_and_legacy_records(self):
        self.client.login(username="contacts_user", password="pwd12345")
        response = self.client.post(
            "/contacts/add",
            {
                "display_name": "Erik - Bar Aurora",
                "entity_type": Contact.EntityType.HYBRID,
                "person_name": "Erik",
                "business_name": "Bar Aurora",
                "email": "erik@example.com",
                "phone": "123456",
                "website": "https://baraurora.example.com",
                "city": "Torino",
                "role_customer": "on",
                "role_supplier": "on",
                "role_payee": "on",
                "role_income_source": "",
                "notes": "Contatto multidimensionale",
                "is_active": "on",
            },
        )
        self.assertEqual(response.status_code, 302)
        self.assertEqual(response.url, "/contacts/")
        self.assertTrue(Contact.objects.filter(owner=self.user, display_name="Erik - Bar Aurora").exists())
        self.assertTrue(Customer.objects.filter(owner=self.user, name="Erik - Bar Aurora").exists())
        self.assertTrue(Payee.objects.filter(owner=self.user, name="Erik - Bar Aurora").exists())

    def test_dashboard_syncs_legacy_records(self):
        Customer.objects.create(owner=self.user, name="Cliente Legacy", email="legacy@example.com")
        Payee.objects.create(owner=self.user, name="Fornitore Legacy")
        IncomeSource.objects.create(owner=self.user, name="Fonte Legacy")

        self.client.login(username="contacts_user", password="pwd12345")
        response = self.client.get("/contacts/")
        self.assertEqual(response.status_code, 200)
        self.assertTrue(Contact.objects.filter(owner=self.user, display_name="Cliente Legacy", role_customer=True).exists())
        self.assertTrue(Contact.objects.filter(owner=self.user, display_name="Fornitore Legacy", role_payee=True).exists())
        self.assertTrue(
            Contact.objects.filter(owner=self.user, display_name="Fonte Legacy", role_income_source=True).exists()
        )


class ContactToolboxPriceListTests(TestCase):
    def setUp(self):
        self.user = get_user_model().objects.create_user(username="contact_tools_user", password="pwd12345")
        self.client.login(username="contact_tools_user", password="pwd12345")
        self.contact = Contact.objects.create(
            owner=self.user,
            display_name="Cliente Test",
            entity_type=Contact.EntityType.HYBRID,
            role_customer=True,
        )

    def test_toolbox_view_creates_container(self):
        response = self.client.get(f"/contacts/toolbox?id={self.contact.id}")
        self.assertEqual(response.status_code, 200)
        self.assertTrue(ContactToolbox.objects.filter(owner=self.user, contact=self.contact).exists())

    def test_add_price_list_calculates_totals(self):
        response = self.client.post(
            f"/contacts/price-lists/add?contact_id={self.contact.id}",
            {
                "title": "Listino Spring",
                "currency_code": "EUR",
                "vat_rate": "22.00",
                "is_active": "on",
                "note": "Listino dedicato",
                "items-TOTAL_FORMS": "1",
                "items-INITIAL_FORMS": "0",
                "items-MIN_NUM_FORMS": "0",
                "items-MAX_NUM_FORMS": "1000",
                "items-0-row_order": "1",
                "items-0-code": "A-001",
                "items-0-title": "Servizio X",
                "items-0-description": "Dettaglio",
                "items-0-quantity": "10",
                "items-0-unit_price_net": "5.00",
                "items-0-discount": "10.00",
            },
        )
        self.assertEqual(response.status_code, 302)
        self.assertEqual(response.url, f"/contacts/toolbox?id={self.contact.id}")

        price_list = ContactPriceList.objects.get(owner=self.user, title="Listino Spring")
        self.assertEqual(price_list.subtotal_net, Decimal("45.00"))
        self.assertEqual(price_list.tax_amount, Decimal("9.90"))
        self.assertEqual(price_list.total_amount, Decimal("54.90"))
        self.assertEqual(price_list.items.count(), 1)

    def test_update_price_list_recalculates_totals(self):
        toolbox = ContactToolbox.objects.create(owner=self.user, contact=self.contact)
        price_list = ContactPriceList.objects.create(
            owner=self.user,
            toolbox=toolbox,
            title="Listino Base",
            currency_code="EUR",
            vat_rate=Decimal("22.00"),
        )
        item = ContactPriceListItem.objects.create(
            owner=self.user,
            price_list=price_list,
            row_order=1,
            title="Voce",
            quantity=Decimal("2.00"),
            unit_price_net=Decimal("10.00"),
            discount=Decimal("0.00"),
        )

        response = self.client.post(
            f"/contacts/price-lists/update?id={price_list.id}",
            {
                "title": "Listino Base",
                "currency_code": "EUR",
                "vat_rate": "10.00",
                "is_active": "on",
                "note": "",
                "items-TOTAL_FORMS": "1",
                "items-INITIAL_FORMS": "1",
                "items-MIN_NUM_FORMS": "0",
                "items-MAX_NUM_FORMS": "1000",
                "items-0-id": str(item.id),
                "items-0-row_order": "1",
                "items-0-code": "",
                "items-0-title": "Voce",
                "items-0-description": "",
                "items-0-quantity": "3.00",
                "items-0-unit_price_net": "15.00",
                "items-0-discount": "0.00",
            },
        )

        self.assertEqual(response.status_code, 302)
        self.assertEqual(response.url, f"/contacts/toolbox?id={self.contact.id}")

        price_list.refresh_from_db()
        self.assertEqual(price_list.subtotal_net, Decimal("45.00"))
        self.assertEqual(price_list.tax_amount, Decimal("4.50"))
        self.assertEqual(price_list.total_amount, Decimal("49.50"))
