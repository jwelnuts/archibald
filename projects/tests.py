from django.test import TestCase
from django.contrib.auth import get_user_model

from planner.models import PlannerItem
from todo.models import Task

from .models import Project, ProjectNote


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
