from django.contrib.auth import get_user_model
from django.test import TestCase

from ai_lab.models import ArchibaldInstructionState, ArchibaldPersonaConfig


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
