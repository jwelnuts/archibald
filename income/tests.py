from django.contrib.auth import get_user_model
from django.test import TestCase


class IncomeDashboardFlowTests(TestCase):
    def setUp(self):
        self.user = get_user_model().objects.create_user(username="income_user", password="test1234")
        self.client.login(username="income_user", password="test1234")

    def test_income_dashboard_redirects_to_transactions_with_quick_form(self):
        response = self.client.get("/income/", follow=True)
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Inserimento rapido")
        self.assertTrue(response.request["PATH_INFO"].startswith("/transactions/"))
        self.assertIn("tx_type=IN", response.request.get("QUERY_STRING", ""))
