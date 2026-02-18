from django.contrib.auth import get_user_model
from django.test import TestCase

from .models import LabEntry


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
