import pyotp
from django.contrib.auth import get_user_model
from django.test import TestCase
from django.utils import timezone

from .models import VaultItem, VaultProfile


class VaultFlowTests(TestCase):
    def setUp(self):
        self.user = get_user_model().objects.create_user(username="vault_user", password="test1234")
        self.client.login(username="vault_user", password="test1234")

    def _create_enabled_profile(self) -> VaultProfile:
        profile = VaultProfile.objects.create(owner=self.user, totp_enabled_at=timezone.now())
        profile.set_totp_secret(pyotp.random_base32())
        profile.save(update_fields=["totp_secret_encrypted", "updated_at"])
        return profile

    def test_dashboard_redirects_to_setup_without_totp(self):
        response = self.client.get("/vault/")
        self.assertEqual(response.status_code, 302)
        self.assertIn("/vault/setup", response.url)

    def test_setup_totp_enables_vault(self):
        response = self.client.get("/vault/setup")
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "data:image/svg+xml;base64,")
        profile = VaultProfile.objects.get(owner=self.user)
        code = pyotp.TOTP(profile.get_totp_secret()).now()
        response = self.client.post("/vault/setup", {"code": code})
        self.assertEqual(response.status_code, 302)
        profile.refresh_from_db()
        self.assertIsNotNone(profile.totp_enabled_at)

    def test_unlock_and_create_item(self):
        profile = self._create_enabled_profile()
        response = self.client.get("/vault/")
        self.assertEqual(response.status_code, 302)
        self.assertIn("/vault/unlock", response.url)

        code = pyotp.TOTP(profile.get_totp_secret()).now()
        response = self.client.post("/vault/unlock", {"code": code})
        self.assertEqual(response.status_code, 302)

        response = self.client.post(
            "/vault/api/add",
            {
                "title": "GitHub",
                "kind": VaultItem.Kind.PASSWORD,
                "login": "me@example.com",
                "website_url": "https://github.com",
                "secret_value": "MyStrongPass!42",
                "notes_value": "2FA attivo",
            },
        )
        self.assertEqual(response.status_code, 302)
        item = VaultItem.objects.get(owner=self.user, title="GitHub")
        self.assertNotEqual(item.secret_encrypted, "MyStrongPass!42")
        self.assertEqual(item.get_secret_value(), "MyStrongPass!42")

    def test_setup_is_blocked_after_totp_enabled(self):
        self._create_enabled_profile()
        response = self.client.get("/vault/setup")
        self.assertEqual(response.status_code, 302)
        self.assertIn("/vault/unlock", response.url)
