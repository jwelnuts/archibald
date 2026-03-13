from datetime import date, timedelta

from django.contrib.auth import get_user_model
from django.test import TestCase

from routines.models import Routine, RoutineCheck, RoutineItem


class RoutineCheckHTMXTests(TestCase):
    def setUp(self):
        self.user = get_user_model().objects.create_user(username="routine_user", password="test12345")
        self.routine = Routine.objects.create(owner=self.user, name="Routine test", is_active=True)
        self.item = RoutineItem.objects.create(
            owner=self.user,
            routine=self.routine,
            title="Task routine",
            weekday=0,
            is_active=True,
        )
        today = date.today()
        self.week_start = today - timedelta(days=today.weekday())
        self.client.login(username="routine_user", password="test12345")

    def test_check_item_htmx_returns_oob_fragment(self):
        response = self.client.post(
            "/routines/check",
            {
                "item_id": str(self.item.id),
                "week": self.week_start.isoformat(),
                "status": RoutineCheck.Status.SKIPPED,
            },
            HTTP_HX_REQUEST="true",
        )

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, f'id="routine-status-{self.item.id}"')
        self.assertContains(response, RoutineCheck.Status.SKIPPED)
        self.assertContains(response, 'hx-swap-oob="outerHTML"')

        check = RoutineCheck.objects.get(owner=self.user, item=self.item, week_start=self.week_start)
        self.assertEqual(check.status, RoutineCheck.Status.SKIPPED)

    def test_check_item_non_htmx_redirects(self):
        response = self.client.post(
            "/routines/check",
            {
                "item_id": str(self.item.id),
                "week": self.week_start.isoformat(),
                "status": RoutineCheck.Status.DONE,
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
            "/routines/check",
            {
                "item_id": str(self.item.id),
                "week": self.week_start.isoformat(),
                "status": RoutineCheck.Status.DONE,
                "data_note_done": "Completata bene",
            },
            HTTP_HX_REQUEST="true",
        )

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, f'id="routine-data-container-{self.item.id}"')
        check = RoutineCheck.objects.get(owner=self.user, item=self.item, week_start=self.week_start)
        self.assertEqual(check.status, RoutineCheck.Status.DONE)
        self.assertEqual(check.data.get("note_done"), "Completata bene")


class RoutineItemCreationTests(TestCase):
    def setUp(self):
        self.user = get_user_model().objects.create_user(username="routine_creator", password="test12345")
        self.routine = Routine.objects.create(owner=self.user, name="Routine creator", is_active=True)
        self.client.login(username="routine_creator", password="test12345")

    def test_add_item_all_days_copies_schema(self):
        response = self.client.post(
            "/routines/items/add",
            {
                "routine_choice": str(self.routine.id),
                "routine_name": "",
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

        items = RoutineItem.objects.filter(owner=self.user, routine=self.routine, title="Stretching")
        self.assertEqual(items.count(), 7)
        for item in items:
            self.assertEqual(item.schema.get("fields", [{}])[0].get("name"), "energia")


class RoutineCrudTests(TestCase):
    def setUp(self):
        self.user = get_user_model().objects.create_user(username="routine_crud", password="test12345")
        self.routine = Routine.objects.create(
            owner=self.user,
            name="Routine iniziale",
            description="Da aggiornare",
            is_active=True,
        )
        self.item = RoutineItem.objects.create(
            owner=self.user,
            routine=self.routine,
            title="Attivita iniziale",
            weekday=0,
            is_active=True,
        )
        self.client.login(username="routine_crud", password="test12345")

    def test_update_routine_updates_fields(self):
        response = self.client.post(
            f"/routines/api/update?id={self.routine.id}",
            {
                "name": "Routine aggiornata",
                "description": "Descrizione nuova",
                "is_active": "on",
            },
        )

        self.assertEqual(response.status_code, 302)
        self.routine.refresh_from_db()
        self.assertEqual(self.routine.name, "Routine aggiornata")
        self.assertEqual(self.routine.description, "Descrizione nuova")
        self.assertTrue(self.routine.is_active)

    def test_remove_routine_deletes_routine_and_items(self):
        response = self.client.post(f"/routines/api/remove?id={self.routine.id}")

        self.assertEqual(response.status_code, 302)
        self.assertFalse(Routine.objects.filter(id=self.routine.id).exists())
        self.assertFalse(RoutineItem.objects.filter(id=self.item.id).exists())

    def test_dashboard_shows_edit_and_remove_links(self):
        response = self.client.get("/routines/")

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, f'/routines/api/update?id={self.routine.id}')
        self.assertContains(response, f'/routines/api/remove?id={self.routine.id}')
        self.assertContains(response, f'/routines/items/update?id={self.item.id}')
        self.assertContains(response, f'/routines/items/remove?id={self.item.id}')
        self.assertContains(response, 'data-routine-day-jump')


class RoutineStatsPageTests(TestCase):
    def setUp(self):
        self.user = get_user_model().objects.create_user(username="routine_stats", password="test12345")
        self.routine_a = Routine.objects.create(owner=self.user, name="Routine A", is_active=True)
        self.routine_b = Routine.objects.create(owner=self.user, name="Routine B", is_active=True)
        self.item_a1 = RoutineItem.objects.create(owner=self.user, routine=self.routine_a, title="A1", weekday=0)
        self.item_a2 = RoutineItem.objects.create(owner=self.user, routine=self.routine_a, title="A2", weekday=1)
        self.item_b1 = RoutineItem.objects.create(owner=self.user, routine=self.routine_b, title="B1", weekday=2)
        today = date.today()
        self.week_start = today - timedelta(days=today.weekday())
        self.prev_week = self.week_start - timedelta(days=7)
        self.client.login(username="routine_stats", password="test12345")

    def test_stats_page_shows_week_and_overall_aggregates(self):
        RoutineCheck.objects.create(
            owner=self.user,
            item=self.item_a1,
            week_start=self.week_start,
            status=RoutineCheck.Status.DONE,
        )
        RoutineCheck.objects.create(
            owner=self.user,
            item=self.item_a2,
            week_start=self.week_start,
            status=RoutineCheck.Status.PLANNED,
        )
        RoutineCheck.objects.create(
            owner=self.user,
            item=self.item_b1,
            week_start=self.week_start,
            status=RoutineCheck.Status.SKIPPED,
        )
        RoutineCheck.objects.create(
            owner=self.user,
            item=self.item_a1,
            week_start=self.prev_week,
            status=RoutineCheck.Status.DONE,
        )

        response = self.client.get(f"/routines/stats?week={self.week_start.isoformat()}")
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Statistiche routine")

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
        self.assertGreaterEqual(len(response.context["routine_stats"]), 2)

    def test_stats_page_can_filter_by_single_routine(self):
        RoutineCheck.objects.create(
            owner=self.user,
            item=self.item_a1,
            week_start=self.week_start,
            status=RoutineCheck.Status.DONE,
        )
        RoutineCheck.objects.create(
            owner=self.user,
            item=self.item_a2,
            week_start=self.week_start,
            status=RoutineCheck.Status.PLANNED,
        )
        RoutineCheck.objects.create(
            owner=self.user,
            item=self.item_b1,
            week_start=self.week_start,
            status=RoutineCheck.Status.SKIPPED,
        )
        RoutineCheck.objects.create(
            owner=self.user,
            item=self.item_a1,
            week_start=self.prev_week,
            status=RoutineCheck.Status.DONE,
        )

        response = self.client.get(
            f"/routines/stats?week={self.week_start.isoformat()}&routine={self.routine_a.id}"
        )
        self.assertEqual(response.status_code, 200)

        selected = response.context["selected_routine"]
        self.assertIsNotNone(selected)
        self.assertEqual(selected.id, self.routine_a.id)

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

        routine_stats = response.context["routine_stats"]
        self.assertEqual(len(routine_stats), 1)
        self.assertEqual(routine_stats[0]["name"], "Routine A")
