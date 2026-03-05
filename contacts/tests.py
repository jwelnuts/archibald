from decimal import Decimal

from django.contrib.auth import get_user_model
from django.test import TestCase

from core.models import Payee
from income.models import IncomeSource
from projects.models import Customer

from .models import Contact, ContactPriceList, ContactPriceListItem, ContactToolbox
from .services import sync_contacts_from_legacy


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

    def test_add_contact_redirects_to_safe_next(self):
        self.client.login(username="contacts_user", password="pwd12345")
        response = self.client.post(
            "/contacts/add",
            {
                "display_name": "Nuovo Cliente",
                "entity_type": Contact.EntityType.PERSON,
                "person_name": "Nuovo Cliente",
                "business_name": "",
                "email": "",
                "phone": "",
                "website": "",
                "city": "",
                "role_customer": "on",
                "role_supplier": "",
                "role_payee": "",
                "role_income_source": "",
                "notes": "",
                "is_active": "on",
                "next": "/projects/api/add",
            },
        )
        self.assertEqual(response.status_code, 302)
        self.assertEqual(response.url, "/projects/api/add")

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

    def test_update_contact_can_change_entity_type(self):
        contact = Contact.objects.create(
            owner=self.user,
            display_name="Contatto Tipo",
            entity_type=Contact.EntityType.HYBRID,
            role_customer=True,
        )
        self.client.login(username="contacts_user", password="pwd12345")
        response = self.client.post(
            f"/contacts/update?id={contact.id}",
            {
                "display_name": "Contatto Tipo",
                "entity_type": Contact.EntityType.ENTITY,
                "person_name": "",
                "business_name": "",
                "email": "",
                "phone": "",
                "website": "",
                "city": "",
                "role_customer": "on",
                "role_supplier": "",
                "role_payee": "",
                "role_income_source": "",
                "notes": "",
                "is_active": "on",
            },
        )
        self.assertEqual(response.status_code, 302)
        self.assertEqual(response.url, "/contacts/")

        contact.refresh_from_db()
        self.assertEqual(contact.entity_type, Contact.EntityType.ENTITY)

    def test_sync_from_legacy_does_not_override_manual_entity_type(self):
        contact = Contact.objects.create(
            owner=self.user,
            display_name="Cliente Manuale",
            entity_type=Contact.EntityType.COMPANY,
            role_customer=True,
        )
        Customer.objects.create(owner=self.user, name="Cliente Manuale", email="legacy@example.com")

        sync_contacts_from_legacy(self.user)
        contact.refresh_from_db()

        self.assertEqual(contact.entity_type, Contact.EntityType.COMPANY)


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

    def test_add_price_list_stores_moq_rules(self):
        response = self.client.post(
            f"/contacts/price-lists/add?contact_id={self.contact.id}",
            {
                "title": "Listino Spring",
                "currency_code": "EUR",
                "pricing_notes": "MOQ standard 10 pezzi",
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
                "items-0-min_quantity": "10",
                "items-0-max_quantity": "",
                "items-0-unit_price": "5.00",
                "items-0-is_active": "on",
            },
        )
        self.assertEqual(response.status_code, 302)
        self.assertEqual(response.url, f"/contacts/toolbox?id={self.contact.id}")

        price_list = ContactPriceList.objects.get(owner=self.user, title="Listino Spring")
        self.assertEqual(price_list.pricing_notes, "MOQ standard 10 pezzi")
        self.assertEqual(price_list.items.count(), 1)
        item = price_list.items.first()
        self.assertEqual(item.min_quantity, Decimal("10.00"))
        self.assertIsNone(item.max_quantity)
        self.assertEqual(item.unit_price, Decimal("5.00"))

    def test_update_price_list_updates_quantity_range(self):
        toolbox = ContactToolbox.objects.create(owner=self.user, contact=self.contact)
        price_list = ContactPriceList.objects.create(
            owner=self.user,
            toolbox=toolbox,
            title="Listino Base",
            currency_code="EUR",
            pricing_notes="MOQ da definire",
        )
        item = ContactPriceListItem.objects.create(
            owner=self.user,
            price_list=price_list,
            row_order=1,
            title="Voce",
            min_quantity=Decimal("1.00"),
            max_quantity=Decimal("9.00"),
            unit_price=Decimal("12.00"),
        )

        response = self.client.post(
            f"/contacts/price-lists/update?id={price_list.id}",
            {
                "title": "Listino Base",
                "currency_code": "EUR",
                "pricing_notes": "MOQ da 10 pezzi",
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
                "items-0-min_quantity": "10.00",
                "items-0-max_quantity": "99.00",
                "items-0-unit_price": "9.50",
                "items-0-is_active": "on",
            },
        )

        self.assertEqual(response.status_code, 302)
        self.assertEqual(response.url, f"/contacts/toolbox?id={self.contact.id}")

        price_list.refresh_from_db()
        item.refresh_from_db()
        self.assertEqual(price_list.pricing_notes, "MOQ da 10 pezzi")
        self.assertEqual(item.min_quantity, Decimal("10.00"))
        self.assertEqual(item.max_quantity, Decimal("99.00"))
        self.assertEqual(item.unit_price, Decimal("9.50"))
        self.assertTrue(item.matches_quantity(Decimal("12.00")))
