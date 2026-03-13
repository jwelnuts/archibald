from unittest.mock import patch

from django.contrib.auth import get_user_model
from django.test import TestCase

from archibald.prompting import (
    build_archibald_system_for_user,
    build_cognitive_context_for_prompt,
    build_relational_context_for_prompt,
)

from .models import ArchibaldPersonaConfig, LabEntry


class AiLabViewsTests(TestCase):
    def setUp(self):
        self.user = get_user_model().objects.create_user(username="alab", password="test1234")

    def test_dashboard_requires_login(self):
        response = self.client.get("/ai-lab/")
        self.assertEqual(response.status_code, 302)

    def test_personal_lab_requires_login(self):
        response = self.client.get("/ai-lab/personal-lab/")
        self.assertEqual(response.status_code, 302)

    def test_add_entry(self):
        self.client.login(username="alab", password="test1234")
        response = self.client.post(
            "/ai-lab/api/add",
            {
                "title": "Studiare embeddings",
                "area": LabEntry.Area.EMBEDDINGS,
                "status": LabEntry.Status.LEARNING,
                "prompt": "cos'e un embedding?",
                "result": "bozza",
                "notes": "partire dalle basi",
                "next_step": "provare similitudine coseno",
                "resource_url": "https://example.com",
            },
        )
        self.assertEqual(response.status_code, 302)
        self.assertEqual(LabEntry.objects.filter(owner=self.user).count(), 1)

    def test_save_archibald_persona(self):
        self.client.login(username="alab", password="test1234")
        response = self.client.post(
            "/ai-lab/personal-lab/",
            {
                "action": "save_persona",
                "preset": ArchibaldPersonaConfig.Preset.OPERATIVE,
                "verbosity": ArchibaldPersonaConfig.Verbosity.SHORT,
                "challenge_level": ArchibaldPersonaConfig.ChallengeLevel.HIGH,
                "action_mode": ArchibaldPersonaConfig.ActionMode.WHEN_USEFUL,
                "avoid_pandering": "on",
                "include_reasoning": "on",
                "psych_validate_emotions": "on",
                "psych_assertive_boundaries": "on",
                "psych_socratic_questions": "on",
                "psych_cognitive_reframe": "on",
                "psych_bias_check": "on",
                "psych_self_efficacy": "on",
                "psych_micro_actions": "on",
                "psych_accountability_nudge": "on",
                "psych_decision_simplify": "on",
                "psych_non_judgmental_tone": "on",
                "bias_catastrophizing": "on",
                "bias_all_or_nothing": "on",
                "bias_overgeneralization": "on",
                "bias_mind_reading": "on",
                "bias_negative_filtering": "on",
                "custom_instructions": "Vai dritto al punto.",
            },
        )
        self.assertEqual(response.status_code, 302)
        cfg = ArchibaldPersonaConfig.objects.get(owner=self.user)
        self.assertEqual(cfg.preset, ArchibaldPersonaConfig.Preset.OPERATIVE)
        self.assertEqual(cfg.verbosity, ArchibaldPersonaConfig.Verbosity.SHORT)
        self.assertEqual(cfg.challenge_level, ArchibaldPersonaConfig.ChallengeLevel.HIGH)
        self.assertTrue(cfg.avoid_pandering)
        self.assertTrue(cfg.psych_socratic_questions)
        self.assertTrue(cfg.bias_catastrophizing)
        self.assertFalse(cfg.bias_confirmation_bias)

    @patch("ai_lab.views.request_openai_response", return_value="Risposta sandbox")
    def test_sandbox_prompt_returns_preview(self, mocked_openai):
        self.client.login(username="alab", password="test1234")
        response = self.client.post(
            "/ai-lab/personal-lab/",
            {
                "action": "test_persona",
                "prompt": "Fammi una risposta piu diretta.",
            },
        )
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Risposta sandbox")
        mocked_openai.assert_called_once()

    @patch("ai_lab.views.request_openai_response", return_value="Risposta sandbox")
    def test_sandbox_uses_unsaved_custom_instructions_override(self, mocked_openai):
        self.client.login(username="alab", password="test1234")
        response = self.client.post(
            "/ai-lab/personal-lab/",
            {
                "action": "test_persona",
                "prompt": "Scrivi un saluto.",
                "custom_instructions_preview": "Rispondi sempre in polacco.",
            },
        )
        self.assertEqual(response.status_code, 200)
        mocked_openai.assert_called_once()
        _, instructions = mocked_openai.call_args[0]
        self.assertIn("Rispondi sempre in polacco.", instructions)
        self.assertIn("Regola prioritaria", instructions)

    @patch("ai_lab.views.request_openai_response_with_debug", return_value=("Risposta sandbox", {"status": "ok"}))
    def test_sandbox_debug_panel_visible_when_enabled(self, mocked_openai_debug):
        self.client.login(username="alab", password="test1234")
        response = self.client.post(
            "/ai-lab/personal-lab/",
            {
                "action": "test_persona",
                "prompt": "Debugga questa risposta.",
                "debug_enabled": "on",
            },
        )
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Debug pipeline sandbox")
        self.assertContains(response, "&quot;status&quot;: &quot;ok&quot;")
        mocked_openai_debug.assert_called_once()

    def test_build_system_supports_custom_override_without_saved_config(self):
        system = build_archibald_system_for_user(
            self.user,
            custom_instructions_override="Rispondi in polacco.",
        )
        self.assertIn("Rispondi in polacco.", system)
        self.assertIn("Regola prioritaria", system)

    def test_build_system_elite_preset_contains_mission_style(self):
        ArchibaldPersonaConfig.objects.update_or_create(
            owner=self.user,
            defaults={
                "preset": ArchibaldPersonaConfig.Preset.ELITE,
            },
        )
        system = build_archibald_system_for_user(self.user)
        self.assertIn("Alfred elite", system)
        self.assertIn("missione", system)

    def test_build_cognitive_context_reflects_enabled_biases(self):
        ArchibaldPersonaConfig.objects.update_or_create(
            owner=self.user,
            defaults={
                "psych_bias_check": True,
                "bias_catastrophizing": True,
                "bias_all_or_nothing": False,
                "bias_overgeneralization": False,
                "bias_mind_reading": False,
                "bias_negative_filtering": False,
                "bias_confirmation_bias": False,
            },
        )
        context = build_cognitive_context_for_prompt(self.user, "E un disastro, e finita.")
        self.assertIn("Layer cognitivo operativo", context)
        self.assertIn("catastrofismo", context)
        self.assertNotIn("bias di conferma", context)
        self.assertIn("Intensita intervento", context)

    def test_build_cognitive_context_disabled_when_bias_check_off(self):
        ArchibaldPersonaConfig.objects.update_or_create(
            owner=self.user,
            defaults={
                "psych_bias_check": False,
            },
        )
        context = build_cognitive_context_for_prompt(self.user, "e un disastro")
        self.assertEqual(context, "")

    def test_personal_lab_shows_cognitive_preview_in_sandbox(self):
        self.client.login(username="alab", password="test1234")
        response = self.client.post(
            "/ai-lab/personal-lab/",
            {
                "action": "test_persona",
                "prompt": "E un disastro, non ne usciro.",
                "debug_enabled": "on",
            },
        )
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Layer cognitivo operativo")

    def test_build_relational_context_detects_distress_signals(self):
        ArchibaldPersonaConfig.objects.update_or_create(
            owner=self.user,
            defaults={
                "psych_validate_emotions": True,
                "psych_non_judgmental_tone": True,
            },
        )
        context = build_relational_context_for_prompt(
            self.user,
            "Se sono infelice e colpa mia, sono demotivato e lavoro 36 ore.",
        )
        self.assertIn("Layer relazionale umano", context)
        self.assertIn("auto-colpevolizzazione", context)
        self.assertIn("sovraccarico lavorativo", context)
        self.assertIn("demotivazione/infelicita", context)

    def test_build_relational_context_empty_without_signals(self):
        ArchibaldPersonaConfig.objects.update_or_create(
            owner=self.user,
            defaults={},
        )
        context = build_relational_context_for_prompt(self.user, "Aggiorna il planner di domani.")
        self.assertEqual(context, "")
