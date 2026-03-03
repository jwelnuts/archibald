from django.test import TestCase
from django.contrib.auth import get_user_model

from planner.models import PlannerItem
from projects.models import Category, Project

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
                "item_type": Task.ItemType.TASK,
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
                "item_type": Task.ItemType.TASK,
                "due_date": "",
                "status": Task.Status.OPEN,
                "priority": Task.Priority.HIGH,
                "project_choice": "__new__",
                "project_name": "Progetto Beta",
                "note": "",
            },
        )
        self.assertEqual(response.status_code, 302)
        task = Task.objects.get(owner=self.user, title="Task nuovo progetto")
        project = Project.objects.get(owner=self.user, id=task.project_id)
        self.assertTrue(project.name.startswith("Nuovo"))
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

    def test_transfer_task_to_planner(self):
        category = Category.objects.create(owner=self.user, name="Admin")
        task = Task.objects.create(
            owner=self.user,
            title="Contattare cliente",
            item_type=Task.ItemType.REMINDER,
            status=Task.Status.IN_PROGRESS,
            priority=Task.Priority.HIGH,
            category=category,
            note="Call entro domani",
        )
        self.client.login(username="todo_user", password="test1234")
        response = self.client.post("/todo/to-planner", {"id": task.id})
        self.assertEqual(response.status_code, 302)
        self.assertEqual(response.url, "/planner/")
        self.assertFalse(Task.objects.filter(id=task.id).exists())
        planner_item = PlannerItem.objects.get(owner=self.user, title="Contattare cliente")
        self.assertEqual(planner_item.status, PlannerItem.Status.PLANNED)
        self.assertEqual(planner_item.category_id, category.id)
        self.assertIn("Call entro domani", planner_item.note)
        self.assertIn("[Da Todo] Tipo: Reminder", planner_item.note)
        self.assertIn("[Da Todo] Priorita:", planner_item.note)
        self.assertIn("[Da Todo] Categoria: Admin", planner_item.note)

    def test_add_task_as_reminder(self):
        self.client.login(username="todo_user", password="test1234")
        response = self.client.post(
            "/todo/api/add",
            {
                "title": "Ricordati rinnovo",
                "item_type": Task.ItemType.REMINDER,
                "due_date": "",
                "status": Task.Status.OPEN,
                "priority": Task.Priority.LOW,
                "project_choice": "",
                "project_name": "",
                "note": "Controlla il contratto",
            },
        )
        self.assertEqual(response.status_code, 302)
        task = Task.objects.get(owner=self.user, title="Ricordati rinnovo")
        self.assertEqual(task.item_type, Task.ItemType.REMINDER)

    def test_add_task_as_appointment(self):
        self.client.login(username="todo_user", password="test1234")
        response = self.client.post(
            "/todo/api/add",
            {
                "title": "Call cliente ore 15",
                "item_type": Task.ItemType.APPOINTMENT,
                "due_date": "2026-03-02",
                "due_time": "15:00",
                "status": Task.Status.OPEN,
                "priority": Task.Priority.MEDIUM,
                "project_choice": "",
                "project_name": "",
                "note": "",
            },
        )
        self.assertEqual(response.status_code, 302)
        task = Task.objects.get(owner=self.user, title="Call cliente ore 15")
        self.assertEqual(task.item_type, Task.ItemType.APPOINTMENT)
        self.assertEqual(task.due_time.strftime("%H:%M"), "15:00")

    def test_add_task_with_existing_category(self):
        category = Category.objects.create(owner=self.user, name="Clienti")
        self.client.login(username="todo_user", password="test1234")
        response = self.client.post(
            "/todo/api/add",
            {
                "title": "Follow-up cliente",
                "item_type": Task.ItemType.TASK,
                "status": Task.Status.OPEN,
                "priority": Task.Priority.MEDIUM,
                "project_choice": "",
                "project_name": "",
                "category_choice": str(category.id),
                "category_name": "",
                "note": "",
            },
        )
        self.assertEqual(response.status_code, 302)
        task = Task.objects.get(owner=self.user, title="Follow-up cliente")
        self.assertEqual(task.category_id, category.id)

    def test_add_task_creates_new_category_if_requested(self):
        self.client.login(username="todo_user", password="test1234")
        response = self.client.post(
            "/todo/api/add",
            {
                "title": "Task con nuova categoria",
                "item_type": Task.ItemType.TASK,
                "status": Task.Status.OPEN,
                "priority": Task.Priority.LOW,
                "project_choice": "",
                "project_name": "",
                "category_choice": "__new__",
                "category_name": "Backoffice",
                "note": "",
            },
        )
        self.assertEqual(response.status_code, 302)
        task = Task.objects.get(owner=self.user, title="Task con nuova categoria")
        category = Category.objects.get(owner=self.user, id=task.category_id)
        self.assertTrue(category.name.startswith("Nuovo"))
        self.assertEqual(task.category_id, category.id)

    def test_set_status_htmx_returns_oob_fragment(self):
        task = Task.objects.create(
            owner=self.user,
            title="Task status htmx",
            item_type=Task.ItemType.TASK,
            status=Task.Status.OPEN,
            priority=Task.Priority.MEDIUM,
        )
        self.client.login(username="todo_user", password="test1234")
        response = self.client.post(
            "/todo/api/status",
            {"id": str(task.id), "status": Task.Status.DONE},
            HTTP_HX_REQUEST="true",
        )
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, f'id="todo-task-row-{task.id}"')
        self.assertContains(response, 'hx-swap-oob="outerHTML"')
        task.refresh_from_db()
        self.assertEqual(task.status, Task.Status.DONE)

    def test_set_status_non_htmx_redirects(self):
        task = Task.objects.create(
            owner=self.user,
            title="Task status redirect",
            item_type=Task.ItemType.TASK,
            status=Task.Status.OPEN,
            priority=Task.Priority.LOW,
        )
        self.client.login(username="todo_user", password="test1234")
        response = self.client.post(
            "/todo/api/status",
            {"id": str(task.id), "status": Task.Status.IN_PROGRESS},
        )
        self.assertEqual(response.status_code, 302)
        self.assertEqual(response.url, "/todo/")
        task.refresh_from_db()
        self.assertEqual(task.status, Task.Status.IN_PROGRESS)
