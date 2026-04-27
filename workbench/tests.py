import json
import tempfile
from pathlib import Path

from django.contrib.auth import get_user_model
from django.test import TestCase, override_settings
from passlib.hash import bcrypt

from core.models import DavAccount


class WorkbenchDashboardAuthTests(TestCase):
    def test_dashboard_redirects_anonymous_user_to_login(self):
        response = self.client.get("/workbench/")
        self.assertEqual(response.status_code, 302)
        self.assertIn("/accounts/login/", response.headers.get("Location", ""))

    def test_dashboard_forbids_non_superuser(self):
        user = get_user_model().objects.create_user(
            username="basic_user",
            email="basic@example.com",
            password="test1234",
        )
        self.client.force_login(user)
        response = self.client.get("/workbench/")
        self.assertEqual(response.status_code, 403)

    def test_dashboard_allows_superuser(self):
        user = get_user_model().objects.create_user(
            username="admin_dashboard",
            email="admin_dashboard@example.com",
            password="test1234",
            is_superuser=True,
            is_staff=True,
        )
        self.client.force_login(user)
        response = self.client.get("/workbench/")
        self.assertEqual(response.status_code, 200)


class WorkbenchDavControlPanelTests(TestCase):
    def setUp(self):
        self.admin = get_user_model().objects.create_user(
            username="wb_admin",
            email="wb_admin@example.com",
            password="test1234",
            is_superuser=True,
            is_staff=True,
        )
        self.client.force_login(self.admin)
        self.tempdir = tempfile.TemporaryDirectory()
        self.addCleanup(self.tempdir.cleanup)
        self.users_file = Path(self.tempdir.name) / "users"
        self.lock_file = Path(self.tempdir.name) / "users.lock"

    @override_settings(
        CALDAV_SERVICE_USERNAME="archibald",
        CALDAV_SERVICE_PASSWORD="service-password-123",
    )
    def test_sync_users_file_action_creates_htpasswd(self):
        with override_settings(
            RADICALE_USERS_FILE=str(self.users_file),
            RADICALE_USERS_LOCK_FILE=str(self.lock_file),
        ):
            response = self.client.post(
                "/workbench/debug/radicale",
                {"action": "sync_users_file"},
            )
            self.assertEqual(response.status_code, 302)
            self.assertEqual(response.headers.get("Location"), "/workbench/debug/radicale")
            self.assertTrue(self.users_file.exists())
            content = self.users_file.read_text(encoding="utf-8")
            self.assertIn("archibald:$2", content)

    def test_create_user_calendar_action_creates_collection_props(self):
        app_user = get_user_model().objects.create_user(
            username="dav_user",
            email="dav_user@example.com",
            password="test1234",
        )
        DavAccount.objects.create(
            user=app_user,
            dav_username="dav_user",
            password_hash=bcrypt.hash("test1234"),
            is_active=True,
        )

        with override_settings(
            RADICALE_USERS_FILE=str(self.users_file),
            RADICALE_USERS_LOCK_FILE=str(self.lock_file),
        ):
            response = self.client.post(
                "/workbench/debug/radicale",
                {
                    "action": "create_user_calendar",
                    "principal": "dav_user",
                    "calendar_slug": "lavoro",
                    "display_name": "Calendario Lavoro",
                },
            )
            self.assertEqual(response.status_code, 302)
            self.assertEqual(response.headers.get("Location"), "/workbench/debug/radicale")

            props_path = (
                Path(self.tempdir.name)
                / "collections"
                / "collection-root"
                / "dav_user"
                / "lavoro"
                / ".Radicale.props"
            )
            self.assertTrue(props_path.exists())
            payload = json.loads(props_path.read_text(encoding="utf-8"))
            self.assertEqual(payload.get("tag"), "VCALENDAR")
            self.assertEqual(payload.get("D:displayname"), "Calendario Lavoro")