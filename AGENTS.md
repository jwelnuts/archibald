# MIO - Quick Reference for AI Agents

**Stack:** Django 6 + PostgreSQL | HTMX + Stimulus + UIKit 3 | LESS

---

## 🏗️ Architecture (6 Layers - NO upward imports!)

```
L0 common → L1 core → L2 hubs (finance_hub, projects, contacts) → L3 ops (transactions, planner, etc.) → L4 archibald_mail
```

**Isolated:** vault  
**Memory Hub:** memory_stock (base) ← link_storage (specialization via FK)  
**Dev:** workbench

---

## 📝 Code Patterns

### Timeline (Weekly Calendar)
- Route: `/projects/timeline` — `projects/timeline_views.py`
- Rendered server-side with Jinja (no HTMX on the page itself)
- `timeline_views._build_week_data()` collects SubProjects, Tasks, and PlannerItems that overlap the selected week
- `_week_options()` generates ±4 weeks of navigation choices
- JS Stimulus controller (`timeline`) handles prev/next week navigation via `<select>` and button clicks
- Styles in `core/static/core/styles/timeline-weekly.less` — light theme with grid-based weekly table

### Models
```python
from common.models import OwnedModel, TimeStampedModel

class MyModel(OwnedModel, TimeStampedModel):
    name = models.CharField(max_length=120)
    class Meta:
        ordering = ["-created_at"]
        unique_together = ["owner", "name"]
```

### Views
```python
from django.contrib.auth.decorators import login_required

@login_required
def my_view(request):
    items = MyModel.objects.filter(owner=request.user)  # ALWAYS filter!
    return render(request, "app/template.html", {"items": items})
```

### Forms in Templates
```html
<form method="post" action="">
  {% csrf_token %}
  <input name="field" class="uk-input">
  <button class="btn primary" type="submit">Save</button>
</form>
```

### Stimulus Controller
```javascript
import { registerStimulusController } from "@core/stimulus.js";

class MyController extends window.StimulusModule.Controller {
  static targets = ["input"];

  connect() { /* init */ }

  action(event) {
    event.preventDefault();
    // logic
  }
}
registerStimulusController("name", MyController);
```

---

## 🎨 UI Kit

### Colors
- Primary: `#667eea` → `#764ba2` (gradient)
- Success: `#48bb78` | Error: `#f0506e` | Warning: `#ed8936` | Info: `#4299e1`
- Dark bg: `#1a1a2e`, `#16213e`, `#0f3460`

### Common Classes
- Card: `uk-card uk-card-default`
- Input: `uk-input` | Select: `uk-select` | Button Primary: `uk-button uk-button-primary`
- Grid: `uk-grid` `uk-child-width-1-2@s`

---

## 🔒 Security Checklist

- [ ] `@login_required` on ALL views
- [ ] `{% csrf_token %}` in ALL forms
- [ ] Filter by `owner=request.user`
- [ ] Set `item.owner = request.user` before save

---

## 🔄 Key Business Rules

**OwnedModel Pattern:** Every record has `owner = ForeignKey(User)`  
**Query Pattern:** `Model.objects.filter(owner=request.user)`  

**Email Flags:**
| Flag | Action |
|------|--------|
| `[MEMORY]` | Save to memory_stock |
| `[TODO]` | Create task |
| `[TX]` | Create transaction |
| `[REMINDER]` | Create agenda item |

---

## 📁 File Locations

- Templates: `app/templates/app/`
- Static JS: `app/static/app/` (Stimulus controllers)
- Static CSS: `app/static/app/styles.less`
- Tests: `app/tests.py`

---

## 🚀 Quick Commands

```bash
# Migrations
python manage.py makemigrations && python manage.py migrate

# Tests
python manage.py test

# Run dev
python manage.py runserver
```

---

## ⚡ Golden Rules

1. **NEVER** break the 6-layer architecture (no upward imports)
2. **ALWAYS** use HTMX + Stimulus for interactivity (no vanilla JS spaghetti)
3. **ALWAYS** inherit from `OwnedModel, TimeStampedModel`
4. **ALWAYS** protect views with `@login_required`
5. **ALWAYS** filter by `request.user`
6. Use UIKit components (don't reinvent)

---

*See full docs in `/docs/` (Obsidian vault)*
