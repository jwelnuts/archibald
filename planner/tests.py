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

    def test_transfer_planner_item_to_todo(self):
        planner_item = PlannerItem.objects.create(
            owner=self.user,
            title="Pagamento assicurazione",
            status=PlannerItem.Status.PLANNED,
            note="Da ricordare",
            amount="89.90",
        )
        self.client.login(username="planner_user", password="test1234")
        response = self.client.post("/planner/to-todo", {"id": planner_item.id})
        self.assertEqual(response.status_code, 302)
        self.assertEqual(response.url, "/todo/")
        self.assertFalse(PlannerItem.objects.filter(id=planner_item.id).exists())
        task = Task.objects.get(owner=self.user, title="Pagamento assicurazione")
        self.assertEqual(task.status, Task.Status.OPEN)
        self.assertIn("Da ricordare", task.note)
        self.assertIn("[Da Planner] Importo", task.note)
