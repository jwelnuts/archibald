from datetime import date, timedelta
from decimal import Decimal

from django.contrib.auth import get_user_model
from django.test import TestCase

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

    def test_add_agenda_item(self):
        self.client.login(username="agenda_user", password="test1234")
        response = self.client.post(
            "/agenda/?month=2026-02&selected=2026-02-10",
            {
                "action": "add_item",
                "title": "Call cliente",
                "item_type": AgendaItem.ItemType.REMINDER,
                "due_date": "2026-02-10",
                "due_time": "09:30",
                "status": AgendaItem.Status.PLANNED,
                "project": "",
                "note": "Preparare documento",
            },
        )
        self.assertEqual(response.status_code, 302)
        item = AgendaItem.objects.get(owner=self.user, title="Call cliente")
        self.assertEqual(item.item_type, AgendaItem.ItemType.REMINDER)

    def test_log_hours_updates_same_day(self):
        self.client.login(username="agenda_user", password="test1234")
        first = self.client.post(
            "/agenda/?month=2026-02&selected=2026-02-12",
            {
                "action": "log_hours",
                "work_date": "2026-02-12",
                "hours": "6.00",
                "note": "Sviluppo",
            },
        )
        self.assertEqual(first.status_code, 302)
        second = self.client.post(
            "/agenda/?month=2026-02&selected=2026-02-12",
            {
                "action": "log_hours",
                "work_date": "2026-02-12",
                "hours": "8.25",
                "note": "Sviluppo + review",
            },
        )
        self.assertEqual(second.status_code, 302)
        self.assertEqual(WorkLog.objects.filter(owner=self.user, work_date="2026-02-12").count(), 1)
        log = WorkLog.objects.get(owner=self.user, work_date="2026-02-12")
        self.assertEqual(log.hours, Decimal("8.25"))
