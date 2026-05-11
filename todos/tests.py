from datetime import date, timedelta

from django.contrib.auth import get_user_model
from django.test import TestCase

from todos.models import TodoList, TodoCategory, TodoRecurrence, TodoItem


class TodoRecurrenceHTMXTests(TestCase):
    def setUp(self):
        self.user = get_user_model().objects.create_user(username="todo_user", password="test12345")
        self.todo = TodoList.objects.create(owner=self.user, name="TodoList test", is_active=True)
        self.item = TodoItem.objects.create(
            owner=self.user,
            todo=self.todo,
            title="TodoItem todo",
            weekday=0,
            is_active=True,
        )
        today = date.today()
        self.week_start = today - timedelta(days=today.weekday())
        self.client.login(username="todo_user", password="test12345")

    def test_check_item_htmx_returns_oob_fragment(self):
        response = self.client.post(
            "/todos/check",
            {
                "item_id": str(self.item.id),
                "week": self.week_start.isoformat(),
                "status": TodoRecurrence.Status.SKIPPED,
            },
            HTTP_HX_REQUEST="true",
        )

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, f'id="todo-status-{self.item.id}"')
        self.assertContains(response, TodoRecurrence.Status.SKIPPED)
        self.assertContains(response, 'hx-swap-oob="outerHTML"')

        check = TodoRecurrence.objects.get(owner=self.user, item=self.item, week_start=self.week_start)
        self.assertEqual(check.status, TodoRecurrence.Status.SKIPPED)

    def test_check_item_non_htmx_redirects(self):
        response = self.client.post(
            "/todos/check",
            {
                "item_id": str(self.item.id),
                "week": self.week_start.isoformat(),
                "status": TodoRecurrence.Status.DONE,
            },
        )
        self.assertEqual(response.status_code, 302)

    def test_check_item_saves_custom_data_and_returns_data_oob(self):
        self.item.schema = {
            "fields": [
                {"name": "note_done", "label": "Nota", "type": "text"},
            ]
        }
        self.item.save(update_fields=["schema"])

        response = self.client.post(
            "/todos/check",
            {
                "item_id": str(self.item.id),
                "week": self.week_start.isoformat(),
                "status": TodoRecurrence.Status.DONE,
                "data_note_done": "Completata bene",
            },
            HTTP_HX_REQUEST="true",
        )

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, f'id="todo-data-container-{self.item.id}"')
        self.assertContains(response, f'id="todo-values-{self.item.id}"')
        self.assertContains(response, "Completata bene")
        check = TodoRecurrence.objects.get(owner=self.user, item=self.item, week_start=self.week_start)
        self.assertEqual(check.status, TodoRecurrence.Status.DONE)
        self.assertEqual(check.data.get("note_done"), "Completata bene")


class TodoItemCreationTests(TestCase):
    def setUp(self):
        self.user = get_user_model().objects.create_user(username="todo_creator", password="test12345")
        self.todo = TodoList.objects.create(owner=self.user, name="TodoList creator", is_active=True)
        self.client.login(username="todo_creator", password="test12345")

    def test_add_item_all_days_copies_schema(self):
        response = self.client.post(
            "/todos/items/add",
            {
                "todo_choice": str(self.todo.id),
                "project_choice": "",
                "project_name": "",
                "title": "Stretching",
                "weekday": "ALL",
                "time_start": "",
                "time_end": "",
                "note": "Ogni giorno",
                "schema": '{"fields":[{"name":"energia","label":"Energia","type":"number"}]}',
                "is_active": "on",
            },
        )
        self.assertEqual(response.status_code, 302)

        items = TodoItem.objects.filter(owner=self.user, todo=self.todo, title="Stretching")
        self.assertEqual(items.count(), 7)
        for item in items:
            self.assertEqual(item.schema.get("fields", [{}])[0].get("name"), "energia")

    def test_dashboard_quick_add_todo_creates_todo(self):
        today = date.today()
        week_start = today - timedelta(days=today.weekday())

        response = self.client.post(
            "/todos/",
            {
                "quick_action": "add_todo",
                "week": week_start.isoformat(),
                "name": "TodoList lampo",
                "description": "Creata da dashboard",
            },
        )

        self.assertEqual(response.status_code, 302)
        self.assertTrue(TodoList.objects.filter(owner=self.user, name="TodoList lampo", is_active=True).exists())

    def test_dashboard_quick_add_item_creates_category(self):
        today = date.today()
        week_start = today - timedelta(days=today.weekday())

        category_name = "Salute"
        response = self.client.post(
            "/todos/",
            {
                "quick_action": "add_item",
                "week": week_start.isoformat(),
                "todo_choice": str(self.todo.id),
                "title": "TodoItem con categoria",
                "weekday": "1",
                "category_choice": "__new__",
                "category_name": category_name,
            },
        )

        self.assertEqual(response.status_code, 302)
        category = TodoCategory.objects.filter(owner=self.user, name=category_name).first()
        self.assertIsNotNone(category)
        item = TodoItem.objects.filter(owner=self.user, title="TodoItem con categoria").first()
        self.assertIsNotNone(item)
        self.assertEqual(item.category_id, category.id)

    def test_dashboard_quick_add_item_creates_item(self):
        today = date.today()
        week_start = today - timedelta(days=today.weekday())

        response = self.client.post(
            "/todos/",
            {
                "quick_action": "add_item",
                "week": week_start.isoformat(),
                "todo_choice": str(self.todo.id),
                "title": "TodoItem veloce",
                "weekday": "2",
                "time_start": "08:15",
                "note": "Da dashboard",
            },
        )

        self.assertEqual(response.status_code, 302)
        created = TodoItem.objects.filter(owner=self.user, todo=self.todo, title="TodoItem veloce")
        self.assertEqual(created.count(), 1)
        self.assertEqual(created.first().weekday, 2)

    def test_dashboard_can_filter_by_category(self):
        category_a = TodoCategory.objects.create(owner=self.user, name="Fitness", is_active=True)
        category_b = TodoCategory.objects.create(owner=self.user, name="Lavoro", is_active=True)
        todo_a = TodoList.objects.create(owner=self.user, name="Morning", is_active=True)
        todo_b = TodoList.objects.create(owner=self.user, name="Office", is_active=True)
        TodoItem.objects.create(owner=self.user, todo=todo_a, category=category_a, title="Pushup", weekday=0, is_active=True)
        TodoItem.objects.create(owner=self.user, todo=todo_b, category=category_b, title="Mail check", weekday=0, is_active=True)

        response = self.client.get(f"/todos/?category={category_a.id}")

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Pushup")
        self.assertNotContains(response, "Mail check")


class TodoListCrudTests(TestCase):
    def setUp(self):
        self.user = get_user_model().objects.create_user(username="todo_crud", password="test12345")
        self.todo = TodoList.objects.create(
            owner=self.user,
            name="TodoList iniziale",
            description="Da aggiornare",
            is_active=True,
        )
        self.item = TodoItem.objects.create(
            owner=self.user,
            todo=self.todo,
            title="Attivita iniziale",
            weekday=0,
            is_active=True,
        )
        self.client.login(username="todo_crud", password="test12345")

    def test_update_todo_updates_fields(self):
        response = self.client.post(
            f"/todos/api/update?id={self.todo.id}",
            {
                "name": "TodoList aggiornata",
                "description": "Descrizione nuova",
                "is_active": "on",
            },
        )

        self.assertEqual(response.status_code, 302)
        self.todo.refresh_from_db()
        self.assertEqual(self.todo.name, "TodoList aggiornata")
        self.assertEqual(self.todo.description, "Descrizione nuova")
        self.assertTrue(self.todo.is_active)

    def test_remove_todo_deletes_todo_and_items(self):
        response = self.client.post(f"/todos/api/remove?id={self.todo.id}")

        self.assertEqual(response.status_code, 302)
        self.assertFalse(TodoList.objects.filter(id=self.todo.id).exists())
        self.assertFalse(TodoItem.objects.filter(id=self.item.id).exists())

    def test_dashboard_shows_edit_and_remove_links(self):
        response = self.client.get("/todos/")

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, f'/todos/api/update?id={self.todo.id}')
        self.assertContains(response, f'/todos/api/remove?id={self.todo.id}')
        self.assertContains(response, f'/todos/items/update?id={self.item.id}')
        self.assertContains(response, f'/todos/items/remove?id={self.item.id}')
        self.assertContains(response, 'data-todo-day-jump')


class TodoListStatsPageTests(TestCase):
    def setUp(self):
        self.user = get_user_model().objects.create_user(username="todo_stats", password="test12345")
        self.todo_a = TodoList.objects.create(owner=self.user, name="TodoList A", is_active=True)
        self.todo_b = TodoList.objects.create(owner=self.user, name="TodoList B", is_active=True)
        self.item_a1 = TodoItem.objects.create(owner=self.user, todo=self.todo_a, title="A1", weekday=0)
        self.item_a2 = TodoItem.objects.create(owner=self.user, todo=self.todo_a, title="A2", weekday=1)
        self.item_b1 = TodoItem.objects.create(owner=self.user, todo=self.todo_b, title="B1", weekday=2)
        today = date.today()
        self.week_start = today - timedelta(days=today.weekday())
        self.prev_week = self.week_start - timedelta(days=7)
        self.client.login(username="todo_stats", password="test12345")

    def test_stats_page_shows_week_and_overall_aggregates(self):
        TodoRecurrence.objects.create(
            owner=self.user,
            item=self.item_a1,
            week_start=self.week_start,
            status=TodoRecurrence.Status.DONE,
        )
        TodoRecurrence.objects.create(
            owner=self.user,
            item=self.item_a2,
            week_start=self.week_start,
            status=TodoRecurrence.Status.PLANNED,
        )
        TodoRecurrence.objects.create(
            owner=self.user,
            item=self.item_b1,
            week_start=self.week_start,
            status=TodoRecurrence.Status.SKIPPED,
        )
        TodoRecurrence.objects.create(
            owner=self.user,
            item=self.item_a1,
            week_start=self.prev_week,
            status=TodoRecurrence.Status.DONE,
        )

        response = self.client.get(f"/todos/stats?week={self.week_start.isoformat()}")
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Statistiche todo")

        week_stats = response.context["week_stats"]
        self.assertEqual(week_stats["total"], 3)
        self.assertEqual(week_stats["done"], 1)
        self.assertEqual(week_stats["planned"], 1)
        self.assertEqual(week_stats["skipped"], 1)
        self.assertEqual(week_stats["completion_rate"], 33.3)

        overall_stats = response.context["overall_stats"]
        self.assertEqual(overall_stats["total"], 4)
        self.assertEqual(overall_stats["done"], 2)
        self.assertEqual(overall_stats["planned"], 1)
        self.assertEqual(overall_stats["skipped"], 1)
        self.assertEqual(overall_stats["completion_rate"], 50.0)

        self.assertEqual(len(response.context["trend"]), 8)
        self.assertGreaterEqual(len(response.context["todo_stats"]), 2)

    def test_stats_page_can_filter_by_single_todo(self):
        TodoRecurrence.objects.create(
            owner=self.user,
            item=self.item_a1,
            week_start=self.week_start,
            status=TodoRecurrence.Status.DONE,
        )
        TodoRecurrence.objects.create(
            owner=self.user,
            item=self.item_a2,
            week_start=self.week_start,
            status=TodoRecurrence.Status.PLANNED,
        )
        TodoRecurrence.objects.create(
            owner=self.user,
            item=self.item_b1,
            week_start=self.week_start,
            status=TodoRecurrence.Status.SKIPPED,
        )
        TodoRecurrence.objects.create(
            owner=self.user,
            item=self.item_a1,
            week_start=self.prev_week,
            status=TodoRecurrence.Status.DONE,
        )

        response = self.client.get(
            f"/todos/stats?week={self.week_start.isoformat()}&todo={self.todo_a.id}"
        )
        self.assertEqual(response.status_code, 200)

        selected = response.context["selected_todo"]
        self.assertIsNotNone(selected)
        self.assertEqual(selected.id, self.todo_a.id)

        week_stats = response.context["week_stats"]
        self.assertEqual(week_stats["total"], 2)
        self.assertEqual(week_stats["done"], 1)
        self.assertEqual(week_stats["planned"], 1)
        self.assertEqual(week_stats["skipped"], 0)
        self.assertEqual(week_stats["completion_rate"], 50.0)

        overall_stats = response.context["overall_stats"]
        self.assertEqual(overall_stats["total"], 3)
        self.assertEqual(overall_stats["done"], 2)
        self.assertEqual(overall_stats["planned"], 1)
        self.assertEqual(overall_stats["skipped"], 0)
        self.assertEqual(overall_stats["completion_rate"], 66.7)

        todo_stats = response.context["todo_stats"]
        self.assertEqual(len(todo_stats), 1)
        self.assertEqual(todo_stats[0]["name"], "TodoList A")
