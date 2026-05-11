from django.contrib.auth import get_user_model
from django.test import TestCase

from .models import PlannerItem


class PlannerDashboardTests(TestCase):
    def setUp(self):
        self.user = get_user_model().objects.create_user(username="planner_user", password="test1234")

    def test_dashboard_still_loads_with_planned_items(self):
        PlannerItem.objects.create(
            owner=self.user,
            title="Spesa futura",
            status=PlannerItem.Status.PLANNED,
        )
        self.client.login(username="planner_user", password="test1234")
        response = self.client.get("/planner/")
        self.assertEqual(response.status_code, 200)
        self.assertIn("upcoming", response.context)
        self.assertIn("counts", response.context)

    def test_dashboard_filters_by_status(self):
        PlannerItem.objects.create(owner=self.user, title="Pianificato", status=PlannerItem.Status.PLANNED)
        PlannerItem.objects.create(owner=self.user, title="Completato", status=PlannerItem.Status.DONE)
        PlannerItem.objects.create(owner=self.user, title="Saltato", status=PlannerItem.Status.SKIPPED)
        self.client.login(username="planner_user", password="test1234")

        response = self.client.get("/planner/?status=planned")
        self.assertEqual(response.status_code, 200)
        self.assertEqual(len(response.context["upcoming"]), 1)

    def test_dashboard_filters_by_query(self):
        PlannerItem.objects.create(owner=self.user, title="Spesa per casa", status=PlannerItem.Status.PLANNED)
        PlannerItem.objects.create(owner=self.user, title="Vacanza mare", status=PlannerItem.Status.PLANNED)
        self.client.login(username="planner_user", password="test1234")

        response = self.client.get("/planner/?q=casa")
        self.assertEqual(response.status_code, 200)
        self.assertEqual(len(response.context["upcoming"]), 1)

    def test_add_item_creates_planner_item(self):
        self.client.login(username="planner_user", password="test1234")
        response = self.client.post("/planner/add", {
            "title": "Nuova spesa",
            "status": "PLANNED",
        })
        self.assertEqual(response.status_code, 302)
        self.assertTrue(PlannerItem.objects.filter(title="Nuova spesa").exists())

    def test_update_item_modifies_planner_item(self):
        item = PlannerItem.objects.create(owner=self.user, title="Vecchio titolo", status=PlannerItem.Status.PLANNED)
        self.client.login(username="planner_user", password="test1234")
        response = self.client.post(f"/planner/update?id={item.id}", {
            "title": "Nuovo titolo",
            "status": "PLANNED",
        })
        self.assertEqual(response.status_code, 302)
        item.refresh_from_db()
        self.assertEqual(item.title, "Nuovo titolo")

    def test_remove_item_deletes_planner_item(self):
        item = PlannerItem.objects.create(owner=self.user, title="Da eliminare", status=PlannerItem.Status.PLANNED)
        self.client.login(username="planner_user", password="test1234")
        response = self.client.post(f"/planner/remove?id={item.id}")
        self.assertEqual(response.status_code, 302)
        self.assertFalse(PlannerItem.objects.filter(id=item.id).exists())

    def test_api_toggle_status(self):
        item = PlannerItem.objects.create(owner=self.user, title="Test item", status=PlannerItem.Status.PLANNED)
        self.client.login(username="planner_user", password="test1234")
        response = self.client.post(
            f"/planner/api/toggle-status/{item.id}/",
            {"status": "DONE"},
            content_type="application/json",
            HTTP_X_REQUESTED_WITH="XMLHttpRequest",
        )
        self.assertEqual(response.status_code, 200)
        item.refresh_from_db()
        self.assertEqual(item.status, PlannerItem.Status.DONE)

    def test_api_delete_item(self):
        item = PlannerItem.objects.create(owner=self.user, title="Test delete", status=PlannerItem.Status.PLANNED)
        self.client.login(username="planner_user", password="test1234")
        response = self.client.post(
            f"/planner/api/delete/{item.id}/",
            {},
            content_type="application/json",
            HTTP_X_REQUESTED_WITH="XMLHttpRequest",
        )
        self.assertEqual(response.status_code, 200)
        self.assertFalse(PlannerItem.objects.filter(id=item.id).exists())