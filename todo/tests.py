from django.test import TestCase
from django.contrib.auth import get_user_model

from planner.models import PlannerItem
from projects.models import Project

from .models import Task


class TodoProjectBindingTests(TestCase):
    def setUp(self):
        self.user = get_user_model().objects.create_user(username="todo_user", password="test1234")

    def test_add_task_with_existing_project(self):
        project = Project.objects.create(owner=self.user, name="Progetto Alpha")
        self.client.login(username="todo_user", password="test1234")
        response = self.client.post(
            "/todo/api/add",
            {
                "title": "Task con progetto",
                "due_date": "",
                "status": Task.Status.OPEN,
                "priority": Task.Priority.MEDIUM,
                "project_choice": str(project.id),
                "project_name": "",
                "note": "note",
            },
        )
        self.assertEqual(response.status_code, 302)
        task = Task.objects.get(owner=self.user, title="Task con progetto")
        self.assertEqual(task.project_id, project.id)

    def test_add_task_creates_new_project_if_requested(self):
        self.client.login(username="todo_user", password="test1234")
        response = self.client.post(
            "/todo/api/add",
            {
                "title": "Task nuovo progetto",
                "due_date": "",
                "status": Task.Status.OPEN,
                "priority": Task.Priority.HIGH,
                "project_choice": "__new__",
                "project_name": "Progetto Beta",
                "note": "",
            },
        )
        self.assertEqual(response.status_code, 302)
        project = Project.objects.get(owner=self.user, name="Progetto Beta")
        task = Task.objects.get(owner=self.user, title="Task nuovo progetto")
        self.assertEqual(task.project_id, project.id)

    def test_dashboard_includes_planner_snapshot(self):
        PlannerItem.objects.create(
            owner=self.user,
            title="Promemoria bolletta",
            status=PlannerItem.Status.PLANNED,
        )
        self.client.login(username="todo_user", password="test1234")
        response = self.client.get("/todo/")
        self.assertEqual(response.status_code, 200)
        self.assertIn("planner_upcoming", response.context)
        self.assertIn("planner_counts", response.context)
