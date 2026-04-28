from django.contrib.auth import get_user_model
from django.test import TestCase


class ArchibaldHelloPageTests(TestCase):
    def setUp(self):
        self.user = get_user_model().objects.create_user(
            username="archibald_user",
            password="pwd12345",
        )

    def test_hello_page_renders_for_authenticated_user(self):
        self.client.force_login(self.user)
        response = self.client.get("/archibald/")
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Ciao, come stai?")
