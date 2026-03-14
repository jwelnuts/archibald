import json

from django.contrib.auth import get_user_model
from django.test import TestCase

from ai_lab.models import ArchibaldInstructionState, ArchibaldPersonaConfig
from .models import UserNavConfig
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
