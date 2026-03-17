import json
import tempfile
from datetime import timedelta
from pathlib import Path

from django.contrib.auth import get_user_model
from django.test import TestCase, override_settings
from django.utils import timezone

from ai_lab.models import ArchibaldInstructionState, ArchibaldPersonaConfig
from planner.models import PlannerItem
from routines.models import Routine, RoutineCategory, RoutineItem, RoutineCheck
from todo.models import Task
from .models import DavAccount, MobileApiSession, UserNavConfig
from .views import DEFAULT_DASHBOARD_WIDGET_IDS


class ProfileArchibaldInstructionsTests(TestCase):
    def setUp(self):
        self.user = get_user_model().objects.create_user(username="profile_user", password="test12345")

    def test_profile_requires_login(self):
        response = self.client.get("/profile/")
        self.assertEqual(response.status_code, 302)
        self.assertIn("/accounts/login/", response.url)

    def test_save_archibald_custom_instructions(self):
        self.client.login(username="profile_user", password="test12345")
        response = self.client.post(
            "/profile/",
            {
                "action": "save_archibald_instructions",
                "archibald_custom_instructions": "Sii diretto e focalizzato su azioni pratiche.",
            },
        )
        self.assertEqual(response.status_code, 302)
        persona = ArchibaldPersonaConfig.objects.get(owner=self.user)
        self.assertEqual(persona.custom_instructions, "Sii diretto e focalizzato su azioni pratiche.")

    def test_save_apply_and_delete_archibald_state(self):
        self.client.login(username="profile_user", password="test12345")

        response = self.client.post(
            "/profile/",
            {
                "action": "save_archibald_state",
                "state_name": "Operativo Secco",
                "archibald_custom_instructions": "No frasi decorative, vai dritto ai tradeoff.",
            },
        )
        self.assertEqual(response.status_code, 302)
        state = ArchibaldInstructionState.objects.get(owner=self.user, name="Operativo Secco")

        response = self.client.post(
            "/profile/",
            {
                "action": "save_archibald_instructions",
                "archibald_custom_instructions": "Versione temporanea diversa.",
            },
        )
        self.assertEqual(response.status_code, 302)

        response = self.client.post(
            "/profile/",
            {
                "action": "apply_archibald_state",
                "state_id": state.id,
            },
        )
        self.assertEqual(response.status_code, 302)
        persona = ArchibaldPersonaConfig.objects.get(owner=self.user)
        self.assertEqual(persona.custom_instructions, "No frasi decorative, vai dritto ai tradeoff.")

        response = self.client.post(
            "/profile/",
            {
                "action": "delete_archibald_state",
                "state_id": state.id,
            },
        )
        self.assertEqual(response.status_code, 302)
        self.assertFalse(ArchibaldInstructionState.objects.filter(owner=self.user, id=state.id).exists())

    def test_save_bias_settings(self):
        self.client.login(username="profile_user", password="test12345")
        response = self.client.post(
            "/profile/",
            {
                "action": "save_bias_settings",
                "bias_catastrophizing": "on",
                "bias_all_or_nothing": "",
                "bias_overgeneralization": "on",
                "bias_mind_reading": "",
                "bias_negative_filtering": "on",
                "bias_confirmation_bias": "on",
            },
        )
        self.assertEqual(response.status_code, 302)
        persona = ArchibaldPersonaConfig.objects.get(owner=self.user)
        self.assertTrue(persona.bias_catastrophizing)
        self.assertFalse(persona.bias_all_or_nothing)
        self.assertTrue(persona.bias_overgeneralization)
        self.assertFalse(persona.bias_mind_reading)
        self.assertTrue(persona.bias_negative_filtering)
        self.assertTrue(persona.bias_confirmation_bias)


class DavProvisioningTests(TestCase):
    def setUp(self):
        self._tmpdir = tempfile.TemporaryDirectory()
        self.addCleanup(self._tmpdir.cleanup)
        users_file = Path(self._tmpdir.name) / "users"
        lock_file = Path(self._tmpdir.name) / "users.lock"
        self._override = override_settings(
            CALDAV_ENABLED=True,
            CALDAV_BASE_URL="http://localhost:5232/",
            CALDAV_LOGIN_DOMAIN="miorganizzo.ovh",
            CALDAV_SERVICE_USERNAME="archibald",
            CALDAV_SERVICE_PASSWORD="archibald-service-pass",
            RADICALE_USERS_FILE=str(users_file),
            RADICALE_USERS_LOCK_FILE=str(lock_file),
        )
        self._override.enable()
        self.addCleanup(self._override.disable)
        self.users_file = users_file

    def test_signup_provisions_user_and_writes_hashed_users_file(self):
        response = self.client.post(
            "/accounts/signup/",
            {
                "username": "renee",
                "email": "renee.suman@miorganizzo.ovh",
                "password1": "testpass12345A!",
                "password2": "testpass12345A!",
            },
        )
        self.assertEqual(response.status_code, 302)
        self.assertTrue(response.url.startswith("/profile/"))

        user = get_user_model().objects.get(username="renee")
        account = DavAccount.objects.get(user=user)
        self.assertEqual(account.dav_username, "renee@miorganizzo.ovh")

        session = self.client.session
        onboarding = session.get("dav_onboarding")
        self.assertIsNotNone(onboarding)
        self.assertEqual(onboarding.get("username"), "renee@miorganizzo.ovh")
        issued_password = onboarding.get("password")
        self.assertTrue(issued_password)

        content = self.users_file.read_text(encoding="utf-8")
        self.assertIn("renee@miorganizzo.ovh:{SSHA}", content)
        self.assertIn("archibald:{SSHA}", content)
        self.assertNotIn(issued_password, content)

    def test_profile_rotate_dav_password_updates_hash_and_onboarding_secret(self):
        user = get_user_model().objects.create_user(username="martina", password="testpass12345A!")
        self.client.login(username="martina", password="testpass12345A!")
        self.client.post("/profile/", {"action": "rotate_dav_password"})
        original_hash = DavAccount.objects.get(user=user).password_hash

        rotate = self.client.post("/profile/", {"action": "rotate_dav_password"})
        self.assertEqual(rotate.status_code, 302)
        self.assertTrue(rotate.url.startswith("/profile/"))

        account = DavAccount.objects.get(user=user)
        self.assertNotEqual(account.password_hash, original_hash)

        onboarding = self.client.session.get("dav_onboarding")
        self.assertTrue(onboarding and onboarding.get("password"))
        self.assertNotIn(onboarding["password"], self.users_file.read_text(encoding="utf-8"))


class NavSettingsTests(TestCase):
    def setUp(self):
        self.user = get_user_model().objects.create_user(username="nav_user", password="test12345")

    def test_nav_settings_requires_login(self):
        response = self.client.get("/profile/nav/")
        self.assertEqual(response.status_code, 302)
        self.assertIn("/accounts/login/", response.url)

    def test_save_nav_settings_and_render_in_header(self):
        self.client.login(username="nav_user", password="test12345")
        response = self.client.post(
            "/profile/nav/",
            {
                "app_visible_todo": "on",
                "app_order_todo": "1",
                "app_visible_agenda": "on",
                "app_order_agenda": "2",
                "app_order_planner": "3",
                "custom_label_1": "Wiki Team",
                "custom_url_1": "https://example.com/wiki",
                "widgets_json": '[{"title":"KPI","type":"text","config":{"source":"local"}}]',
            },
        )
        self.assertEqual(response.status_code, 302)

        nav_cfg = UserNavConfig.objects.get(user=self.user)
        self.assertTrue(nav_cfg.config.get("_configured"))
        self.assertIn("todo", nav_cfg.config.get("app_order", []))
        self.assertIn("planner", nav_cfg.config.get("hidden_apps", []))
        self.assertEqual(nav_cfg.config.get("custom_links", [])[0]["label"], "Wiki Team")

        page = self.client.get("/todo/")
        self.assertEqual(page.status_code, 200)
        self.assertContains(page, "Wiki Team")
        self.assertContains(page, '<option value="/todo/" selected>', html=False)
        self.assertNotContains(page, '<option value="/planner/"', html=False)


class DashboardWidgetsTests(TestCase):
    def setUp(self):
        self.user = get_user_model().objects.create_user(username="dash_user", password="test12345")

    def test_dashboard_widgets_endpoint_requires_login(self):
        response = self.client.post(
            "/dashboard/widgets",
            data=json.dumps({"order": [], "hidden": []}),
            content_type="application/json",
        )
        self.assertEqual(response.status_code, 302)
        self.assertIn("/accounts/login/", response.url)

    def test_dashboard_widgets_endpoint_saves_normalized_payload(self):
        self.client.login(username="dash_user", password="test12345")
        response = self.client.post(
            "/dashboard/widgets",
            data=json.dumps(
                {
                    "order": ["todo", "planner", "invalid_widget"],
                    "hidden": ["planner", "invalid_widget"],
                }
            ),
            content_type="application/json",
        )
        self.assertEqual(response.status_code, 200)
        nav_cfg = UserNavConfig.objects.get(user=self.user)
        dashboard_cfg = nav_cfg.config.get("dashboard_widgets", {})
        self.assertEqual(dashboard_cfg.get("order", [])[0], "todo")
        self.assertEqual(dashboard_cfg.get("order", [])[1], "planner")
        self.assertIn("planner", dashboard_cfg.get("hidden", []))
        self.assertNotIn("invalid_widget", dashboard_cfg.get("order", []))
        self.assertNotIn("invalid_widget", dashboard_cfg.get("hidden", []))
        self.assertGreaterEqual(len(dashboard_cfg.get("order", [])), len(DEFAULT_DASHBOARD_WIDGET_IDS))

    def test_dashboard_context_uses_saved_widget_layout(self):
        self.client.login(username="dash_user", password="test12345")
        UserNavConfig.objects.create(
            user=self.user,
            config={
                "dashboard_widgets": {
                    "order": ["vault", "todo"],
                    "hidden": ["todo"],
                }
            },
        )
        response = self.client.get("/")
        self.assertEqual(response.status_code, 200)
        widgets = response.context["dashboard_widgets"]
        self.assertEqual(widgets[0]["id"], "vault")
        todo_widget = next(row for row in widgets if row["id"] == "todo")
        self.assertTrue(todo_widget["hidden"])


class DashboardPreferencesTests(TestCase):
    def setUp(self):
        self.user = get_user_model().objects.create_user(username="dash_pref_user", password="test12345")

    def test_dashboard_preferences_endpoint_requires_login(self):
        response = self.client.post(
            "/dashboard/preferences",
            data=json.dumps({"density": "compact", "accent": "green", "sections": ["snapshot"]}),
            content_type="application/json",
        )
        self.assertEqual(response.status_code, 302)
        self.assertIn("/accounts/login/", response.url)

    def test_dashboard_preferences_endpoint_saves_normalized_payload(self):
        self.client.login(username="dash_pref_user", password="test12345")
        response = self.client.post(
            "/dashboard/preferences",
            data=json.dumps(
                {
                    "density": "compact",
                    "accent": "rose",
                    "sections": ["snapshot", "calendar", "invalid"],
                }
            ),
            content_type="application/json",
        )
        self.assertEqual(response.status_code, 200)
        nav_cfg = UserNavConfig.objects.get(user=self.user)
        prefs = nav_cfg.config.get("dashboard_preferences", {})
        self.assertEqual(prefs.get("density"), "compact")
        self.assertEqual(prefs.get("accent"), "rose")
        self.assertEqual(prefs.get("sections"), ["snapshot", "calendar"])

    def test_dashboard_snapshot_requires_login(self):
        response = self.client.get("/dashboard/snapshot")
        self.assertEqual(response.status_code, 302)
        self.assertIn("/accounts/login/", response.url)

    def test_dashboard_context_exposes_preferences(self):
        self.client.login(username="dash_pref_user", password="test12345")
        UserNavConfig.objects.create(
            user=self.user,
            config={
                "dashboard_preferences": {
                    "density": "compact",
                    "accent": "amber",
                    "sections": ["snapshot", "widgets"],
                }
            },
        )
        response = self.client.get("/")
        self.assertEqual(response.status_code, 200)
        prefs = response.context["dashboard_preferences"]
        self.assertEqual(prefs["density"], "compact")
        self.assertEqual(prefs["accent"], "amber")
        self.assertEqual(prefs["sections"], ["snapshot", "widgets"])


class MobileApiAuthTests(TestCase):
    def setUp(self):
        self.user = get_user_model().objects.create_user(
            username="mobile_user",
            email="mobile@example.com",
            password="test12345",
        )

    def _login(self):
        response = self.client.post(
            "/api/mobile/auth/login",
            data=json.dumps({"identity": "mobile@example.com", "password": "test12345"}),
            content_type="application/json",
        )
        self.assertEqual(response.status_code, 200)
        return response.json()

    def test_login_issues_tokens(self):
        payload = self._login()
        self.assertTrue(payload["ok"])
        self.assertIn("access_token", payload)
        self.assertIn("refresh_token", payload)
        self.assertEqual(payload["user"]["id"], self.user.id)
        self.assertEqual(MobileApiSession.objects.filter(user=self.user, revoked_at__isnull=True).count(), 1)

    def test_login_rejects_invalid_credentials(self):
        response = self.client.post(
            "/api/mobile/auth/login",
            data=json.dumps({"identity": "mobile@example.com", "password": "wrong"}),
            content_type="application/json",
        )
        self.assertEqual(response.status_code, 401)
        self.assertEqual(response.json()["error"], "invalid_credentials")

    def test_dashboard_requires_bearer_token(self):
        response = self.client.get("/api/mobile/dashboard")
        self.assertEqual(response.status_code, 401)
        self.assertEqual(response.json()["error"], "missing_bearer_token")

    def test_dashboard_returns_user_snapshot(self):
        Task.objects.create(
            owner=self.user,
            title="Task mobile",
            status=Task.Status.OPEN,
            due_date=timezone.localdate() - timedelta(days=1),
        )
        PlannerItem.objects.create(
            owner=self.user,
            title="Planner mobile",
            status=PlannerItem.Status.PLANNED,
        )

        payload = self._login()
        access = payload["access_token"]
        response = self.client.get(
            "/api/mobile/dashboard",
            HTTP_AUTHORIZATION=f"Bearer {access}",
        )
        self.assertEqual(response.status_code, 200)
        body = response.json()
        self.assertEqual(body["metrics"]["open_tasks"], 1)
        self.assertEqual(body["metrics"]["planner_queue"], 1)
        self.assertEqual(body["metrics"]["alerts_open"], 1)

    def test_refresh_rotates_tokens(self):
        payload = self._login()
        old_refresh = payload["refresh_token"]

        refresh_response = self.client.post(
            "/api/mobile/auth/refresh",
            data=json.dumps({"refresh_token": old_refresh}),
            content_type="application/json",
        )
        self.assertEqual(refresh_response.status_code, 200)
        refreshed = refresh_response.json()
        self.assertNotEqual(refreshed["refresh_token"], old_refresh)

        second_refresh = self.client.post(
            "/api/mobile/auth/refresh",
            data=json.dumps({"refresh_token": old_refresh}),
            content_type="application/json",
        )
        self.assertEqual(second_refresh.status_code, 401)

    def test_logout_revokes_session(self):
        payload = self._login()
        access = payload["access_token"]

        logout = self.client.post(
            "/api/mobile/auth/logout",
            data=json.dumps({}),
            content_type="application/json",
            HTTP_AUTHORIZATION=f"Bearer {access}",
        )
        self.assertEqual(logout.status_code, 200)

        denied = self.client.get("/api/mobile/dashboard", HTTP_AUTHORIZATION=f"Bearer {access}")
        self.assertEqual(denied.status_code, 401)

    def test_mobile_options_preflight_returns_cors_headers(self):
        response = self.client.options(
            "/api/mobile/auth/login",
            HTTP_ORIGIN="http://localhost",
            HTTP_ACCESS_CONTROL_REQUEST_METHOD="POST",
        )
        self.assertEqual(response.status_code, 204)
        self.assertEqual(response["Access-Control-Allow-Origin"], "http://localhost")

    def test_api_options_preflight_returns_cors_headers(self):
        response = self.client.options(
            "/api/routines",
            HTTP_ORIGIN="http://localhost",
            HTTP_ACCESS_CONTROL_REQUEST_METHOD="GET",
        )
        self.assertEqual(response.status_code, 204)
        self.assertEqual(response["Access-Control-Allow-Origin"], "http://localhost")

    def test_mobile_routines_returns_week_items(self):
        routine = Routine.objects.create(owner=self.user, name="Routine Mobile", is_active=True)
        item = RoutineItem.objects.create(
            owner=self.user,
            routine=routine,
            title="Stretching",
            weekday=timezone.localdate().weekday(),
            is_active=True,
        )
        week_start = timezone.localdate() - timedelta(days=timezone.localdate().weekday())
        RoutineCheck.objects.create(
            owner=self.user,
            item=item,
            week_start=week_start,
            status=RoutineCheck.Status.DONE,
        )

        payload = self._login()
        access = payload["access_token"]
        response = self.client.get(
            f"/api/mobile/routines?week={week_start.isoformat()}",
            HTTP_AUTHORIZATION=f"Bearer {access}",
        )
        self.assertEqual(response.status_code, 200)
        body = response.json()
        self.assertTrue(body["ok"])
        self.assertEqual(body["week_start"], week_start.isoformat())
        self.assertEqual(len(body["items"]), 1)
        self.assertEqual(body["items"][0]["title"], "Stretching")
        self.assertEqual(body["items"][0]["status"], RoutineCheck.Status.DONE)
        self.assertEqual(body["stats"]["planned"], 0)
        self.assertEqual(body["stats"]["done"], 1)
        self.assertEqual(body["stats"]["skipped"], 0)

    def test_mobile_routines_counts_unchecked_items_as_planned(self):
        routine = Routine.objects.create(owner=self.user, name="Routine Planned", is_active=True)
        RoutineItem.objects.create(
            owner=self.user,
            routine=routine,
            title="Morning walk",
            weekday=timezone.localdate().weekday(),
            is_active=True,
        )
        week_start = timezone.localdate() - timedelta(days=timezone.localdate().weekday())
        payload = self._login()
        access = payload["access_token"]

        response = self.client.get(
            f"/api/mobile/routines?week={week_start.isoformat()}",
            HTTP_AUTHORIZATION=f"Bearer {access}",
        )
        self.assertEqual(response.status_code, 200)
        body = response.json()
        self.assertEqual(body["stats"]["planned"], 1)
        self.assertEqual(body["stats"]["done"], 0)
        self.assertEqual(body["stats"]["skipped"], 0)

    def test_mobile_routines_check_updates_status(self):
        routine = Routine.objects.create(owner=self.user, name="Routine Check", is_active=True)
        item = RoutineItem.objects.create(
            owner=self.user,
            routine=routine,
            title="Hydration",
            weekday=0,
            is_active=True,
        )
        week_start = timezone.localdate() - timedelta(days=timezone.localdate().weekday())
        payload = self._login()
        access = payload["access_token"]

        response = self.client.post(
            "/api/mobile/routines/check",
            data=json.dumps(
                {
                    "item_id": item.id,
                    "status": RoutineCheck.Status.SKIPPED,
                    "week": week_start.isoformat(),
                }
            ),
            content_type="application/json",
            HTTP_AUTHORIZATION=f"Bearer {access}",
        )
        self.assertEqual(response.status_code, 200)
        body = response.json()
        self.assertTrue(body["ok"])
        self.assertEqual(body["status"], RoutineCheck.Status.SKIPPED)
        self.assertEqual(body["stats"]["planned"], 0)
        self.assertEqual(body["stats"]["done"], 0)
        self.assertEqual(body["stats"]["skipped"], 1)

        check = RoutineCheck.objects.get(owner=self.user, item=item, week_start=week_start)
        self.assertEqual(check.status, RoutineCheck.Status.SKIPPED)

    def test_mobile_routines_item_crud(self):
        routine = Routine.objects.create(owner=self.user, name="Routine CRUD", is_active=True)
        category = RoutineCategory.objects.create(owner=self.user, name="Salute", is_active=True)
        payload = self._login()
        access = payload["access_token"]

        create_response = self.client.post(
            "/api/mobile/routines/items/create",
            data=json.dumps(
                {
                    "routine_id": routine.id,
                    "title": "Mobilita",
                    "weekday": 2,
                    "time_start": "08:30",
                    "time_end": "09:00",
                    "category_id": category.id,
                    "note": "Foam roller",
                }
            ),
            content_type="application/json",
            HTTP_AUTHORIZATION=f"Bearer {access}",
        )
        self.assertEqual(create_response.status_code, 200)
        created_id = create_response.json()["item_id"]
        item = RoutineItem.objects.get(id=created_id, owner=self.user)
        self.assertEqual(item.title, "Mobilita")
        self.assertEqual(item.category_id, category.id)

        update_response = self.client.post(
            "/api/mobile/routines/items/update",
            data=json.dumps(
                {
                    "item_id": item.id,
                    "routine_id": routine.id,
                    "title": "Mobilita mattina",
                    "weekday": 3,
                    "time_start": "08:45",
                    "time_end": "",
                    "category_id": "",
                    "note": "Versione breve",
                }
            ),
            content_type="application/json",
            HTTP_AUTHORIZATION=f"Bearer {access}",
        )
        self.assertEqual(update_response.status_code, 200)
        item.refresh_from_db()
        self.assertEqual(item.title, "Mobilita mattina")
        self.assertEqual(item.weekday, 3)
        self.assertIsNone(item.time_end)
        self.assertIsNone(item.category_id)

        delete_response = self.client.post(
            "/api/mobile/routines/items/delete",
            data=json.dumps({"item_id": item.id}),
            content_type="application/json",
            HTTP_AUTHORIZATION=f"Bearer {access}",
        )
        self.assertEqual(delete_response.status_code, 200)
        self.assertFalse(RoutineItem.objects.filter(id=item.id).exists())

    def test_unified_routines_api_accepts_session_auth(self):
        self.client.login(username="mobile_user", password="test12345")
        routine = Routine.objects.create(owner=self.user, name="Routine Session", is_active=True)
        week_start = timezone.localdate() - timedelta(days=timezone.localdate().weekday())

        create_response = self.client.post(
            "/api/routines/items/create",
            data=json.dumps(
                {
                    "routine_id": routine.id,
                    "title": "Session task",
                    "weekday": 1,
                }
            ),
            content_type="application/json",
        )
        self.assertEqual(create_response.status_code, 200)
        item_id = create_response.json()["item_id"]

        list_response = self.client.get(f"/api/routines?week={week_start.isoformat()}")
        self.assertEqual(list_response.status_code, 200)
        body = list_response.json()
        self.assertTrue(any(row["id"] == item_id for row in body["items"]))

    def test_unified_routines_api_accepts_bearer_auth(self):
        routine = Routine.objects.create(owner=self.user, name="Routine Bearer", is_active=True)
        payload = self._login()
        access = payload["access_token"]

        create_response = self.client.post(
            "/api/routines/items/create",
            data=json.dumps(
                {
                    "routine_id": routine.id,
                    "title": "Bearer task",
                    "weekday": 2,
                }
            ),
            content_type="application/json",
            HTTP_AUTHORIZATION=f"Bearer {access}",
        )
        self.assertEqual(create_response.status_code, 200)

        list_response = self.client.get(
            "/api/routines",
            HTTP_AUTHORIZATION=f"Bearer {access}",
        )
        self.assertEqual(list_response.status_code, 200)
        self.assertTrue(list_response.json()["ok"])

    def test_unified_projects_api_accepts_bearer_auth(self):
        from projects.models import Project, SubProject

        project = Project.objects.create(owner=self.user, name="Project API", is_archived=False)
        SubProject.objects.create(
            owner=self.user,
            project=project,
            title="Milestone 1",
            status=SubProject.Status.DONE,
            is_archived=False,
        )

        payload = self._login()
        access = payload["access_token"]
        response = self.client.get("/api/projects", HTTP_AUTHORIZATION=f"Bearer {access}")
        self.assertEqual(response.status_code, 200)
        body = response.json()
        self.assertTrue(body["ok"])
        self.assertEqual(body["stats"]["total"], 1)
        self.assertEqual(body["stats"]["active"], 1)
        self.assertEqual(body["items"][0]["name"], "Project API")
        self.assertEqual(body["items"][0]["subprojects_total"], 1)

    def test_unified_projects_api_accepts_session_auth(self):
        from projects.models import Project

        Project.objects.create(owner=self.user, name="Project Session", is_archived=False)
        self.client.login(username="mobile_user", password="test12345")
        response = self.client.get("/api/projects")
        self.assertEqual(response.status_code, 200)
        body = response.json()
        self.assertTrue(body["ok"])
        self.assertEqual(body["stats"]["total"], 1)

    def test_unified_agenda_api_accepts_bearer_auth(self):
        from agenda.models import AgendaItem

        AgendaItem.objects.create(
            owner=self.user,
            title="Call cliente",
            item_type=AgendaItem.ItemType.REMINDER,
            due_date=timezone.localdate(),
            status=AgendaItem.Status.PLANNED,
        )
        payload = self._login()
        access = payload["access_token"]

        response = self.client.get(
            "/api/agenda",
            HTTP_AUTHORIZATION=f"Bearer {access}",
        )
        self.assertEqual(response.status_code, 200)
        body = response.json()
        self.assertTrue(body["ok"])
        self.assertEqual(body["stats"]["total"], 1)
        self.assertEqual(body["stats"]["reminders"], 1)
        self.assertEqual(body["items"][0]["title"], "Call cliente")

    def test_unified_agenda_api_accepts_session_auth(self):
        from agenda.models import AgendaItem

        AgendaItem.objects.create(
            owner=self.user,
            title="Workout",
            item_type=AgendaItem.ItemType.ACTIVITY,
            due_date=timezone.localdate(),
            status=AgendaItem.Status.DONE,
        )
        self.client.login(username="mobile_user", password="test12345")
        response = self.client.get("/api/agenda")
        self.assertEqual(response.status_code, 200)
        body = response.json()
        self.assertTrue(body["ok"])
        self.assertEqual(body["stats"]["total"], 1)
        self.assertEqual(body["stats"]["activities"], 1)
