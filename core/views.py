from datetime import date, timedelta
from decimal import Decimal
import json

from django.contrib import messages as django_messages
from django.contrib.auth import login, logout as auth_logout
from django.contrib.auth.decorators import login_required
from django.db.models import Count, Sum
from django.db.models.functions import Coalesce
from django.http import JsonResponse
from django.shortcuts import get_object_or_404, redirect, render
from django.views.decorators.http import require_http_methods

from agenda.models import AgendaItem, WorkLog
from .forms import AccountForm, SignUpForm
from .hero_actions import HERO_ACTIONS
from .models import UserHeroActionsConfig, UserNavConfig
from .navigation import DEFAULT_APP_OPTIONS, normalize_nav_config, parse_widgets_json
from planner.models import PlannerItem
from routines.models import RoutineItem
from subscriptions.models import Account
from subscriptions.models import SubscriptionOccurrence
from todo.models import Task
from transactions.models import Transaction


DEFAULT_DASHBOARD_WIDGETS = [
    {
        "id": "transactions",
        "title": "Transactions",
        "description": "Movimenti completi e filtri operativi.",
        "url": "/transactions/",
        "group": "money",
    },
    {
        "id": "finance_hub",
        "title": "Finance Hub",
        "description": "Preventivi, fatture e ordini lavoro.",
        "url": "/finance/",
        "group": "money",
    },
    {
        "id": "subscriptions",
        "title": "Subscriptions",
        "description": "Scadenze ricorrenti e rinnovi.",
        "url": "/subs/",
        "group": "money",
    },
    {
        "id": "accounts",
        "title": "Accounts",
        "description": "Conti e saldi principali.",
        "url": "/core/accounts/",
        "group": "money",
    },
    {
        "id": "projects",
        "title": "Projects",
        "description": "Progetti e stato operativo.",
        "url": "/projects/",
        "group": "ops",
    },
    {
        "id": "contacts",
        "title": "Contacts",
        "description": "Clienti, partner e rubriche.",
        "url": "/contacts/",
        "group": "ops",
    },
    {
        "id": "todo",
        "title": "Todo",
        "description": "Task giornalieri e backlog.",
        "url": "/todo/",
        "group": "planning",
    },
    {
        "id": "planner",
        "title": "Planner",
        "description": "Pianificazione settimanale.",
        "url": "/planner/",
        "group": "planning",
    },
    {
        "id": "agenda",
        "title": "Agenda",
        "description": "Agenda eventi e attività.",
        "url": "/agenda/",
        "group": "planning",
    },
    {
        "id": "routines",
        "title": "Routines",
        "description": "Routine e statistiche disciplina.",
        "url": "/routines/",
        "group": "planning",
    },
    {
        "id": "archibald",
        "title": "Archibald",
        "description": "Assistente AI contestuale.",
        "url": "/archibald/",
        "group": "ops",
    },
    {
        "id": "ai_lab",
        "title": "AI Lab",
        "description": "Esperimenti e appunti AI.",
        "url": "/ai-lab/",
        "group": "ops",
    },
    {
        "id": "vault",
        "title": "Vault",
        "description": "Credenziali e note cifrate.",
        "url": "/vault/",
        "group": "ops",
    },
    {
        "id": "workbench",
        "title": "Workbench",
        "description": "Tooling tecnico e generatori.",
        "url": "/workbench/",
        "group": "ops",
    },
]

DEFAULT_DASHBOARD_WIDGET_IDS = [item["id"] for item in DEFAULT_DASHBOARD_WIDGETS]
DASHBOARD_WIDGETS_BY_ID = {item["id"]: item for item in DEFAULT_DASHBOARD_WIDGETS}
DEFAULT_DASHBOARD_PREFERENCES = {
    "density": "comfortable",
    "accent": "blue",
    "sections": ["snapshot", "widgets", "calendar", "archibald", "quick_actions"],
}
ALLOWED_DASHBOARD_DENSITIES = {"comfortable", "compact"}
ALLOWED_DASHBOARD_ACCENTS = {"blue", "green", "amber", "rose"}
ALLOWED_DASHBOARD_SECTIONS = {"snapshot", "widgets", "calendar", "archibald", "quick_actions"}


def _normalize_dashboard_widgets(raw_config):
    if not isinstance(raw_config, dict):
        raw_config = {}
    raw_order = raw_config.get("order", [])
    raw_hidden = raw_config.get("hidden", [])

    order = []
    for widget_id in raw_order:
        if widget_id in DASHBOARD_WIDGETS_BY_ID and widget_id not in order:
            order.append(widget_id)
    for widget_id in DEFAULT_DASHBOARD_WIDGET_IDS:
        if widget_id not in order:
            order.append(widget_id)

    hidden = []
    for widget_id in raw_hidden:
        if widget_id in DASHBOARD_WIDGETS_BY_ID and widget_id not in hidden:
            hidden.append(widget_id)

    return {"order": order, "hidden": hidden}


def _dashboard_widgets_for_user(user):
    nav_config, _ = UserNavConfig.objects.get_or_create(user=user)
    raw = nav_config.config or {}
    normalized = _normalize_dashboard_widgets(raw.get("dashboard_widgets", {}))
    hidden_set = set(normalized["hidden"])
    widgets = []
    for widget_id in normalized["order"]:
        base = DASHBOARD_WIDGETS_BY_ID[widget_id]
        widgets.append(
            {
                "id": base["id"],
                "title": base["title"],
                "description": base["description"],
                "url": base["url"],
                "group": base["group"],
                "hidden": widget_id in hidden_set,
            }
        )
    return widgets


def _normalize_dashboard_preferences(raw_config):
    if not isinstance(raw_config, dict):
        raw_config = {}

    density = (raw_config.get("density") or DEFAULT_DASHBOARD_PREFERENCES["density"]).strip().lower()
    if density not in ALLOWED_DASHBOARD_DENSITIES:
        density = DEFAULT_DASHBOARD_PREFERENCES["density"]

    accent = (raw_config.get("accent") or DEFAULT_DASHBOARD_PREFERENCES["accent"]).strip().lower()
    if accent not in ALLOWED_DASHBOARD_ACCENTS:
        accent = DEFAULT_DASHBOARD_PREFERENCES["accent"]

    sections_raw = raw_config.get("sections", [])
    sections = []
    if isinstance(sections_raw, list):
        for row in sections_raw:
            key = (str(row) or "").strip().lower()
            if key in ALLOWED_DASHBOARD_SECTIONS and key not in sections:
                sections.append(key)

    if not sections:
        sections = list(DEFAULT_DASHBOARD_PREFERENCES["sections"])

    return {
        "density": density,
        "accent": accent,
        "sections": sections,
    }


def _dashboard_preferences_for_user(user):
    nav_config, _ = UserNavConfig.objects.get_or_create(user=user)
    raw = nav_config.config or {}
    return _normalize_dashboard_preferences(raw.get("dashboard_preferences", {}))


def _dashboard_snapshot_context(user):
    today = date.today()
    week_end = today + timedelta(days=7)
    month_start = today.replace(day=1)
    month_end = (month_start + timedelta(days=32)).replace(day=1) - timedelta(days=1)

    open_tasks_qs = Task.objects.filter(owner=user).exclude(status=Task.Status.DONE)
    planned_planner_qs = PlannerItem.objects.filter(owner=user, status=PlannerItem.Status.PLANNED)
    due_subs_qs = SubscriptionOccurrence.objects.filter(
        owner=user,
        due_date__range=(today, week_end),
        state=SubscriptionOccurrence.State.PLANNED,
    )

    month_tx_qs = Transaction.objects.filter(owner=user, date__range=(month_start, month_end))
    month_income = month_tx_qs.filter(tx_type=Transaction.Type.INCOME).aggregate(
        total=Coalesce(Sum("amount"), Decimal("0.00"))
    )["total"]
    month_expense = month_tx_qs.filter(tx_type=Transaction.Type.EXPENSE).aggregate(
        total=Coalesce(Sum("amount"), Decimal("0.00"))
    )["total"]

    focus_rows = []

    for task in open_tasks_qs.filter(due_date__isnull=False).order_by("due_date", "title")[:4]:
        focus_rows.append(
            {
                "kind": "Task",
                "title": task.title,
                "due_date": task.due_date,
                "url": "/todo/",
            }
        )

    for item in planned_planner_qs.filter(due_date__isnull=False).order_by("due_date", "title")[:4]:
        focus_rows.append(
            {
                "kind": "Planner",
                "title": item.title,
                "due_date": item.due_date,
                "url": "/planner/",
            }
        )

    for occ in due_subs_qs.select_related("subscription").order_by("due_date", "subscription__name")[:4]:
        focus_rows.append(
            {
                "kind": "Abbonamento",
                "title": occ.subscription.name,
                "due_date": occ.due_date,
                "url": "/subs/",
            }
        )

    focus_rows.sort(key=lambda row: (row["due_date"] is None, row["due_date"] or today, row["kind"], row["title"]))
    focus_rows = focus_rows[:8]

    return {
        "snapshot": {
            "open_tasks": open_tasks_qs.count(),
            "tasks_today": open_tasks_qs.filter(due_date=today).count(),
            "overdue_tasks": open_tasks_qs.filter(due_date__lt=today).count(),
            "planner_planned": planned_planner_qs.count(),
            "planner_today": planned_planner_qs.filter(due_date=today).count(),
            "due_subscriptions_week": due_subs_qs.count(),
            "month_income": month_income,
            "month_expense": month_expense,
            "month_balance": month_income - month_expense,
            "month_transactions": month_tx_qs.count(),
        },
        "focus_rows": focus_rows,
        "generated_on": today,
    }


def _calendar_events_for_range(user, start: date, end: date):
    events = {}

    def add_event(day, kind, label, count=None):
        key = day.isoformat()
        payload = {"kind": kind, "label": label}
        if count is not None:
            payload["count"] = count
        events.setdefault(key, []).append(payload)

    tasks = (
        Task.objects.filter(owner=user, due_date__range=(start, end))
        .exclude(status=Task.Status.DONE)
        .values("due_date")
        .annotate(count=Count("id"))
    )
    for row in tasks:
        add_event(row["due_date"], "task", "Task", row["count"])

    agenda_activities = (
        AgendaItem.objects.filter(
            owner=user,
            due_date__range=(start, end),
            item_type=AgendaItem.ItemType.ACTIVITY,
            status=AgendaItem.Status.PLANNED,
        )
        .values("due_date")
        .annotate(count=Count("id"))
    )
    for row in agenda_activities:
        add_event(row["due_date"], "agenda_activity", "Agenda attivita", row["count"])

    agenda_reminders = (
        AgendaItem.objects.filter(
            owner=user,
            due_date__range=(start, end),
            item_type=AgendaItem.ItemType.REMINDER,
            status=AgendaItem.Status.PLANNED,
        )
        .values("due_date")
        .annotate(count=Count("id"))
    )
    for row in agenda_reminders:
        add_event(row["due_date"], "agenda_reminder", "Agenda reminder", row["count"])

    planner = (
        PlannerItem.objects.filter(owner=user, due_date__range=(start, end), status=PlannerItem.Status.PLANNED)
        .values("due_date")
        .annotate(count=Count("id"))
    )
    for row in planner:
        add_event(row["due_date"], "planner", "Planner", row["count"])

    subs = (
        SubscriptionOccurrence.objects.filter(owner=user, due_date__range=(start, end))
        .values("due_date")
        .annotate(count=Count("id"))
    )
    for row in subs:
        add_event(row["due_date"], "subscription", "Abbonamenti", row["count"])

    tx = (
        Transaction.objects.filter(owner=user, date__range=(start, end))
        .values("date")
        .annotate(count=Count("id"))
    )
    for row in tx:
        add_event(row["date"], "transaction", "Transazioni", row["count"])

    work_logs = (
        WorkLog.objects.filter(owner=user, work_date__range=(start, end))
        .values("work_date")
        .annotate(total_hours=Sum("hours"))
    )
    for row in work_logs:
        if row["total_hours"]:
            add_event(row["work_date"], "worklog", "Ore lavoro", 1)

    routine_counts = (
        RoutineItem.objects.filter(owner=user, is_active=True)
        .values("weekday")
        .annotate(count=Count("id"))
    )
    routine_map = {row["weekday"]: row["count"] for row in routine_counts}
    if routine_map:
        cursor = start
        while cursor <= end:
            count = routine_map.get(cursor.weekday())
            if count:
                add_event(cursor, "routine", "Routine", count)
            cursor += timedelta(days=1)

    return events


@login_required
def dashboard(request):
    context = {
        "dashboard_widgets": _dashboard_widgets_for_user(request.user),
        "dashboard_preferences": _dashboard_preferences_for_user(request.user),
    }
    return render(request, "core/dashboard.html", context)


@login_required
@require_http_methods(["POST"])
def dashboard_widgets(request):
    try:
        payload = json.loads((request.body or b"{}").decode("utf-8"))
    except (json.JSONDecodeError, UnicodeDecodeError):
        return JsonResponse({"ok": False, "error": "invalid_json"}, status=400)

    order_raw = payload.get("order", [])
    hidden_raw = payload.get("hidden", [])
    if not isinstance(order_raw, list) or not isinstance(hidden_raw, list):
        return JsonResponse({"ok": False, "error": "invalid_payload"}, status=400)

    normalized = _normalize_dashboard_widgets({"order": order_raw, "hidden": hidden_raw})
    nav_config, _ = UserNavConfig.objects.get_or_create(user=request.user)
    config = nav_config.config if isinstance(nav_config.config, dict) else {}
    config["dashboard_widgets"] = normalized
    nav_config.config = config
    nav_config.save(update_fields=["config"])
    return JsonResponse({"ok": True, "dashboard_widgets": normalized})


@login_required
@require_http_methods(["POST"])
def dashboard_preferences(request):
    try:
        payload = json.loads((request.body or b"{}").decode("utf-8"))
    except (json.JSONDecodeError, UnicodeDecodeError):
        return JsonResponse({"ok": False, "error": "invalid_json"}, status=400)

    normalized = _normalize_dashboard_preferences(payload)

    nav_config, _ = UserNavConfig.objects.get_or_create(user=request.user)
    config = nav_config.config if isinstance(nav_config.config, dict) else {}
    config["dashboard_preferences"] = normalized
    nav_config.config = config
    nav_config.save(update_fields=["config"])

    return JsonResponse({"ok": True, "dashboard_preferences": normalized})


@login_required
@require_http_methods(["GET"])
def dashboard_snapshot(request):
    context = _dashboard_snapshot_context(request.user)
    return render(request, "core/partials/dashboard_snapshot.html", context)


@login_required
def calendar_events(request):
    start_raw = request.GET.get("start")
    end_raw = request.GET.get("end")
    today = date.today()
    try:
        start = date.fromisoformat(start_raw) if start_raw else today.replace(day=1)
    except ValueError:
        start = today.replace(day=1)
    try:
        end = date.fromisoformat(end_raw) if end_raw else (start + timedelta(days=31))
    except ValueError:
        end = start + timedelta(days=31)

    events = _calendar_events_for_range(request.user, start, end)
    payload = [{"date": day, "items": items} for day, items in events.items()]
    return JsonResponse({"events": payload})


def signup(request):
    if request.method == "POST":
        form = SignUpForm(request.POST)
        if form.is_valid():
            user = form.save()
            login(request, user)
            return redirect("/")
    else:
        form = SignUpForm()
    return render(request, "registration/signup.html", {"form": form})


@require_http_methods(["GET", "POST"])
def logout_view(request):
    auth_logout(request)
    return redirect("/")


@login_required
def profile(request):
    from ai_lab.models import ArchibaldInstructionState, ArchibaldPersonaConfig
    from archibald.prompting import build_archibald_system_for_user

    persona, _ = ArchibaldPersonaConfig.objects.get_or_create(owner=request.user)

    if request.method == "POST":
        action = (request.POST.get("action") or "").strip()
        custom_text = (request.POST.get("archibald_custom_instructions") or "").strip()

        if action == "save_archibald_instructions":
            persona.custom_instructions = custom_text
            persona.save()
            django_messages.success(request, "Istruzioni Archibald salvate.")
            return redirect("/profile/")

        if action == "save_archibald_state":
            state_name = (request.POST.get("state_name") or "").strip()
            if not state_name:
                django_messages.error(request, "Inserisci un nome stato prima di salvare.")
            else:
                persona.custom_instructions = custom_text
                persona.save()
                state, created = ArchibaldInstructionState.objects.update_or_create(
                    owner=request.user,
                    name=state_name,
                    defaults={"instructions_text": custom_text},
                )
                label = "creato" if created else "aggiornato"
                django_messages.success(request, f"Stato '{state.name}' {label}.")
            return redirect("/profile/")

        if action == "apply_archibald_state":
            state_id = request.POST.get("state_id")
            state = ArchibaldInstructionState.objects.filter(owner=request.user, id=state_id).first()
            if not state:
                django_messages.error(request, "Stato non trovato.")
            else:
                persona.custom_instructions = state.instructions_text
                persona.save()
                django_messages.success(request, f"Stato '{state.name}' applicato alle istruzioni attive.")
            return redirect("/profile/")

        if action == "delete_archibald_state":
            state_id = request.POST.get("state_id")
            state = ArchibaldInstructionState.objects.filter(owner=request.user, id=state_id).first()
            if not state:
                django_messages.error(request, "Stato non trovato.")
            else:
                label = state.name
                state.delete()
                django_messages.success(request, f"Stato '{label}' eliminato.")
            return redirect("/profile/")

        if action == "save_bias_settings":
            persona.bias_catastrophizing = request.POST.get("bias_catastrophizing") == "on"
            persona.bias_all_or_nothing = request.POST.get("bias_all_or_nothing") == "on"
            persona.bias_overgeneralization = request.POST.get("bias_overgeneralization") == "on"
            persona.bias_mind_reading = request.POST.get("bias_mind_reading") == "on"
            persona.bias_negative_filtering = request.POST.get("bias_negative_filtering") == "on"
            persona.bias_confirmation_bias = request.POST.get("bias_confirmation_bias") == "on"
            persona.save(
                update_fields=[
                    "bias_catastrophizing",
                    "bias_all_or_nothing",
                    "bias_overgeneralization",
                    "bias_mind_reading",
                    "bias_negative_filtering",
                    "bias_confirmation_bias",
                ]
            )
            django_messages.success(request, "Impostazioni bias cognitivi salvate.")
            return redirect("/profile/#bias-cognitivi")

    states = ArchibaldInstructionState.objects.filter(owner=request.user).order_by("-updated_at", "name")
    context = {
        "archibald_custom_instructions": persona.custom_instructions or "",
        "archibald_instruction_states": states[:24],
        "archibald_system_preview": build_archibald_system_for_user(request.user),
        "archibald_persona": persona,
    }
    return render(request, "core/profile.html", context)


@login_required
def nav_settings(request):
    config_obj, _ = UserNavConfig.objects.get_or_create(user=request.user)
    raw = config_obj.config or {}
    normalized = normalize_nav_config(raw)
    apps_by_key = {item["key"]: item for item in DEFAULT_APP_OPTIONS}

    if request.method == "POST":
        errors = []
        ordered_rows = []
        for index, item in enumerate(DEFAULT_APP_OPTIONS, start=1):
            key = item["key"]
            visible = request.POST.get(f"app_visible_{key}") == "on"
            order_raw = (request.POST.get(f"app_order_{key}") or "").strip()
            try:
                order_value = int(order_raw) if order_raw else index
            except ValueError:
                order_value = index
            ordered_rows.append((order_value, index, key, visible))
        ordered_rows.sort(key=lambda row: (row[0], row[1]))

        app_order = [row[2] for row in ordered_rows]
        hidden_apps = [row[2] for row in ordered_rows if not row[3]]

        custom_links = []
        for idx in range(1, 7):
            label = (request.POST.get(f"custom_label_{idx}") or "").strip()
            url = (request.POST.get(f"custom_url_{idx}") or "").strip()
            if not label and not url:
                continue
            if not label or not url:
                errors.append(f"Link personalizzato #{idx}: inserisci sia etichetta che URL.")
                continue
            if not (url.startswith("/") or url.startswith("http://") or url.startswith("https://")):
                errors.append(f"Link personalizzato #{idx}: URL non valido.")
                continue
            custom_links.append(
                {
                    "label": label[:40],
                    "url": url[:300],
                    "external": url.startswith("http://") or url.startswith("https://"),
                }
            )

        widgets_json_raw = request.POST.get("widgets_json") or ""
        try:
            widgets = parse_widgets_json(widgets_json_raw)
        except json.JSONDecodeError:
            widgets = []
            errors.append("JSON widgets non valido.")
        except ValueError as exc:
            widgets = []
            errors.append(str(exc))

        if errors:
            for msg in errors:
                django_messages.error(request, msg)
            normalized = normalize_nav_config(
                {
                    "_configured": True,
                    "app_order": app_order,
                    "hidden_apps": hidden_apps,
                    "custom_links": custom_links,
                    "widgets": widgets,
                }
            )
        else:
            config_obj.config = {
                "_configured": True,
                "app_order": app_order,
                "hidden_apps": hidden_apps,
                "custom_links": custom_links,
                "widgets": widgets,
            }
            config_obj.save(update_fields=["config"])
            django_messages.success(request, "Navigazione personalizzata salvata.")
            return redirect("/profile/nav/")

    app_rows = []
    for position, key in enumerate(normalized["app_order"], start=1):
        item = apps_by_key.get(key)
        if not item:
            continue
        app_rows.append(
            {
                "key": key,
                "label": item["label"],
                "icon": item.get("icon", "thumbnails"),
                "url": item["url"],
                "visible": key not in normalized["hidden_apps"],
                "order": position,
            }
        )

    custom_link_rows = []
    saved_links = normalized["custom_links"]
    for idx in range(6):
        if idx < len(saved_links):
            row = saved_links[idx]
            custom_link_rows.append({"index": idx + 1, "label": row.get("label", ""), "url": row.get("url", "")})
        else:
            custom_link_rows.append({"index": idx + 1, "label": "", "url": ""})

    context = {
        "app_rows": app_rows,
        "custom_link_rows": custom_link_rows,
        "widgets_json": json.dumps(normalized["widgets"], ensure_ascii=True, indent=2),
    }
    return render(request, "core/nav_settings.html", context)


@login_required
def hero_actions(request):
    config_obj, _ = UserHeroActionsConfig.objects.get_or_create(user=request.user)
    if request.method == "POST":
        new_config = {}
        for module, actions in HERO_ACTIONS.items():
            enabled = []
            for action in actions:
                key = f"{module}:{action['key']}"
                if request.POST.get(key) == "on":
                    enabled.append(action["key"])
            new_config[module] = enabled
        new_config["_configured"] = True
        config_obj.config = new_config
        config_obj.save(update_fields=["config"])
        return redirect("/profile/hero-actions/")

    selected = config_obj.config or {}
    if selected and not selected.get("_configured"):
        # Backfill legacy config with defaults for missing modules.
        for module, actions in HERO_ACTIONS.items():
            if module not in selected:
                selected[module] = [a["key"] for a in actions if a.get("default")]
        selected["_configured"] = True
        config_obj.config = selected
        config_obj.save(update_fields=["config"])
    context = {
        "actions": HERO_ACTIONS,
        "selected": selected,
    }
    return render(request, "core/hero_actions.html", context)


@login_required
def accounts(request):
    accounts_list = Account.objects.filter(owner=request.user).order_by("name")
    return render(request, "core/accounts.html", {"accounts": accounts_list})


@login_required
def add_account(request):
    if request.method == "POST":
        form = AccountForm(request.POST)
        if form.is_valid():
            account = form.save(commit=False)
            account.owner = request.user
            account.save()
            return redirect("/core/accounts/")
    else:
        form = AccountForm()
    return render(request, "core/add_account.html", {"form": form})


@login_required
def update_account(request):
    account_id = request.GET.get("id")
    account = None
    if account_id:
        account = get_object_or_404(Account, id=account_id, owner=request.user)
        if request.method == "POST":
            form = AccountForm(request.POST, instance=account)
            if form.is_valid():
                form.save()
                return redirect("/core/accounts/")
        else:
            form = AccountForm(instance=account)
        return render(request, "core/update_account.html", {"form": form, "account": account})
    accounts_list = Account.objects.filter(owner=request.user).order_by("name")[:20]
    return render(request, "core/update_account.html", {"accounts": accounts_list})


@login_required
def remove_account(request):
    account_id = request.GET.get("id")
    account = None
    if account_id:
        account = get_object_or_404(Account, id=account_id, owner=request.user)
        if request.method == "POST":
            account.delete()
            return redirect("/core/accounts/")
    accounts_list = Account.objects.filter(owner=request.user).order_by("name")[:20]
    return render(request, "core/remove_account.html", {"account": account, "accounts": accounts_list})
