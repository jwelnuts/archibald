from datetime import date, timedelta
from decimal import Decimal
import hashlib
import json
import logging
import secrets
from types import SimpleNamespace
from urllib.parse import quote, urljoin

from django.conf import settings
from django.contrib import messages as django_messages
from django.contrib.auth import authenticate, get_user_model, login, logout as auth_logout
from django.contrib.auth.decorators import login_required
from django.contrib.auth.views import LoginView, PasswordChangeView
from django.db.models import Count, Sum
from django.db.models.functions import Coalesce
from django.http import JsonResponse
from django.shortcuts import get_object_or_404, redirect, render
from django.utils import timezone
from django.views.decorators.csrf import csrf_exempt
from django.views.decorators.http import require_http_methods

from agenda.models import AgendaItem, WorkLog
from .dav import (
    DavProvisioningError,
    caldav_base_url,
    create_external_dav_account,
    create_managed_calendar,
    ensure_user_dav_access,
    grant_external_access_to_calendar,
    rotate_external_dav_password,
    set_calendar_grant_active,
    set_external_dav_account_active,
    set_managed_calendar_active,
)
from .forms import AccountForm, SignUpForm
from .hero_actions import HERO_ACTIONS
from .models import (
    DavAccount,
    DavCalendarGrant,
    DavExternalAccount,
    DavManagedCalendar,
    MobileApiSession,
    UserHeroActionsConfig,
    UserNavConfig,
)
from .navigation import DEFAULT_APP_OPTIONS, normalize_nav_config, parse_widgets_json
from planner.models import PlannerItem
from projects.models import Project, SubProject
from routines.models import Routine, RoutineCategory, RoutineCheck, RoutineItem
from routines.services import (
    RoutineCrudError,
    create_routine_item,
    delete_routine_item,
    get_category_for_owner,
    get_routine_for_owner,
    parse_weekday,
    update_routine_item,
)
from subscriptions.models import Account
from subscriptions.models import SubscriptionOccurrence
from todo.models import Task
from transactions.models import Transaction

logger = logging.getLogger(__name__)


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
        "id": "archibald_mail",
        "title": "Archibald Mail",
        "description": "Inbox AI e notifiche email.",
        "url": "/archibald-mail/",
        "group": "ops",
    },
    {
        "id": "memory_stock",
        "title": "Memory Stock",
        "description": "Catture rapide da email e link interessanti.",
        "url": "/memory-stock/",
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


class AccountPasswordChangeView(PasswordChangeView):
    def form_valid(self, form):
        response = super().form_valid(form)
        if settings.CALDAV_ENABLED:
            raw_password = (form.cleaned_data.get("new_password1") or "").strip()
            if raw_password:
                try:
                    ensure_user_dav_access(self.request.user, raw_password=raw_password)
                except DavProvisioningError as exc:
                    django_messages.warning(
                        self.request,
                        f"Password account aggiornata, ma sync DAV non completata: {exc}",
                    )
                else:
                    django_messages.success(
                        self.request,
                        "Credenziali DAV allineate alla nuova password account.",
                    )
        return response


class AccountLoginView(LoginView):
    def form_valid(self, form):
        if settings.CALDAV_ENABLED:
            raw_password = (form.cleaned_data.get("password") or "").strip()
            if raw_password:
                try:
                    ensure_user_dav_access(form.get_user(), raw_password=raw_password)
                except DavProvisioningError as exc:
                    django_messages.warning(
                        self.request,
                        f"Login completato, ma sync DAV non completata: {exc}",
                    )
                else:
                    self.request._dav_synced = True
        response = super().form_valid(form)
        return response


def signup(request):
    if request.method == "POST":
        form = SignUpForm(request.POST)
        if form.is_valid():
            user = form.save()
            login(request, user)
            if settings.CALDAV_ENABLED:
                try:
                    raw_password = (form.cleaned_data.get("password1") or "").strip()
                    account, _ = ensure_user_dav_access(user, raw_password=raw_password)
                except DavProvisioningError as exc:
                    django_messages.warning(
                        request,
                        f"Account creato, ma provisioning DAV non completato: {exc}",
                    )
                else:
                    django_messages.success(
                        request,
                        f"Accesso DAV attivo per {account.dav_username}: usa la stessa password del tuo account.",
                    )
            return redirect("/profile/#dav-access")
    else:
        form = SignUpForm()
    return render(request, "registration/signup.html", {"form": form})


@require_http_methods(["GET", "POST"])
def logout_view(request):
    auth_logout(request)
    return redirect("/")


def _dav_collection_url(base_url: str, principal: str, collection_slug: str = "") -> str:
    base = (base_url or "").strip()
    if not base:
        return ""
    if not base.endswith("/"):
        base = f"{base}/"
    principal_value = (principal or "").strip()
    if not principal_value:
        return base
    principal_token = quote(principal_value, safe="@._+-")
    if not collection_slug:
        return urljoin(base, f"{principal_token}/")
    collection_token = quote((collection_slug or "").strip(), safe="@._+-")
    return urljoin(base, f"{principal_token}/{collection_token}/")


def _split_collection_path(raw_path: str) -> tuple[str, str]:
    value = (raw_path or "").strip().strip("/")
    if not value or "/" not in value:
        return "", ""
    principal, slug = value.split("/", 1)
    return principal.strip(), slug.strip()


def _build_dav_context(request, *, consume_onboarding: bool) -> dict:
    base_url = caldav_base_url()
    dav_account = DavAccount.objects.filter(user=request.user).first()
    managed_calendars_qs = DavManagedCalendar.objects.filter(owner=request.user).order_by(
        "-is_active", "principal", "calendar_slug"
    )
    external_accounts_qs = (
        DavExternalAccount.objects.filter(owner=request.user)
        .prefetch_related("grants__calendar")
        .order_by("-is_active", "dav_username")
    )
    grants_qs = (
        DavCalendarGrant.objects.filter(owner=request.user)
        .select_related("external_account", "calendar")
        .order_by("-is_active", "external_account__dav_username", "calendar__principal", "calendar__calendar_slug")
    )
    default_team_principal, default_team_slug = _split_collection_path(settings.CALDAV_DEFAULT_TEAM_COLLECTION)
    managed_rows = [
        {
            "calendar": calendar,
            "url": _dav_collection_url(base_url, calendar.principal, calendar.calendar_slug),
        }
        for calendar in managed_calendars_qs[:200]
    ]
    grants_rows = [
        {
            "grant": grant,
            "url": _dav_collection_url(base_url, grant.calendar.principal, grant.calendar.calendar_slug),
        }
        for grant in grants_qs[:400]
    ]
    onboarding_payload = (
        request.session.pop("dav_external_onboarding", None)
        if consume_onboarding
        else request.session.get("dav_external_onboarding")
    )
    return {
        "caldav_enabled": settings.CALDAV_ENABLED,
        "caldav_base_url": base_url,
        "dav_account": dav_account,
        "dav_default_team_collection": settings.CALDAV_DEFAULT_TEAM_COLLECTION,
        "dav_access_pattern_url": f"{base_url}{{username}}/{{collezione}}/" if base_url else "",
        "dav_account_root_url": _dav_collection_url(base_url, getattr(dav_account, "dav_username", "")),
        "dav_default_team_collection_url": _dav_collection_url(base_url, default_team_principal, default_team_slug),
        "dav_external_onboarding_username": (onboarding_payload or {}).get("username", ""),
        "dav_external_onboarding_password": (onboarding_payload or {}).get("password", ""),
        "dav_external_accounts": external_accounts_qs[:200],
        "dav_managed_calendars": managed_calendars_qs[:200],
        "dav_managed_calendar_rows": managed_rows,
        "dav_active_external_accounts": external_accounts_qs.filter(is_active=True)[:200],
        "dav_active_managed_calendars": managed_calendars_qs.filter(is_active=True)[:200],
        "dav_grants": grants_qs[:400],
        "dav_grant_rows": grants_rows,
    }


def _handle_dav_actions(request, action: str, *, redirect_base: str):
    if action.startswith("dav_") and not settings.CALDAV_ENABLED:
        django_messages.error(request, "CalDAV non abilitato in questa istanza.")
        return redirect(f"{redirect_base}#dav-access")

    if action == "rotate_dav_password":
        django_messages.info(
            request,
            "Le credenziali DAV usano la stessa password account. Aggiorna la password da questa pagina.",
        )
        return redirect("/accounts/password_change/")

    if action == "dav_create_external_user":
        try:
            account, issued_password = create_external_dav_account(
                owner=request.user,
                label=request.POST.get("dav_external_label") or "",
                username_hint=request.POST.get("dav_external_username_hint") or "",
                raw_password=request.POST.get("dav_external_password") or "",
            )
        except DavProvisioningError as exc:
            django_messages.error(request, f"Creazione utente DAV esterno fallita: {exc}")
        else:
            request.session["dav_external_onboarding"] = {
                "username": account.dav_username,
                "password": issued_password,
            }
            django_messages.success(
                request,
                f"Utente DAV esterno creato: {account.dav_username}. Password disponibile in questa pagina.",
            )
        return redirect(f"{redirect_base}#dav-external-access")

    if action == "dav_rotate_external_password":
        external_id = request.POST.get("external_id")
        external = DavExternalAccount.objects.filter(owner=request.user, id=external_id).first()
        if not external:
            django_messages.error(request, "Utente DAV esterno non trovato.")
            return redirect(f"{redirect_base}#dav-external-access")
        try:
            issued_password = rotate_external_dav_password(
                owner=request.user,
                external_account=external,
                raw_password=request.POST.get("dav_external_password") or "",
            )
        except DavProvisioningError as exc:
            django_messages.error(request, f"Rotazione password DAV esterna fallita: {exc}")
        else:
            request.session["dav_external_onboarding"] = {
                "username": external.dav_username,
                "password": issued_password,
            }
            django_messages.success(
                request,
                f"Password aggiornata per {external.dav_username}.",
            )
        return redirect(f"{redirect_base}#dav-external-access")

    if action in {"dav_activate_external_user", "dav_deactivate_external_user"}:
        external_id = request.POST.get("external_id")
        external = DavExternalAccount.objects.filter(owner=request.user, id=external_id).first()
        if not external:
            django_messages.error(request, "Utente DAV esterno non trovato.")
            return redirect(f"{redirect_base}#dav-external-access")
        try:
            set_external_dav_account_active(
                owner=request.user,
                external_account=external,
                is_active=(action == "dav_activate_external_user"),
            )
        except DavProvisioningError as exc:
            django_messages.error(request, f"Aggiornamento stato utente DAV esterno fallito: {exc}")
        else:
            label = "riattivato" if action == "dav_activate_external_user" else "disattivato"
            django_messages.success(request, f"Utente DAV esterno {label}: {external.dav_username}.")
        return redirect(f"{redirect_base}#dav-external-access")

    if action == "dav_create_calendar":
        try:
            calendar = create_managed_calendar(
                owner=request.user,
                principal=request.POST.get("dav_calendar_principal") or "team",
                calendar_slug=request.POST.get("dav_calendar_slug") or "",
                display_name=request.POST.get("dav_calendar_display_name") or "",
            )
        except DavProvisioningError as exc:
            django_messages.error(request, f"Creazione calendario DAV fallita: {exc}")
        else:
            django_messages.success(
                request,
                f"Calendario DAV pronto: {calendar.collection_path}",
            )
        return redirect(f"{redirect_base}#dav-external-access")

    if action in {"dav_activate_calendar", "dav_deactivate_calendar"}:
        calendar_id = request.POST.get("calendar_id")
        calendar = DavManagedCalendar.objects.filter(owner=request.user, id=calendar_id).first()
        if not calendar:
            django_messages.error(request, "Calendario DAV non trovato.")
            return redirect(f"{redirect_base}#dav-external-access")
        try:
            set_managed_calendar_active(
                owner=request.user,
                calendar=calendar,
                is_active=(action == "dav_activate_calendar"),
            )
        except DavProvisioningError as exc:
            django_messages.error(request, f"Aggiornamento stato calendario DAV fallito: {exc}")
        else:
            label = "riattivato" if action == "dav_activate_calendar" else "disattivato"
            django_messages.success(request, f"Calendario DAV {label}: {calendar.collection_path}.")
        return redirect(f"{redirect_base}#dav-external-access")

    if action == "dav_grant_calendar_access":
        external_id = request.POST.get("external_id")
        calendar_id = request.POST.get("calendar_id")
        access_level = (request.POST.get("access_level") or "").strip().lower()
        external = DavExternalAccount.objects.filter(owner=request.user, id=external_id, is_active=True).first()
        calendar = DavManagedCalendar.objects.filter(owner=request.user, id=calendar_id, is_active=True).first()
        if not external or not calendar:
            django_messages.error(request, "Seleziona utente esterno e calendario validi.")
            return redirect(f"{redirect_base}#dav-external-access")
        try:
            grant_external_access_to_calendar(
                owner=request.user,
                external_account=external,
                calendar=calendar,
                access_level=access_level,
            )
        except DavProvisioningError as exc:
            django_messages.error(request, f"Assegnazione permesso DAV fallita: {exc}")
        else:
            django_messages.success(
                request,
                f"Permesso aggiornato: {external.dav_username} -> {calendar.collection_path}.",
            )
        return redirect(f"{redirect_base}#dav-external-access")

    if action in {"dav_activate_grant", "dav_revoke_grant"}:
        grant_id = request.POST.get("grant_id")
        grant = DavCalendarGrant.objects.select_related("external_account", "calendar").filter(
            owner=request.user, id=grant_id
        ).first()
        if not grant:
            django_messages.error(request, "Permesso DAV non trovato.")
            return redirect(f"{redirect_base}#dav-external-access")
        try:
            set_calendar_grant_active(
                owner=request.user,
                grant=grant,
                is_active=(action == "dav_activate_grant"),
            )
        except DavProvisioningError as exc:
            django_messages.error(request, f"Aggiornamento permesso DAV fallito: {exc}")
        else:
            label = "riattivato" if action == "dav_activate_grant" else "revocato"
            django_messages.success(
                request,
                f"Permesso {label}: {grant.external_account.dav_username} -> {grant.calendar.collection_path}.",
            )
        return redirect(f"{redirect_base}#dav-external-access")

    return None


@login_required
def profile(request):
    from ai_lab.models import ArchibaldInstructionState, ArchibaldPersonaConfig
    from archibald.prompting import build_archibald_system_for_user

    persona, _ = ArchibaldPersonaConfig.objects.get_or_create(owner=request.user)

    if request.method == "POST":
        action = (request.POST.get("action") or "").strip()
        custom_text = (request.POST.get("archibald_custom_instructions") or "").strip()

        if action == "rotate_dav_password" or action.startswith("dav_"):
            dav_response = _handle_dav_actions(request, action, redirect_base="/profile/dav/")
            if dav_response is not None:
                return dav_response

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
    dav_context = _build_dav_context(request, consume_onboarding=False)
    dav_onboarding = request.session.pop("dav_onboarding", None)
    context = {
        "archibald_custom_instructions": persona.custom_instructions or "",
        "archibald_instruction_states": states[:24],
        "archibald_system_preview": build_archibald_system_for_user(request.user),
        "archibald_persona": persona,
        "dav_onboarding_username": (dav_onboarding or {}).get("username", ""),
        "dav_onboarding_password": (dav_onboarding or {}).get("password", ""),
        **dav_context,
    }
    return render(request, "core/profile.html", context)


@login_required
def dav_management(request):
    if request.method == "POST":
        action = (request.POST.get("action") or "").strip()
        dav_response = _handle_dav_actions(request, action, redirect_base="/profile/dav/")
        if dav_response is not None:
            return dav_response

    context = _build_dav_context(request, consume_onboarding=True)
    return render(request, "core/dav_management.html", context)


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


def _mobile_json_error(error: str, status: int = 400):
    return JsonResponse({"ok": False, "error": error}, status=status)


def _mobile_parse_json(request):
    try:
        payload = json.loads((request.body or b"{}").decode("utf-8"))
    except (json.JSONDecodeError, UnicodeDecodeError):
        return None
    return payload if isinstance(payload, dict) else None


def _mobile_hash_token(token: str) -> str:
    return hashlib.sha256(token.encode("utf-8")).hexdigest()


def _mobile_access_ttl_seconds() -> int:
    raw = int(getattr(settings, "MOBILE_API_ACCESS_TTL_SECONDS", 900) or 900)
    return max(raw, 60)


def _mobile_refresh_ttl_days() -> int:
    raw = int(getattr(settings, "MOBILE_API_REFRESH_TTL_DAYS", 14) or 14)
    return max(raw, 1)


def _mobile_client_ip(request) -> str:
    forwarded = (request.headers.get("X-Forwarded-For") or "").split(",")[0].strip()
    if forwarded:
        return forwarded
    return (request.META.get("REMOTE_ADDR") or "").strip()


def _mobile_issue_tokens():
    return secrets.token_urlsafe(32), secrets.token_urlsafe(48)


def _mobile_create_session(user, request, device_label: str = ""):
    access_token, refresh_token = _mobile_issue_tokens()
    now = timezone.now()
    session = MobileApiSession.objects.create(
        user=user,
        access_token_hash=_mobile_hash_token(access_token),
        refresh_token_hash=_mobile_hash_token(refresh_token),
        access_expires_at=now + timedelta(seconds=_mobile_access_ttl_seconds()),
        refresh_expires_at=now + timedelta(days=_mobile_refresh_ttl_days()),
        device_label=(device_label or "")[:120],
        user_agent=(request.headers.get("User-Agent") or "")[:255],
        ip_address=_mobile_client_ip(request) or None,
    )
    return session, access_token, refresh_token


def _mobile_payload(user, access_token: str, refresh_token: str, session: MobileApiSession):
    return {
        "ok": True,
        "access_token": access_token,
        "access_expires_at": session.access_expires_at.isoformat(),
        "refresh_token": refresh_token,
        "refresh_expires_at": session.refresh_expires_at.isoformat(),
        "user": {
            "id": user.id,
            "username": user.username,
            "email": user.email,
        },
    }


def _mobile_bearer_token(request) -> str:
    header = (request.headers.get("Authorization") or "").strip()
    if not header.lower().startswith("bearer "):
        return ""
    return header[7:].strip()


def _mobile_authenticate_request(request):
    token = _mobile_bearer_token(request)
    if not token:
        return None, _mobile_json_error("missing_bearer_token", status=401)

    now = timezone.now()
    session = (
        MobileApiSession.objects.select_related("user")
        .filter(
            access_token_hash=_mobile_hash_token(token),
            revoked_at__isnull=True,
            access_expires_at__gt=now,
        )
        .first()
    )
    if not session:
        return None, _mobile_json_error("invalid_or_expired_access_token", status=401)

    session.last_used_at = now
    session.save(update_fields=["last_used_at", "updated_at"])
    return session, None


@csrf_exempt
@require_http_methods(["POST"])
def mobile_auth_login(request):
    payload = _mobile_parse_json(request)
    if payload is None:
        return _mobile_json_error("invalid_json", status=400)

    identity = (payload.get("identity") or payload.get("email") or payload.get("username") or "").strip()
    password = (payload.get("password") or "").strip()
    device_label = (payload.get("device_label") or "").strip()

    if not identity or not password:
        return _mobile_json_error("missing_credentials", status=400)

    user_model = get_user_model()
    user_by_email = user_model.objects.filter(email__iexact=identity).first()
    auth_username = user_by_email.username if user_by_email else identity
    user = authenticate(request, username=auth_username, password=password)
    if not user or not user.is_active:
        return _mobile_json_error("invalid_credentials", status=401)

    if settings.CALDAV_ENABLED:
        try:
            ensure_user_dav_access(user, raw_password=password)
        except DavProvisioningError as exc:
            logger.warning("DAV sync failed during mobile login for user=%s: %s", user.id, exc)

    session, access_token, refresh_token = _mobile_create_session(user, request, device_label=device_label)
    return JsonResponse(_mobile_payload(user, access_token, refresh_token, session))


@csrf_exempt
@require_http_methods(["POST"])
def mobile_auth_refresh(request):
    payload = _mobile_parse_json(request)
    if payload is None:
        return _mobile_json_error("invalid_json", status=400)

    refresh_token = (payload.get("refresh_token") or "").strip()
    if not refresh_token:
        return _mobile_json_error("missing_refresh_token", status=400)

    now = timezone.now()
    session = (
        MobileApiSession.objects.select_related("user")
        .filter(
            refresh_token_hash=_mobile_hash_token(refresh_token),
            revoked_at__isnull=True,
            refresh_expires_at__gt=now,
        )
        .first()
    )
    if not session:
        return _mobile_json_error("invalid_or_expired_refresh_token", status=401)

    access_token, new_refresh_token = _mobile_issue_tokens()
    session.access_token_hash = _mobile_hash_token(access_token)
    session.refresh_token_hash = _mobile_hash_token(new_refresh_token)
    session.access_expires_at = now + timedelta(seconds=_mobile_access_ttl_seconds())
    session.refresh_expires_at = now + timedelta(days=_mobile_refresh_ttl_days())
    session.last_used_at = now
    session.save(
        update_fields=[
            "access_token_hash",
            "refresh_token_hash",
            "access_expires_at",
            "refresh_expires_at",
            "last_used_at",
            "updated_at",
        ]
    )

    return JsonResponse(_mobile_payload(session.user, access_token, new_refresh_token, session))


@csrf_exempt
@require_http_methods(["POST"])
def mobile_auth_logout(request):
    payload = _mobile_parse_json(request)
    if payload is None:
        payload = {}

    now = timezone.now()
    session = None
    access_token = _mobile_bearer_token(request)
    if access_token:
        session = (
            MobileApiSession.objects.filter(
                access_token_hash=_mobile_hash_token(access_token),
                revoked_at__isnull=True,
            )
            .order_by("-id")
            .first()
        )

    if not session:
        refresh_token = (payload.get("refresh_token") or "").strip()
        if refresh_token:
            session = (
                MobileApiSession.objects.filter(
                    refresh_token_hash=_mobile_hash_token(refresh_token),
                    revoked_at__isnull=True,
                )
                .order_by("-id")
                .first()
            )

    if session:
        session.revoked_at = now
        session.save(update_fields=["revoked_at", "updated_at"])

    return JsonResponse({"ok": True})


@require_http_methods(["GET"])
def mobile_dashboard(request):
    session, error = _mobile_authenticate_request(request)
    if error:
        return error

    snapshot_context = _dashboard_snapshot_context(session.user)
    snapshot = snapshot_context["snapshot"]
    today = date.today()
    events = []
    for row in snapshot_context["focus_rows"][:8]:
        due_date = row.get("due_date")
        events.append(
            {
                "kind": row.get("kind"),
                "title": row.get("title"),
                "due_date": due_date.isoformat() if due_date else "",
                "url": row.get("url", ""),
                "warn": bool(due_date and due_date < today),
            }
        )

    return JsonResponse(
        {
            "ok": True,
            "synced_at": timezone.now().isoformat(),
            "metrics": {
                "open_tasks": snapshot["open_tasks"],
                "planner_queue": snapshot["planner_planned"],
                "alerts_open": snapshot["overdue_tasks"],
                "due_subscriptions_week": snapshot["due_subscriptions_week"],
            },
            "snapshot": {
                "tasks_today": snapshot["tasks_today"],
                "month_transactions": snapshot["month_transactions"],
                "month_income": snapshot["month_income"],
                "month_expense": snapshot["month_expense"],
                "month_balance": snapshot["month_balance"],
            },
            "events": events,
            "user": {
                "id": session.user.id,
                "username": session.user.username,
                "email": session.user.email,
            },
        }
    )


def _mobile_week_start_for(value: str | None) -> date:
    today = date.today()
    if value:
        try:
            parsed = date.fromisoformat(value)
            return parsed - timedelta(days=parsed.weekday())
        except ValueError:
            pass
    return today - timedelta(days=today.weekday())


def _mobile_routines_stats_from_items(items, check_map):
    planned = 0
    done = 0
    skipped = 0
    for item in items:
        check = check_map.get(item.id)
        status = check.status if check else RoutineCheck.Status.PLANNED
        if status == RoutineCheck.Status.DONE:
            done += 1
        elif status == RoutineCheck.Status.SKIPPED:
            skipped += 1
        else:
            planned += 1
    return {"planned": planned, "done": done, "skipped": skipped}


def _api_authenticate_request(request):
    token = _mobile_bearer_token(request)
    if token:
        return _mobile_authenticate_request(request)
    if request.user.is_authenticated:
        return SimpleNamespace(user=request.user), None
    return None, _mobile_json_error("authentication_required", status=401)


def _routines_response_for_user(user, week_value: str | None):
    week_start = _mobile_week_start_for(week_value)
    week_end = week_start + timedelta(days=6)
    items = (
        RoutineItem.objects.filter(owner=user, is_active=True, routine__is_active=True)
        .select_related("routine", "category", "project")
        .order_by("weekday", "time_start", "time_end", "title")
    )
    checks = RoutineCheck.objects.filter(owner=user, week_start=week_start, item__in=items)
    check_map = {check.item_id: check for check in checks}

    payload_items = []
    for item in items:
        check = check_map.get(item.id)
        payload_items.append(
            {
                "id": item.id,
                "title": item.title,
                "weekday": item.weekday,
                "weekday_label": item.get_weekday_display(),
                "time_start": item.time_start.strftime("%H:%M") if item.time_start else "",
                "time_end": item.time_end.strftime("%H:%M") if item.time_end else "",
                "note": item.note or "",
                "routine_id": item.routine_id,
                "container": item.routine.name,
                "category_id": item.category_id or "",
                "category": item.category.name if item.category_id else "",
                "project": item.project.name if item.project_id else "",
                "status": check.status if check else RoutineCheck.Status.PLANNED,
            }
        )

    stats = _mobile_routines_stats_from_items(items, check_map)
    return JsonResponse(
        {
            "ok": True,
            "synced_at": timezone.now().isoformat(),
            "week_start": week_start.isoformat(),
            "week_end": week_end.isoformat(),
            "stats": stats,
            "items": payload_items,
            "containers": list(
                Routine.objects.filter(owner=user, is_active=True)
                .order_by("name")
                .values("id", "name")
            ),
            "categories": list(
                RoutineCategory.objects.filter(owner=user, is_active=True)
                .order_by("name")
                .values("id", "name")
            ),
        }
    )


def _routines_check_for_user(user, payload):
    item_id = payload.get("item_id")
    status = (payload.get("status") or "").strip().upper()
    week_start = _mobile_week_start_for(payload.get("week"))

    allowed_statuses = {RoutineCheck.Status.PLANNED, RoutineCheck.Status.DONE, RoutineCheck.Status.SKIPPED}
    if status not in allowed_statuses:
        return _mobile_json_error("invalid_status", status=400)

    item = RoutineItem.objects.filter(owner=user, id=item_id).first()
    if not item:
        return _mobile_json_error("item_not_found", status=404)

    check, _created = RoutineCheck.objects.get_or_create(
        owner=user,
        item=item,
        week_start=week_start,
        defaults={"status": RoutineCheck.Status.PLANNED},
    )
    check.status = status
    check.save(update_fields=["status", "updated_at"])

    active_items = list(
        RoutineItem.objects.filter(owner=user, is_active=True, routine__is_active=True).only("id")
    )
    active_checks = RoutineCheck.objects.filter(owner=user, week_start=week_start, item__in=active_items)
    active_check_map = {row.item_id: row for row in active_checks}
    stats = _mobile_routines_stats_from_items(active_items, active_check_map)
    return JsonResponse(
        {
            "ok": True,
            "item_id": item.id,
            "status": check.status,
            "stats": stats,
            "week_start": week_start.isoformat(),
        }
    )


def _routines_item_create_for_user(user, payload):
    try:
        routine = get_routine_for_owner(
            owner=user,
            routine_id=payload.get("routine_id"),
            active_only=True,
        )
        category = get_category_for_owner(
            owner=user,
            category_id=payload.get("category_id"),
            active_only=True,
        )
        item = create_routine_item(
            owner=user,
            routine=routine,
            category=category,
            title=payload.get("title"),
            weekday=parse_weekday(payload.get("weekday")),
            time_start=payload.get("time_start"),
            time_end=payload.get("time_end"),
            note=payload.get("note"),
            is_active=True,
        )
    except RoutineCrudError as error:
        code = error.code
        if code in {"routine_not_found", "category_not_found"}:
            return _mobile_json_error(code, status=404)
        return _mobile_json_error(code, status=400)

    return JsonResponse({"ok": True, "item_id": item.id})


def _routines_item_update_for_user(user, payload):
    item_id = payload.get("item_id")
    item = RoutineItem.objects.filter(owner=user, id=item_id).first()
    if not item:
        return _mobile_json_error("item_not_found", status=404)

    try:
        routine = get_routine_for_owner(
            owner=user,
            routine_id=payload.get("routine_id"),
            active_only=True,
        )
        category = get_category_for_owner(
            owner=user,
            category_id=payload.get("category_id"),
            active_only=True,
        )
        update_routine_item(
            item=item,
            routine=routine,
            category=category,
            title=payload.get("title"),
            weekday=parse_weekday(payload.get("weekday")),
            time_start=payload.get("time_start"),
            time_end=payload.get("time_end"),
            note=payload.get("note"),
        )
    except RoutineCrudError as error:
        code = error.code
        if code in {"routine_not_found", "category_not_found"}:
            return _mobile_json_error(code, status=404)
        return _mobile_json_error(code, status=400)

    return JsonResponse({"ok": True, "item_id": item.id})


def _routines_item_delete_for_user(user, payload):
    item_id = payload.get("item_id")
    item = RoutineItem.objects.filter(owner=user, id=item_id).first()
    if not item:
        return _mobile_json_error("item_not_found", status=404)

    delete_routine_item(item=item)
    return JsonResponse({"ok": True, "item_id": item_id})


def _projects_response_for_user(user):
    projects = list(
        Project.objects.filter(owner=user)
        .select_related("customer", "category")
        .order_by("is_archived", "name")
    )

    sub_totals = {
        row["project_id"]: row["total"]
        for row in (
            SubProject.objects.filter(owner=user, is_archived=False)
            .values("project_id")
            .annotate(total=Count("id"))
        )
    }
    sub_done = {
        row["project_id"]: row["total"]
        for row in (
            SubProject.objects.filter(owner=user, is_archived=False, status=SubProject.Status.DONE)
            .values("project_id")
            .annotate(total=Count("id"))
        )
    }
    sub_blocked = {
        row["project_id"]: row["total"]
        for row in (
            SubProject.objects.filter(owner=user, is_archived=False, status=SubProject.Status.BLOCKED)
            .values("project_id")
            .annotate(total=Count("id"))
        )
    }

    payload_items = []
    for project in projects:
        payload_items.append(
            {
                "id": project.id,
                "name": project.name,
                "description": project.description or "",
                "is_archived": bool(project.is_archived),
                "customer": project.customer.name if project.customer_id else "",
                "category": project.category.name if project.category_id else "",
                "subprojects_total": int(sub_totals.get(project.id, 0)),
                "subprojects_done": int(sub_done.get(project.id, 0)),
                "subprojects_blocked": int(sub_blocked.get(project.id, 0)),
                "created_at": project.created_at.isoformat() if project.created_at else "",
                "updated_at": project.updated_at.isoformat() if project.updated_at else "",
            }
        )

    active_count = sum(1 for row in payload_items if not row["is_archived"])
    archived_count = sum(1 for row in payload_items if row["is_archived"])
    return JsonResponse(
        {
            "ok": True,
            "synced_at": timezone.now().isoformat(),
            "stats": {
                "total": len(payload_items),
                "active": active_count,
                "archived": archived_count,
            },
            "items": payload_items,
        }
    )


def _agenda_response_for_user(user, start_value: str | None, duration_value):
    start_date = timezone.localdate()
    if start_value:
        try:
            start_date = date.fromisoformat(start_value)
        except ValueError:
            start_date = timezone.localdate()

    try:
        duration = int(duration_value or 14)
    except (TypeError, ValueError):
        duration = 14
    duration = max(1, min(duration, 31))
    end_date = start_date + timedelta(days=duration - 1)

    items = list(
        AgendaItem.objects.filter(owner=user, due_date__range=(start_date, end_date))
        .select_related("project")
        .order_by("due_date", "due_time", "title")
    )

    payload_items = []
    for item in items:
        payload_items.append(
            {
                "id": item.id,
                "title": item.title,
                "item_type": item.item_type,
                "item_type_label": item.get_item_type_display(),
                "status": item.status,
                "status_label": item.get_status_display(),
                "due_date": item.due_date.isoformat() if item.due_date else "",
                "due_time": item.due_time.strftime("%H:%M") if item.due_time else "",
                "project": item.project.name if item.project_id else "",
                "note": item.note or "",
            }
        )

    activity_total = sum(1 for row in payload_items if row["item_type"] == AgendaItem.ItemType.ACTIVITY)
    reminder_total = sum(1 for row in payload_items if row["item_type"] == AgendaItem.ItemType.REMINDER)
    done_total = sum(1 for row in payload_items if row["status"] == AgendaItem.Status.DONE)
    planned_total = sum(1 for row in payload_items if row["status"] == AgendaItem.Status.PLANNED)

    return JsonResponse(
        {
            "ok": True,
            "synced_at": timezone.now().isoformat(),
            "range_start": start_date.isoformat(),
            "range_end": end_date.isoformat(),
            "stats": {
                "total": len(payload_items),
                "activities": activity_total,
                "reminders": reminder_total,
                "planned": planned_total,
                "done": done_total,
            },
            "items": payload_items,
        }
    )


@require_http_methods(["GET"])
def mobile_routines(request):
    session, error = _mobile_authenticate_request(request)
    if error:
        return error
    return _routines_response_for_user(session.user, request.GET.get("week"))


@csrf_exempt
@require_http_methods(["POST"])
def mobile_routines_check(request):
    payload = _mobile_parse_json(request)
    if payload is None:
        return _mobile_json_error("invalid_json", status=400)
    session, error = _mobile_authenticate_request(request)
    if error:
        return error
    return _routines_check_for_user(session.user, payload)


@csrf_exempt
@require_http_methods(["POST"])
def mobile_routines_item_create(request):
    payload = _mobile_parse_json(request)
    if payload is None:
        return _mobile_json_error("invalid_json", status=400)
    session, error = _mobile_authenticate_request(request)
    if error:
        return error
    return _routines_item_create_for_user(session.user, payload)


@csrf_exempt
@require_http_methods(["POST"])
def mobile_routines_item_update(request):
    payload = _mobile_parse_json(request)
    if payload is None:
        return _mobile_json_error("invalid_json", status=400)
    session, error = _mobile_authenticate_request(request)
    if error:
        return error
    return _routines_item_update_for_user(session.user, payload)


@csrf_exempt
@require_http_methods(["POST"])
def mobile_routines_item_delete(request):
    payload = _mobile_parse_json(request)
    if payload is None:
        return _mobile_json_error("invalid_json", status=400)
    session, error = _mobile_authenticate_request(request)
    if error:
        return error
    return _routines_item_delete_for_user(session.user, payload)


@require_http_methods(["GET"])
def api_routines(request):
    session, error = _api_authenticate_request(request)
    if error:
        return error
    return _routines_response_for_user(session.user, request.GET.get("week"))


@csrf_exempt
@require_http_methods(["POST"])
def api_routines_check(request):
    payload = _mobile_parse_json(request)
    if payload is None:
        return _mobile_json_error("invalid_json", status=400)
    session, error = _api_authenticate_request(request)
    if error:
        return error
    return _routines_check_for_user(session.user, payload)


@csrf_exempt
@require_http_methods(["POST"])
def api_routines_item_create(request):
    payload = _mobile_parse_json(request)
    if payload is None:
        return _mobile_json_error("invalid_json", status=400)
    session, error = _api_authenticate_request(request)
    if error:
        return error
    return _routines_item_create_for_user(session.user, payload)


@csrf_exempt
@require_http_methods(["POST"])
def api_routines_item_update(request):
    payload = _mobile_parse_json(request)
    if payload is None:
        return _mobile_json_error("invalid_json", status=400)
    session, error = _api_authenticate_request(request)
    if error:
        return error
    return _routines_item_update_for_user(session.user, payload)


@csrf_exempt
@require_http_methods(["POST"])
def api_routines_item_delete(request):
    payload = _mobile_parse_json(request)
    if payload is None:
        return _mobile_json_error("invalid_json", status=400)
    session, error = _api_authenticate_request(request)
    if error:
        return error
    return _routines_item_delete_for_user(session.user, payload)


@require_http_methods(["GET"])
def api_projects(request):
    session, error = _api_authenticate_request(request)
    if error:
        return error
    return _projects_response_for_user(session.user)


@require_http_methods(["GET"])
def mobile_projects(request):
    session, error = _mobile_authenticate_request(request)
    if error:
        return error
    return _projects_response_for_user(session.user)


@require_http_methods(["GET"])
def api_agenda(request):
    session, error = _api_authenticate_request(request)
    if error:
        return error
    return _agenda_response_for_user(
        session.user,
        request.GET.get("start"),
        request.GET.get("duration"),
    )


@require_http_methods(["GET"])
def mobile_agenda(request):
    session, error = _mobile_authenticate_request(request)
    if error:
        return error
    return _agenda_response_for_user(
        session.user,
        request.GET.get("start"),
        request.GET.get("duration"),
    )
