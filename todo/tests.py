from unittest.mock import patch

from django.test import TestCase
from django.contrib.auth import get_user_model

from core.models import DavAccount
from projects.models import Category, Project

from .dav_sync import DavSyncOutcome, push_task_to_vtodo, sync_all_tasks_to_vtodo
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

    def test_dashboard_includes_dav_vtodo_context(self):
        self.client.login(username="todo_user", password="test1234")
        response = self.client.get("/todo/")
        self.assertEqual(response.status_code, 200)
        self.assertIn("dav_vtodo_collection_slug", response.context)
        self.assertIn("dav_vtodo_collection_path", response.context)
        self.assertIn("dav_vtodo_collection_url", response.context)

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

    @patch("todo.views.sync_all_tasks_to_vtodo")
    def test_sync_vtodo_endpoint_redirects(self, mock_sync):
        mock_sync.return_value = {"total": 2, "synced": 2, "failed": 0, "error": ""}
        self.client.login(username="todo_user", password="test1234")
        response = self.client.post("/todo/api/sync-vtodo")
        self.assertEqual(response.status_code, 302)
        self.assertEqual(response.url, "/todo/")
        mock_sync.assert_called_once()


class TodoDavSyncTests(TestCase):
    def setUp(self):
        self.user = get_user_model().objects.create_user(username="todo_dav_user", password="test1234")
        self.task = Task.objects.create(
            owner=self.user,
            title="Task DAV",
            item_type=Task.ItemType.TASK,
            status=Task.Status.OPEN,
            priority=Task.Priority.MEDIUM,
        )

    @patch("todo.dav_sync._dav_request")
    @patch("todo.dav_sync._ensure_collection")
    def test_push_task_to_vtodo_success(self, mock_ensure, mock_request):
        DavAccount.objects.create(
            user=self.user,
            dav_username="todo_dav_user",
            password_hash="$2b$12$T7Y8P2hso3Ubn8hY2X43NOmJ4xWjQ0X1E4p9h8e2xK0P8IhW5M9sC",
            is_active=True,
        )
        mock_ensure.return_value = DavSyncOutcome(ok=True)
        mock_request.return_value = (201, {}, "")

        with self.settings(
            CALDAV_ENABLED=True,
            CALDAV_BASE_URL="https://example.com/dav/",
            CALDAV_SERVICE_USERNAME="archibald",
            CALDAV_SERVICE_PASSWORD="secret",
            CALDAV_DEFAULT_USER_COLLECTION="personal_dav",
        ):
            result = push_task_to_vtodo(self.task)

        self.assertTrue(result.ok)
        self.assertEqual(mock_request.call_count, 1)

    def test_sync_all_tasks_to_vtodo_fails_without_dav_account(self):
        with self.settings(
            CALDAV_ENABLED=True,
            CALDAV_BASE_URL="https://example.com/dav/",
            CALDAV_SERVICE_USERNAME="archibald",
            CALDAV_SERVICE_PASSWORD="secret",
            CALDAV_DEFAULT_USER_COLLECTION="personal_dav",
        ):
            stats = sync_all_tasks_to_vtodo(self.user)
        self.assertEqual(stats["total"], 1)
        self.assertEqual(stats["synced"], 0)
        self.assertEqual(stats["failed"], 1)
