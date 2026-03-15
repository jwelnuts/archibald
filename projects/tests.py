from datetime import date
from decimal import Decimal

from django.test import TestCase
from django.contrib.auth import get_user_model

from planner.models import PlannerItem
from routines.models import Routine, RoutineItem
from subscriptions.models import Account, Currency, Subscription
from todo.models import Task
from transactions.models import Transaction

from .models import Category, Customer, Project, ProjectNote, SubProject, SubProjectActivity


class ProjectStoryboardFormsTests(TestCase):
    def setUp(self):
        self.user = get_user_model().objects.create_user(username="proj_user", password="test1234")
        self.project = Project.objects.create(owner=self.user, name="Project Story")
        self.client.login(username="proj_user", password="test1234")

    def test_storyboard_add_note(self):
        response = self.client.post(
            f"/projects/storyboard?id={self.project.id}",
            {
                "form_kind": "note",
                "content": "<p>Nota test</p>",
            },
        )
        self.assertEqual(response.status_code, 302)
        self.assertEqual(ProjectNote.objects.filter(owner=self.user, project=self.project).count(), 1)

    def test_storyboard_add_task(self):
        response = self.client.post(
            f"/projects/storyboard?id={self.project.id}",
            {
                "form_kind": "task",
                "task-title": "Task da storyboard",
                "task-due_date": "",
                "task-status": Task.Status.OPEN,
                "task-priority": Task.Priority.HIGH,
                "task-note": "dettaglio task",
            },
        )
        self.assertEqual(response.status_code, 302)
        task = Task.objects.get(owner=self.user, title="Task da storyboard")
        self.assertEqual(task.project_id, self.project.id)

    def test_storyboard_add_planner_item(self):
        response = self.client.post(
            f"/projects/storyboard?id={self.project.id}",
            {
                "form_kind": "planner",
                "planner-title": "Planner da storyboard",
                "planner-due_date": "",
                "planner-status": PlannerItem.Status.PLANNED,
                "planner-note": "dettaglio planner",
            },
        )
        self.assertEqual(response.status_code, 302)
        planner_item = PlannerItem.objects.get(owner=self.user, title="Planner da storyboard")
        self.assertEqual(planner_item.project_id, self.project.id)


class ProjectStoryboardLogTests(TestCase):
    def setUp(self):
        self.user = get_user_model().objects.create_user(username="storyboard_log_user", password="test1234")
        self.client.login(username="storyboard_log_user", password="test1234")
        self.project = Project.objects.create(owner=self.user, name="Project Log")
        self.currency, _ = Currency.objects.get_or_create(code="EUR", defaults={"name": "Euro"})
        self.account = Account.objects.create(
            owner=self.user,
            name="Conto Storyboard",
            kind=Account.Kind.BANK,
            currency=self.currency,
            opening_balance=Decimal("0.00"),
            is_active=True,
        )
        ProjectNote.objects.create(owner=self.user, project=self.project, content="<p>Nota storyboard</p>")
        Task.objects.create(owner=self.user, project=self.project, title="Task storyboard", status=Task.Status.OPEN)
        PlannerItem.objects.create(
            owner=self.user, project=self.project, title="Reminder storyboard", status=PlannerItem.Status.PLANNED
        )
        Transaction.objects.create(
            owner=self.user,
            tx_type=Transaction.Type.EXPENSE,
            date=date(2026, 2, 10),
            amount=Decimal("12.50"),
            currency=self.currency,
            account=self.account,
            project=self.project,
            note="Spesa storyboard",
        )

    def test_storyboard_log_kind_filter(self):
        response = self.client.get(f"/projects/storyboard/log?id={self.project.id}&kind=note")
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Appunto progetto")
        self.assertNotContains(response, "Task storyboard")
        self.assertNotContains(response, "Reminder storyboard")

    def test_storyboard_log_search_filter(self):
        response = self.client.get(f"/projects/storyboard/log?id={self.project.id}&q=Spesa")
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Spesa storyboard")
        self.assertNotContains(response, "Nessuna voce trovata")


class ProjectDashboardContextTests(TestCase):
    def setUp(self):
        self.user = get_user_model().objects.create_user(username="proj_dash_user", password="test1234")
        self.client.login(username="proj_dash_user", password="test1234")
        self.customer = Customer.objects.create(owner=self.user, name="Cliente Uno")
        self.category = Category.objects.create(owner=self.user, name="Consulenza")
        self.active_project = Project.objects.create(
            owner=self.user,
            name="Progetto Attivo",
            customer=self.customer,
            category=self.category,
            is_archived=False,
        )
        self.archived_project = Project.objects.create(
            owner=self.user,
            name="Progetto Archiviato",
            customer=self.customer,
            category=self.category,
            is_archived=True,
        )
        self.currency, _ = Currency.objects.get_or_create(code="EUR", defaults={"name": "Euro"})
        self.account = Account.objects.create(
            owner=self.user,
            name="Conto Test",
            kind=Account.Kind.BANK,
            currency=self.currency,
            opening_balance=Decimal("0.00"),
            is_active=True,
        )

        Transaction.objects.create(
            owner=self.user,
            tx_type=Transaction.Type.INCOME,
            date=date(2026, 2, 1),
            amount=Decimal("100.00"),
            currency=self.currency,
            account=self.account,
            project=self.active_project,
            note="Incasso",
        )
        Transaction.objects.create(
            owner=self.user,
            tx_type=Transaction.Type.EXPENSE,
            date=date(2026, 2, 2),
            amount=Decimal("40.00"),
            currency=self.currency,
            account=self.account,
            project=self.active_project,
            note="Spesa",
        )
        Subscription.objects.create(
            owner=self.user,
            name="Servizio Cloud",
            account=self.account,
            currency=self.currency,
            amount=Decimal("15.00"),
            start_date=date(2026, 1, 1),
            next_due_date=date(2026, 3, 1),
            interval=1,
            interval_unit=Subscription.IntervalUnit.MONTH,
            status=Subscription.Status.ACTIVE,
            project=self.active_project,
        )
        Task.objects.create(
            owner=self.user,
            project=self.active_project,
            title="Task aperta",
            status=Task.Status.OPEN,
        )
        Task.objects.create(
            owner=self.user,
            project=self.active_project,
            title="Task chiusa",
            status=Task.Status.DONE,
        )
        PlannerItem.objects.create(
            owner=self.user,
            project=self.active_project,
            title="Planner planned",
            status=PlannerItem.Status.PLANNED,
        )
        PlannerItem.objects.create(
            owner=self.user,
            project=self.active_project,
            title="Planner done",
            status=PlannerItem.Status.DONE,
        )
        routine = Routine.objects.create(owner=self.user, name="Routine progetto", is_active=True)
        RoutineItem.objects.create(
            owner=self.user,
            routine=routine,
            project=self.active_project,
            title="Routine item",
            is_active=True,
        )

    def test_dashboard_active_scope_has_project_metrics(self):
        response = self.client.get("/projects/")
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.context["scope"], "active")
        rows = response.context["project_rows"]
        self.assertEqual(len(rows), 1)
        row = rows[0]
        self.assertEqual(row["project"].id, self.active_project.id)
        self.assertEqual(row["tx_total"], 2)
        self.assertEqual(row["income_total"], Decimal("100"))
        self.assertEqual(row["expense_total"], Decimal("40"))
        self.assertEqual(row["balance"], Decimal("60"))
        self.assertEqual(row["subscriptions_active"], 1)
        self.assertEqual(row["todo_open"], 1)
        self.assertEqual(row["planner_planned"], 1)
        self.assertEqual(row["routines_active"], 1)

    def test_dashboard_archived_scope_filters_rows(self):
        response = self.client.get("/projects/?scope=archived")
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.context["scope"], "archived")
        rows = response.context["project_rows"]
        self.assertEqual(len(rows), 1)
        self.assertEqual(rows[0]["project"].id, self.archived_project.id)


class SubProjectFlowTests(TestCase):
    def setUp(self):
        self.user = get_user_model().objects.create_user(username="subproj_user", password="test1234")
        self.client.login(username="subproj_user", password="test1234")
        self.project = Project.objects.create(owner=self.user, name="Project Parent")

    def test_add_subproject(self):
        response = self.client.post(
            f"/projects/subprojects/add?project={self.project.id}",
            {
                "project_id": str(self.project.id),
                "title": "Roadmap Fase 1",
                "description": "Sottofase con task dedicati",
                "status": SubProject.Status.IN_PROGRESS,
                "priority": SubProject.Priority.HIGH,
                "completion_percent": 35,
                "start_date": "2026-03-15",
                "due_date": "2026-04-15",
                "is_archived": "",
            },
        )
        self.assertEqual(response.status_code, 302)
        subproject = SubProject.objects.get(owner=self.user, project=self.project, title="Roadmap Fase 1")
        self.assertEqual(subproject.status, SubProject.Status.IN_PROGRESS)
        self.assertEqual(subproject.priority, SubProject.Priority.HIGH)

    def test_create_and_update_activity(self):
        subproject = SubProject.objects.create(owner=self.user, project=self.project, title="Delivery stream")
        create_response = self.client.post(
            f"/projects/subprojects/view?id={subproject.id}",
            {
                "action": "create_activity",
                "activity-title": "Analisi requisiti",
                "activity-description": "Raccolta e validazione",
                "activity-status": SubProjectActivity.Status.TODO,
                "activity-due_date": "2026-03-20",
                "activity-ordering": 1,
            },
        )
        self.assertEqual(create_response.status_code, 302)
        activity = SubProjectActivity.objects.get(owner=self.user, subproject=subproject, title="Analisi requisiti")
        self.assertEqual(activity.status, SubProjectActivity.Status.TODO)

        update_response = self.client.post(
            f"/projects/subprojects/view?id={subproject.id}",
            {
                "action": "update_activity_status",
                "activity_id": str(activity.id),
                "status": SubProjectActivity.Status.DONE,
            },
        )
        self.assertEqual(update_response.status_code, 302)
        activity.refresh_from_db()
        self.assertEqual(activity.status, SubProjectActivity.Status.DONE)


class ProjectDetailPlannerModalTests(TestCase):
    def setUp(self):
        self.user = get_user_model().objects.create_user(username="proj_modal_user", password="test1234")
        self.client.login(username="proj_modal_user", password="test1234")
        self.project = Project.objects.create(owner=self.user, name="Project Modal")

    def test_project_detail_adds_planner_item_via_post(self):
        response = self.client.post(
            f"/projects/view?id={self.project.id}",
            {
                "action": "add_project_planner_item",
                "title": "Reminder da modal",
                "due_date": "2026-03-28",
                "status": PlannerItem.Status.PLANNED,
                "amount": "",
                "category": "",
                "note": "Creato dalla page detail",
            },
        )
        self.assertEqual(response.status_code, 302)
        item = PlannerItem.objects.get(owner=self.user, project=self.project, title="Reminder da modal")
        self.assertEqual(item.status, PlannerItem.Status.PLANNED)

    def test_project_detail_can_confirm_planner_item(self):
        item = PlannerItem.objects.create(
            owner=self.user,
            project=self.project,
            title="Reminder da confermare",
            status=PlannerItem.Status.PLANNED,
        )
        response = self.client.post(
            f"/projects/view?id={self.project.id}",
            {
                "action": "update_project_planner_status",
                "planner_item_id": str(item.id),
                "status": PlannerItem.Status.DONE,
            },
        )
        self.assertEqual(response.status_code, 302)
        item.refresh_from_db()
        self.assertEqual(item.status, PlannerItem.Status.DONE)

    def test_project_detail_shows_planner_modify_link(self):
        item = PlannerItem.objects.create(
            owner=self.user,
            project=self.project,
            title="Reminder da modificare",
            status=PlannerItem.Status.PLANNED,
        )
        response = self.client.get(f"/projects/view?id={self.project.id}")
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, f"/planner/update?id={item.id}")

    def test_project_detail_can_toggle_subscription_status(self):
        currency, _ = Currency.objects.get_or_create(code="EUR", defaults={"name": "Euro"})
        account = Account.objects.create(
            owner=self.user,
            name="Conto Sub Test",
            kind=Account.Kind.BANK,
            currency=currency,
            opening_balance=Decimal("0.00"),
            is_active=True,
        )
        sub = Subscription.objects.create(
            owner=self.user,
            name="Sub rapida",
            account=account,
            currency=currency,
            amount=Decimal("19.99"),
            start_date=date(2026, 3, 1),
            next_due_date=date(2026, 4, 1),
            interval=1,
            interval_unit=Subscription.IntervalUnit.MONTH,
            status=Subscription.Status.ACTIVE,
            project=self.project,
        )
        response = self.client.post(
            f"/projects/view?id={self.project.id}",
            {
                "action": "update_project_subscription_status",
                "subscription_id": str(sub.id),
                "status": Subscription.Status.PAUSED,
            },
        )
        self.assertEqual(response.status_code, 302)
        sub.refresh_from_db()
        self.assertEqual(sub.status, Subscription.Status.PAUSED)

    def test_project_detail_can_toggle_subproject_status(self):
        subproject = SubProject.objects.create(
            owner=self.user,
            project=self.project,
            title="Subproject quick",
            status=SubProject.Status.IN_PROGRESS,
        )
        response = self.client.post(
            f"/projects/view?id={self.project.id}",
            {
                "action": "update_project_subproject_status",
                "subproject_id": str(subproject.id),
                "status": SubProject.Status.DONE,
            },
        )
        self.assertEqual(response.status_code, 302)
        subproject.refresh_from_db()
        self.assertEqual(subproject.status, SubProject.Status.DONE)
