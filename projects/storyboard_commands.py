import re
from datetime import date, timedelta
from django.utils import timezone
from todo.models import Task
from planner.models import PlannerItem
from projects.models import ProjectNote

class StoryboardCommandParser:
    def __init__(self, user, project=None):
        self.user = user
        self.project = project

    def parse_and_create(self, raw_text, attachment=None, fallback_project_id=None):
        raw_text = raw_text.strip()
        if not raw_text:
            return None

        # Prova a dedurre il progetto se non fornito
        active_project = self.project
        if not active_project and fallback_project_id:
            from projects.models import Project
            active_project = Project.objects.filter(owner=self.user, id=fallback_project_id).first()
        
        # Logica per estrarre progetto dal testo (es. @nome_progetto) potrebbe essere aggiunta qui
        
        if not active_project:
            # Se ancora non abbiamo un progetto, non possiamo creare task/planner/note legati ai progetti
            # Potremmo creare task globali, ma per ora atteniamoci ai progetti.
            return None

        self.project = active_project

        if raw_text.startswith("!") or raw_text.startswith("/task") or raw_text.startswith("/todo"):
            content = raw_text[1:].strip()
            if raw_text.startswith("/"):
                content = re.sub(r'^/(task|todo)', '', raw_text).strip()
            return self._handle_task(content)
        elif raw_text.startswith("?") or raw_text.startswith("/planner") or raw_text.startswith("/remind"):
            content = raw_text[1:].strip()
            if raw_text.startswith("/"):
                content = re.sub(r'^/(planner|remind)', '', raw_text).strip()
            return self._handle_planner(content)
        elif raw_text.startswith("/note"):
            content = re.sub(r'^/note', '', raw_text).strip()
            return self._handle_note(content, attachment)
        else:
            return self._handle_note(raw_text, attachment)

    def _handle_task(self, content):
        # Pattern: title [@ date] [# priority] [notes]
        # Priority: low, medium, high, critical
        priority_map = {
            "low": Task.Priority.LOW,
            "medium": Task.Priority.MEDIUM,
            "high": Task.Priority.HIGH,
            "critical": Task.Priority.CRITICAL,
            "1": Task.Priority.LOW,
            "2": Task.Priority.MEDIUM,
            "3": Task.Priority.HIGH,
            "4": Task.Priority.CRITICAL,
        }
        
        due_date, content = self._extract_date(content)
        priority, content = self._extract_priority(content, priority_map, Task.Priority.MEDIUM)
        
        # Split title and notes by newline or double space
        parts = re.split(r'\n|\s\s+', content, 1)
        title = parts[0].strip()
        note = parts[1].strip() if len(parts) > 1 else ""

        return Task.objects.create(
            owner=self.user,
            project=self.project,
            title=title,
            due_date=due_date,
            priority=priority,
            note=note,
            status=Task.Status.TODO
        )

    def _handle_planner(self, content):
        # Pattern: title [@ date] [notes]
        due_date, content = self._extract_date(content)
        
        parts = re.split(r'\n|\s\s+', content, 1)
        title = parts[0].strip()
        note = parts[1].strip() if len(parts) > 1 else ""

        return PlannerItem.objects.create(
            owner=self.user,
            project=self.project,
            title=title,
            due_date=due_date,
            note=note,
            status=PlannerItem.Status.PLANNED
        )

    def _handle_note(self, content, attachment=None):
        return ProjectNote.objects.create(
            owner=self.user,
            project=self.project,
            content=content,
            attachment=attachment
        )

    def _extract_date(self, text):
        match = re.search(r'@(\S+)', text)
        if not match:
            return None, text
        
        date_str = match.group(1).lower()
        due_date = None
        
        if date_str == "today" or date_str == "oggi":
            due_date = timezone.now().date()
        elif date_str == "tomorrow" or date_str == "domani":
            due_date = timezone.now().date() + timedelta(days=1)
        elif date_str == "monday" or date_str == "lunedi":
            due_date = self._next_weekday(0)
        # Add more date parsing if needed, or use a library
        else:
            try:
                # Expect YYYY-MM-DD
                due_date = date.fromisoformat(date_str)
            except ValueError:
                pass
        
        if due_date:
            text = text.replace(match.group(0), "").strip()
        
        return due_date, text

    def _extract_priority(self, text, priority_map, default):
        match = re.search(r'#(\S+)', text)
        if not match:
            return default, text
        
        p_str = match.group(1).lower()
        priority = priority_map.get(p_str, default)
        
        text = text.replace(match.group(0), "").strip()
        return priority, text

    def _next_weekday(self, weekday):
        days_ahead = weekday - timezone.now().weekday()
        if days_ahead <= 0:
            days_ahead += 7
        return timezone.now().date() + timedelta(days_ahead)
