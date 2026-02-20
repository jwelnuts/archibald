from unittest.mock import patch

from django.contrib.auth import get_user_model
from django.test import TestCase

from .models import ArchibaldPersonaConfig, LabEntry


class AiLabViewsTests(TestCase):
    def setUp(self):
        self.user = get_user_model().objects.create_user(username="alab", password="test1234")

    def test_dashboard_requires_login(self):
        response = self.client.get("/ai-lab/")
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
            "/ai-lab/",
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

    @patch("ai_lab.views.request_openai_response", return_value="Risposta sandbox")
    def test_sandbox_prompt_returns_preview(self, mocked_openai):
        self.client.login(username="alab", password="test1234")
        response = self.client.post(
            "/ai-lab/",
            {
                "action": "test_persona",
                "prompt": "Fammi una risposta piu diretta.",
            },
        )
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Risposta sandbox")
        mocked_openai.assert_called_once()
