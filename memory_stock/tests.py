from django.contrib.auth import get_user_model
from django.test import TestCase

from .models import MemoryStockItem
from .services import clean_subject_for_title, extract_first_url, save_memory_from_inbound_email


class MemoryStockServiceTests(TestCase):
    def setUp(self):
        self.user = get_user_model().objects.create_user(
            username="memory_user",
            password="pwd12345",
            email="memory@example.com",
        )

    def test_clean_subject_for_title(self):
        title = clean_subject_for_title("[MEMORY] #memory ACTION:memory_stock.save Come creare abitudini")
        self.assertEqual(title, "Come creare abitudini")

    def test_clean_subject_for_title_with_todo_and_transaction_tokens(self):
        title = clean_subject_for_title("[TODO] #transaction [REMINDER] ACTION:todo Sistemare piano settimanale")
        self.assertEqual(title, "Sistemare piano settimanale")

    def test_extract_first_url(self):
        body = "Guarda questo articolo: https://example.com/articles/abitudini?x=1 interessante"
        self.assertEqual(extract_first_url(body), "https://example.com/articles/abitudini?x=1")

    def test_save_memory_deduplicates_by_message_id(self):
        first = save_memory_from_inbound_email(
            owner=self.user,
            sender="sender@example.com",
            subject="[MEMORY] A",
            body_text="https://example.com/a",
            message_id="<id-1@example.com>",
            action_key="memory_stock.save",
        )
        second = save_memory_from_inbound_email(
            owner=self.user,
            sender="sender@example.com",
            subject="[MEMORY] A duplicate",
            body_text="https://example.com/a2",
            message_id="<id-1@example.com>",
            action_key="memory_stock.save",
        )
        self.assertTrue(first.created)
        self.assertFalse(second.created)
        self.assertEqual(MemoryStockItem.objects.filter(owner=self.user).count(), 1)


class MemoryStockViewTests(TestCase):
    def setUp(self):
        self.user = get_user_model().objects.create_user(username="memory_view", password="pwd12345")
        self.client.login(username="memory_view", password="pwd12345")

    def test_dashboard_renders(self):
        MemoryStockItem.objects.create(owner=self.user, title="Nota rapida")
        response = self.client.get("/memory-stock/")
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Memory Stock")
        self.assertContains(response, "Nota rapida")
