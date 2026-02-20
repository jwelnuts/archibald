from django.contrib.auth import get_user_model
from django.test import TestCase

from core.models import Payee
from income.models import IncomeSource
from projects.models import Customer

from .models import Contact


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
