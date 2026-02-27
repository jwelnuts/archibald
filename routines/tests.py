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
