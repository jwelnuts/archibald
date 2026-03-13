from unittest.mock import patch

from django.contrib.auth import get_user_model
from django.test import TestCase

from ai_lab.models import ArchibaldPersonaConfig

from .models import ArchibaldMessage, ArchibaldThread


class ArchibaldModesTests(TestCase):
    def setUp(self):
        self.user = get_user_model().objects.create_user(username="archi_user", password="pwd12345")
        self.client.login(username="archi_user", password="pwd12345")

    @patch(
        "archibald.views._openai_response_with_state",
        return_value=("Risposta assistente", {}, {}),
    )
    def test_dashboard_diary_post_saves_in_diary_thread(self, _mock_openai):
        response = self.client.post(
            "/archibald/",
            {
                "prompt": "Come organizzo la giornata?",
                "mode": "diary",
                "day": "2026-03-05",
            },
        )
        self.assertEqual(response.status_code, 302)
        self.assertIn("/archibald/?mode=diary", response.url)

        thread = ArchibaldThread.objects.get(owner=self.user, kind=ArchibaldThread.Kind.DIARY)
        self.assertTrue(thread.is_active)
        self.assertEqual(ArchibaldMessage.objects.filter(owner=self.user, thread=thread).count(), 2)

    @patch(
        "archibald.views._openai_response_with_state",
        return_value=("Risposta temporanea", {}, {}),
    )
    def test_dashboard_temp_post_creates_temporary_thread(self, _mock_openai):
        response = self.client.post(
            "/archibald/",
            {
                "prompt": "Nuovo tema temporaneo",
                "mode": "temp",
                "thread_id": "",
            },
        )
        self.assertEqual(response.status_code, 302)
        self.assertIn("/archibald/?mode=temp&thread=", response.url)

        thread = ArchibaldThread.objects.get(owner=self.user, kind=ArchibaldThread.Kind.TEMPORARY)
        self.assertFalse(thread.is_active)
        self.assertEqual(ArchibaldMessage.objects.filter(owner=self.user, thread=thread).count(), 2)

    def test_messages_api_filters_temporary_thread(self):
        temp_a = ArchibaldThread.objects.create(
            owner=self.user,
            title="Temp A",
            kind=ArchibaldThread.Kind.TEMPORARY,
            is_active=False,
        )
        temp_b = ArchibaldThread.objects.create(
            owner=self.user,
            title="Temp B",
            kind=ArchibaldThread.Kind.TEMPORARY,
            is_active=False,
        )
        ArchibaldMessage.objects.create(
            owner=self.user,
            thread=temp_a,
            role=ArchibaldMessage.Role.USER,
            content="A1",
        )
        ArchibaldMessage.objects.create(
            owner=self.user,
            thread=temp_b,
            role=ArchibaldMessage.Role.USER,
            content="B1",
        )

        response = self.client.get(f"/archibald/messages?mode=temp&thread={temp_a.id}")
        self.assertEqual(response.status_code, 200)
        payload = response.json()
        self.assertEqual(len(payload["messages"]), 1)
        self.assertEqual(payload["messages"][0]["content"], "A1")

    def test_dashboard_renders_diary_mode(self):
        response = self.client.get("/archibald/?mode=diary")
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Diario giornaliero")

    def test_dashboard_renders_temp_mode(self):
        response = self.client.get("/archibald/?mode=temp")
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Chat temporanee")

    def test_create_and_remove_temporary_thread(self):
        create_response = self.client.post("/archibald/temp/new")
        self.assertEqual(create_response.status_code, 302)
        self.assertIn("/archibald/?mode=temp&thread=", create_response.url)

        thread = ArchibaldThread.objects.filter(owner=self.user, kind=ArchibaldThread.Kind.TEMPORARY).first()
        self.assertIsNotNone(thread)

        remove_response = self.client.post("/archibald/temp/remove", {"thread_id": thread.id})
        self.assertEqual(remove_response.status_code, 302)
        self.assertEqual(remove_response.url, "/archibald/?mode=temp")
        self.assertFalse(ArchibaldThread.objects.filter(owner=self.user, id=thread.id).exists())

    @patch(
        "archibald.views._openai_response_with_state",
        return_value=("Risposta quick", {}, {}),
    )
    def test_quick_chat_creates_temporary_thread(self, _mock_openai):
        response = self.client.post(
            "/archibald/quick",
            {
                "prompt": "Bozza rapida",
            },
        )
        self.assertEqual(response.status_code, 200)
        payload = response.json()
        thread = ArchibaldThread.objects.get(owner=self.user, id=payload["thread_id"])
        self.assertEqual(thread.kind, ArchibaldThread.Kind.TEMPORARY)
        self.assertEqual(ArchibaldMessage.objects.filter(owner=self.user, thread=thread).count(), 2)

    @patch(
        "archibald.views._openai_response_with_state",
        return_value=(
            "Risposta con stato",
            {
                "response_id": "resp_123",
                "conversation_id": "conv_123",
                "model": "gpt-5.4",
            },
            {},
        ),
    )
    def test_dashboard_persists_openai_state_on_thread_and_message(self, _mock_openai):
        self.client.post(
            "/archibald/",
            {
                "prompt": "Test stato conversazione",
                "mode": "temp",
                "thread_id": "",
            },
        )

        thread = ArchibaldThread.objects.get(owner=self.user, kind=ArchibaldThread.Kind.TEMPORARY)
        assistant = (
            ArchibaldMessage.objects.filter(owner=self.user, thread=thread, role=ArchibaldMessage.Role.ASSISTANT)
            .order_by("-id")
            .first()
        )
        self.assertIsNotNone(assistant)
        self.assertEqual(thread.openai_conversation_id, "conv_123")
        self.assertEqual(thread.openai_last_response_id, "resp_123")
        self.assertEqual(thread.openai_model, "gpt-5.4")
        self.assertEqual(assistant.openai_response_id, "resp_123")

    @patch(
        "archibald.views._openai_response_with_state",
        return_value=("Risposta relazionale", {}, {}),
    )
    def test_dashboard_injects_relational_context_for_distress_prompt(self, mocked_openai):
        ArchibaldPersonaConfig.objects.update_or_create(
            owner=self.user,
            defaults={
                "psych_validate_emotions": True,
                "psych_non_judgmental_tone": True,
            },
        )
        self.client.post(
            "/archibald/",
            {
                "prompt": "Se sono infelice e colpa mia, lavoro 36 ore e sono demotivato.",
                "mode": "diary",
                "day": "2026-03-05",
            },
        )

        messages = mocked_openai.call_args[0][1]
        self.assertTrue(
            any(
                msg.get("role") == "system" and "Layer relazionale umano" in (msg.get("content") or "")
                for msg in messages
            )
        )
