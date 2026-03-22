import json
import tempfile
from types import SimpleNamespace
from unittest.mock import patch
from pathlib import Path

from django.contrib.auth import get_user_model
from django.test import TestCase, override_settings
from passlib.hash import bcrypt

from core.models import DavAccount
from .app_builder import (
    AppBuilderError,
    FieldSpec,
    build_model_fields,
    normalize_app_name,
    parse_spec,
    run_post_generation_setup,
)
from .models import DebugChangeLog
from .orphan_cleanup import (
    remove_app_from_settings_text,
    remove_app_from_urls_text,
)


class AppBuilderTests(TestCase):
    def test_normalize_app_name_rejects_existing(self):
        with self.assertRaises(AppBuilderError):
            normalize_app_name("workbench")

    def test_parse_spec_uses_defaults_when_invalid(self):
        spec = parse_spec({"fields": "bad"}, "custom_app")
        self.assertEqual(spec.model_name, "CustomApp")
        self.assertGreaterEqual(len(spec.fields), 1)

    def test_build_model_fields_for_choice(self):
        lines = build_model_fields(
            [
                FieldSpec(
                    name="status",
                    kind="choice",
                    required=True,
                    choices=["OPEN", "DONE"],
                )
            ]
        )
        rendered = "\n".join(lines)
        self.assertIn("STATUS_CHOICES", rendered)
        self.assertIn("default=\"OPEN\"", rendered)

    @patch("workbench.app_builder.subprocess.run")
    def test_run_post_generation_setup_ok(self, mocked_run):
        mocked_run.side_effect = [
            SimpleNamespace(returncode=0, stdout="makemigrations ok"),
            SimpleNamespace(returncode=0, stdout="migrate ok"),
        ]

        result = run_post_generation_setup("demo_app")

        self.assertTrue(result.ok)
        self.assertEqual(len(result.steps), 2)
        self.assertTrue(all(step.ok for step in result.steps))
        self.assertIn("makemigrations demo_app --noinput", result.steps[0].command)
        self.assertIn("migrate --noinput", result.steps[1].command)

    @patch("workbench.app_builder.subprocess.run")
    def test_run_post_generation_setup_stops_on_failure(self, mocked_run):
        mocked_run.side_effect = [
            SimpleNamespace(returncode=1, stdout="makemigrations failed"),
            SimpleNamespace(returncode=0, stdout="migrate ok"),
        ]

        result = run_post_generation_setup("demo_app")

        self.assertFalse(result.ok)
        self.assertEqual(len(result.steps), 1)
        self.assertFalse(result.steps[0].ok)
        self.assertEqual(mocked_run.call_count, 1)

    def test_cleanup_settings_text_removes_app_entry(self):
        source = "INSTALLED_APPS = [\n    'core',\n    'fileholder',\n    'workbench',\n]\n"
        updated, removed = remove_app_from_settings_text(source, "fileholder")
        self.assertEqual(removed, 1)
        self.assertNotIn("'fileholder'", updated)

    def test_cleanup_urls_text_removes_app_route(self):
        source = (
            "urlpatterns = [\n"
            "    path('', include('core.urls')),\n"
            "    path('fileholder/', include('fileholder.urls')),\n"
            "]\n"
        )
        updated, removed = remove_app_from_urls_text(source, "fileholder")
        self.assertEqual(removed, 1)
        self.assertNotIn("fileholder.urls", updated)


class WorkbenchCleanupViewTests(TestCase):
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

    def test_superuser_can_cleanup_orphan_logs(self):
        user = get_user_model().objects.create_user(
            username="admin",
            email="admin@example.com",
            password="test1234",
            is_superuser=True,
            is_staff=True,
        )
        DebugChangeLog.objects.create(
            user=user,
            source="workbench.ai_app_generator",
            action=DebugChangeLog.Action.CUSTOM,
            app_label="fileholder",
            model_name="FileHolder",
            object_id="-",
            note="orphan app test",
        )
        self.client.force_login(user)

        response = self.client.post(
            "/workbench/api/cleanup-generated-app",
            {"app_label": "fileholder", "mode": "logs"},
        )

        self.assertEqual(response.status_code, 302)
        self.assertEqual(response.headers.get("Location"), "/workbench/")
        self.assertFalse(
            DebugChangeLog.objects.filter(app_label="fileholder").exists()
        )

    def test_non_superuser_cannot_cleanup_orphan_logs(self):
        user = get_user_model().objects.create_user(
            username="user",
            email="user@example.com",
            password="test1234",
        )
        self.client.force_login(user)
        response = self.client.post(
            "/workbench/api/cleanup-generated-app",
            {"app_label": "fileholder", "mode": "logs"},
        )
        self.assertEqual(response.status_code, 403)


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
