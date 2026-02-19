from django.contrib.auth import get_user_model
from django.test import TestCase

from todo.models import Task

from .models import PlannerItem


class PlannerDashboardTests(TestCase):
    def setUp(self):
        self.user = get_user_model().objects.create_user(username="planner_user", password="test1234")

    def test_dashboard_includes_todo_snapshot(self):
        PlannerItem.objects.create(
            owner=self.user,
            title="Spesa futura",
            status=PlannerItem.Status.PLANNED,
        )
        Task.objects.create(
            owner=self.user,
            title="Compra latte",
            status=Task.Status.OPEN,
        )
        self.client.login(username="planner_user", password="test1234")
        response = self.client.get("/planner/")
        self.assertEqual(response.status_code, 200)
        self.assertIn("todo_open", response.context)
        self.assertIn("todo_counts", response.context)
