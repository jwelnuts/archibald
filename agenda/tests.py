import json
from datetime import date, timedelta
from decimal import Decimal

from django.contrib.auth import get_user_model
from django.test import TestCase

from core.models import UserNavConfig
from planner.models import PlannerItem
from routines.models import Routine, RoutineCheck, RoutineItem
from todo.models import Task

from .models import AgendaItem, WorkLog


class AgendaDashboardTests(TestCase):
    def setUp(self):
        self.user = get_user_model().objects.create_user(username="agenda_user", password="test1234")

    def test_dashboard_includes_integrated_day_items(self):
        due = date(2026, 2, 26)
        AgendaItem.objects.create(
            owner=self.user,
            title="Scrivere report",
            due_date=due,
            item_type=AgendaItem.ItemType.ACTIVITY,
        )
        Task.objects.create(
            owner=self.user,
            title="Mandare mail",
            due_date=due,
            item_type=Task.ItemType.REMINDER,
            status=Task.Status.OPEN,
        )
        PlannerItem.objects.create(
            owner=self.user,
            title="Pagare hosting",
            due_date=due,
            status=PlannerItem.Status.PLANNED,
        )
        routine = Routine.objects.create(
            owner=self.user,
            name="Routine ufficio",
            is_active=True,
        )
        routine_item = RoutineItem.objects.create(
            owner=self.user,
            routine=routine,
            title="Standup team",
            weekday=due.weekday(),
            is_active=True,
        )
        RoutineCheck.objects.create(
            owner=self.user,
            item=routine_item,
            week_start=due - timedelta(days=due.weekday()),
            status=RoutineCheck.Status.DONE,
        )
        WorkLog.objects.create(owner=self.user, work_date=due, hours=Decimal("7.50"))

        self.client.login(username="agenda_user", password="test1234")
        response = self.client.get("/agenda/?month=2026-02&selected=2026-02-26")
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Scrivere report")
        self.assertContains(response, "Mandare mail")
        self.assertContains(response, "Pagare hosting")
        self.assertContains(response, "Standup team")
        self.assertEqual(response.context["month_total_hours"], "7.5")

    def test_add_todo_item_from_agenda_uses_todo_model(self):
        self.client.login(username="agenda_user", password="test1234")
        response = self.client.post(
            "/agenda/?month=2026-02&selected=2026-02-10",
            {
                "action": "add_todo_item",
                "title": "Ricordati revisione",
                "item_type": Task.ItemType.REMINDER,
                "due_date": "2026-02-11",
                "due_time": "15:45",
                "status": Task.Status.OPEN,
                "priority": Task.Priority.MEDIUM,
                "project_choice": "",
                "project_name": "",
                "note": "Porta il report",
            },
        )
        self.assertEqual(response.status_code, 302)
        task = Task.objects.get(owner=self.user, title="Ricordati revisione")
        self.assertEqual(task.item_type, Task.ItemType.REMINDER)
        self.assertEqual(task.due_time.strftime("%H:%M"), "15:45")

    def test_log_hours_updates_same_day(self):
        self.client.login(username="agenda_user", password="test1234")
        first = self.client.post(
            "/agenda/?month=2026-02&selected=2026-02-12",
            {
                "action": "log_hours",
                "work_date": "2026-02-12",
                "time_start": "09:00",
                "time_end": "15:00",
                "lunch_break_minutes": "0",
                "note": "Sviluppo",
            },
        )
        self.assertEqual(first.status_code, 302)
        second = self.client.post(
            "/agenda/?month=2026-02&selected=2026-02-12",
            {
                "action": "log_hours",
                "work_date": "2026-02-12",
                "time_start": "09:00",
                "time_end": "17:15",
                "lunch_break_minutes": "0",
                "note": "Sviluppo + review",
            },
        )
        self.assertEqual(second.status_code, 302)
        self.assertEqual(WorkLog.objects.filter(owner=self.user, work_date="2026-02-12").count(), 1)
        log = WorkLog.objects.get(owner=self.user, work_date="2026-02-12")
        self.assertEqual(log.hours, Decimal("8.25"))
        self.assertEqual(log.time_start.strftime("%H:%M"), "09:00")
        self.assertEqual(log.time_end.strftime("%H:%M"), "17:15")

    def test_log_hours_subtracts_lunch_break(self):
        self.client.login(username="agenda_user", password="test1234")
        response = self.client.post(
            "/agenda/?month=2026-02&selected=2026-02-13",
            {
                "action": "log_hours",
                "work_date": "2026-02-13",
                "time_start": "09:00",
                "time_end": "18:00",
                "lunch_break_minutes": "60",
                "note": "Giornata completa",
            },
        )
        self.assertEqual(response.status_code, 302)
        log = WorkLog.objects.get(owner=self.user, work_date="2026-02-13")
        self.assertEqual(log.hours, Decimal("8.00"))
        self.assertEqual(log.lunch_break_minutes, 60)

    def test_log_hours_keeps_zero_break_when_field_missing(self):
        self.client.login(username="agenda_user", password="test1234")
        response = self.client.post(
            "/agenda/?month=2026-02&selected=2026-02-14",
            {
                "action": "log_hours",
                "work_date": "2026-02-14",
                "time_start": "08:00",
                "time_end": "18:00",
                "note": "Senza pausa esplicita",
            },
        )
        self.assertEqual(response.status_code, 302)
        log = WorkLog.objects.get(owner=self.user, work_date="2026-02-14")
        self.assertEqual(log.hours, Decimal("10.00"))
        self.assertEqual(log.lunch_break_minutes, 0)

    def test_add_planner_item_from_agenda_uses_planner_model(self):
        self.client.login(username="agenda_user", password="test1234")
        response = self.client.post(
            "/agenda/?month=2026-02&selected=2026-02-10",
            {
                "action": "add_planner_item",
                "planner-title": "Nuova voce planner da agenda",
                "planner-due_date": "2026-02-15",
                "planner-amount": "49.90",
                "planner-status": PlannerItem.Status.PLANNED,
                "planner-category_choice": "",
                "planner-category_name": "",
                "planner-project_choice": "",
                "planner-project_name": "",
                "planner-note": "Promemoria creato in agenda",
            },
        )
        self.assertEqual(response.status_code, 302)
        self.assertIn("month=2026-02", response.url)
        self.assertIn("selected=2026-02-15", response.url)

        item = PlannerItem.objects.get(owner=self.user, title="Nuova voce planner da agenda")
        self.assertEqual(item.status, PlannerItem.Status.PLANNED)
        self.assertEqual(str(item.amount), "49.90")
        self.assertEqual(item.note, "Promemoria creato in agenda")


class AgendaLiveEndpointsTests(TestCase):
    def setUp(self):
        self.user = get_user_model().objects.create_user(username="agenda_live_user", password="test1234")

    def test_agenda_preferences_requires_login(self):
        response = self.client.post(
            "/agenda/preferences",
            data=json.dumps({"density": "compact", "accent": "green", "sections": ["snapshot"]}),
            content_type="application/json",
        )
        self.assertEqual(response.status_code, 302)
        self.assertIn("/accounts/login/", response.url)

    def test_agenda_preferences_saves_normalized_payload(self):
        self.client.login(username="agenda_live_user", password="test1234")
        response = self.client.post(
            "/agenda/preferences",
            data=json.dumps(
                {
                    "density": "compact",
                    "accent": "rose",
                    "sections": ["snapshot", "panel", "unknown"],
                }
            ),
            content_type="application/json",
        )
        self.assertEqual(response.status_code, 200)
        nav_cfg = UserNavConfig.objects.get(user=self.user)
        prefs = nav_cfg.config.get("agenda_preferences", {})
        self.assertEqual(prefs.get("density"), "compact")
        self.assertEqual(prefs.get("accent"), "rose")
        self.assertEqual(prefs.get("sections"), ["snapshot", "panel"])

    def test_panel_and_snapshot_require_login(self):
        panel = self.client.get("/agenda/panel")
        snapshot = self.client.get("/agenda/snapshot")
        self.assertEqual(panel.status_code, 302)
        self.assertEqual(snapshot.status_code, 302)
        self.assertIn("/accounts/login/", panel.url)
        self.assertIn("/accounts/login/", snapshot.url)

    def test_panel_and_snapshot_render_for_authenticated_user(self):
        self.client.login(username="agenda_live_user", password="test1234")
        panel = self.client.get("/agenda/panel?month=2026-02&selected=2026-02-10")
        snapshot = self.client.get("/agenda/snapshot?month=2026-02&selected=2026-02-10")
        self.assertEqual(panel.status_code, 200)
        self.assertEqual(snapshot.status_code, 200)
        self.assertContains(panel, "agenda-live-panel")
        self.assertContains(snapshot, "agenda-snapshot-card")

    def test_item_action_htmx_returns_panel_and_refresh_trigger(self):
        item = AgendaItem.objects.create(
            owner=self.user,
            title="Follow up cliente",
            due_date=date(2026, 2, 12),
            item_type=AgendaItem.ItemType.ACTIVITY,
            status=AgendaItem.Status.PLANNED,
        )
        self.client.login(username="agenda_live_user", password="test1234")

        response = self.client.post(
            "/agenda/item-action",
            {
                "action": "toggle_item",
                "item_id": str(item.id),
                "month": "2026-02",
                "selected": "2026-02-12",
            },
            HTTP_HX_REQUEST="true",
        )
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.headers.get("HX-Trigger"), "agenda:refresh-snapshot")
        self.assertContains(response, "agenda-live-panel")

        item.refresh_from_db()
        self.assertEqual(item.status, AgendaItem.Status.DONE)

    def test_dashboard_context_exposes_saved_agenda_preferences(self):
        self.client.login(username="agenda_live_user", password="test1234")
        UserNavConfig.objects.create(
            user=self.user,
            config={
                "agenda_preferences": {
                    "density": "compact",
                    "accent": "amber",
                    "sections": ["snapshot", "panel"],
                }
            },
        )
        response = self.client.get("/agenda/")
        self.assertEqual(response.status_code, 200)
        prefs = response.context["agenda_preferences"]
        self.assertEqual(prefs["density"], "compact")
        self.assertEqual(prefs["accent"], "amber")
        self.assertEqual(prefs["sections"], ["snapshot", "panel"])
