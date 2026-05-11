# core/helpers.py
from datetime import date, timedelta
from decimal import Decimal
import hashlib
import json
import logging
import mimetypes
import posixpath
import re
import secrets
from types import SimpleNamespace
from urllib.parse import quote, urljoin

from django.conf import settings
from django.contrib import messages as django_messages
from django.db.models import Count, Sum
from django.db.models.functions import Coalesce
from django.http import FileResponse, Http404, JsonResponse
from django.shortcuts import redirect
from django.utils import timezone

from agenda.models import AgendaItem, WorkLog
from contacts.models import Contact
from planner.models import PlannerItem
from projects.models import Project, SubProject, ProjectNote
from todos.models import TodoList, TodoCategory, TodoRecurrence, TodoItem
from finance_hub.models import SubscriptionOccurrence, Account
from todos.models import TodoItem
from transactions.models import Transaction

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
from .models import (
    DavAccount,
    DavCalendarGrant,
    DavExternalAccount,
    DavManagedCalendar,
    DavTeam,
    MobileApiSession,
    UserNavConfig,
)
from todos.services import (
    TodoListCrudError,
    create_todo_item,
    delete_todo_item,
    get_category_for_owner,
    get_todo_for_owner,
    parse_weekday,
    update_todo_item,
)

logger = logging.getLogger(__name__)

_DAV_TEAM_SLUG_SANITIZER = re.compile(r"[^a-z0-9._-]+")

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
        "description": "TodoItem giornalieri e backlog.",
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
        "id": "todos",
        "title": "TodoLists",
        "description": "TodoList e statistiche disciplina.",
        "url": "/todos/",
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


def _resolve_owned_media_file(owner, relative_path):
    owned_file_fields = (
        (Contact, "profile_image"),
        (ProjectNote, "attachment"),
        (Transaction, "attachment"),
    )
    for model, field_name in owned_file_fields:
        filters = {"owner": owner, field_name: relative_path}
        instance = model.objects.filter(**filters).only(field_name).first()
        if instance is not None:
            return getattr(instance, field_name)
    return None


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


def _dashboard_snapshot_context(user):
    today = date.today()
    week_end = today + timedelta(days=7)
    month_start = today.replace(day=1)
    month_end = (month_start + timedelta(days=32)).replace(day=1) - timedelta(days=1)

    open_tasks_qs = TodoItem.objects.filter(owner=user).exclude(status=TodoItem.Status.DONE)
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
        TodoItem.objects.filter(owner=user, due_date__range=(start, end))
        .exclude(status=TodoItem.Status.DONE)
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

    todo_counts = (
        TodoItem.objects.filter(owner=user, is_active=True)
        .values("weekday")
        .annotate(count=Count("id"))
    )
    todo_map = {row["weekday"]: row["count"] for row in todo_counts}
    if todo_map:
        cursor = start
        while cursor <= end:
            count = todo_map.get(cursor.weekday())
            if count:
                add_event(cursor, "todo", "TodoList", count)
            cursor += timedelta(days=1)

    return events


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


def _mobile_week_start_for(value: str | None) -> date:
    today = date.today()
    if value:
        try:
            parsed = date.fromisoformat(value)
            return parsed - timedelta(days=parsed.weekday())
        except ValueError:
            pass
    return today - timedelta(days=today.weekday())


def _mobile_todos_stats_from_items(items, check_map):
    planned = 0
    done = 0
    skipped = 0
    for item in items:
        check = check_map.get(item.id)
        status = check.status if check else TodoRecurrence.Status.PLANNED
        if status == TodoRecurrence.Status.DONE:
            done += 1
        elif status == TodoRecurrence.Status.SKIPPED:
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


def _dav_collection_url(base_url: str, principal: str, collection_slug: str = "") -> str:
    base = (base_url or "").strip()
    if not base:
        return ""
    if not base.endswith("/"):
        base = f"{base}/"
    principal_value = (principal or "").strip()
    if not principal_value:
        return base
    principal_segments = [quote(segment, safe="@._+-") for segment in principal_value.strip("/").split("/") if segment]
    principal_token = "/".join(principal_segments)
    if not principal_token:
        return base
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


def _normalize_dav_team_slug(value: str) -> str:
    slug = _DAV_TEAM_SLUG_SANITIZER.sub("-", (value or "").strip().lower()).strip("-.")
    if not slug:
        raise DavProvisioningError("Nome team non valido.")
    return slug


def _build_dav_context(request, *, consume_onboarding: bool) -> dict:
    base_url = caldav_base_url()
    dav_account = DavAccount.objects.filter(user=request.user).first()
    dav_teams_qs = DavTeam.objects.filter(owner=request.user).order_by("-is_active", "name", "slug")
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
        "dav_personal_principal": getattr(dav_account, "dav_username", ""),
        "dav_default_team_collection": settings.CALDAV_DEFAULT_TEAM_COLLECTION,
        "dav_access_pattern_url": f"{base_url}{{username}}/{{collezione}}/" if base_url else "",
        "dav_team_access_pattern_url": f"{base_url}{{username}}/{{team}}/{{collezione}}/" if base_url else "",
        "dav_account_root_url": _dav_collection_url(base_url, getattr(dav_account, "dav_username", "")),
        "dav_default_team_collection_url": _dav_collection_url(base_url, default_team_principal, default_team_slug),
        "dav_external_onboarding_username": (onboarding_payload or {}).get("username", ""),
        "dav_external_onboarding_password": (onboarding_payload or {}).get("password", ""),
        "dav_teams": dav_teams_qs[:200],
        "dav_active_teams": dav_teams_qs.filter(is_active=True)[:200],
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

    if action == "dav_create_team":
        raw_name = (request.POST.get("dav_team_name") or "").strip()
        raw_slug = (request.POST.get("dav_team_slug") or "").strip()
        try:
            team_slug = _normalize_dav_team_slug(raw_slug or raw_name)
        except DavProvisioningError as exc:
            django_messages.error(request, f"Creazione team DAV fallita: {exc}")
            return redirect(f"{redirect_base}#dav-team")

        team_name = raw_name[:120] if raw_name else team_slug
        team, created = DavTeam.objects.get_or_create(
            owner=request.user,
            slug=team_slug,
            defaults={
                "name": team_name,
                "is_active": True,
            },
        )
        if not created:
            team.name = team_name
            team.is_active = True
            team.save(update_fields=["name", "is_active", "updated_at"])
            django_messages.success(request, f"Team DAV aggiornato: {team.name} ({team.slug}).")
        else:
            django_messages.success(request, f"Team DAV creato: {team.name} ({team.slug}).")
        return redirect(f"{redirect_base}#dav-team")

    if action in {"dav_activate_team", "dav_deactivate_team"}:
        team_id = request.POST.get("team_id")
        team = DavTeam.objects.filter(owner=request.user, id=team_id).first()
        if not team:
            django_messages.error(request, "Team DAV non trovato.")
            return redirect(f"{redirect_base}#dav-team")
        team.is_active = action == "dav_activate_team"
        team.save(update_fields=["is_active", "updated_at"])
        label = "riattivato" if team.is_active else "disattivato"
        django_messages.success(request, f"Team DAV {label}: {team.name} ({team.slug}).")
        return redirect(f"{redirect_base}#dav-team")

    if action == "dav_create_calendar":
        scope = (request.POST.get("dav_collection_scope") or "").strip().lower()
        if not scope:
            # Backward compatibility with previous form payloads.
            scope = "team" if (request.POST.get("dav_calendar_principal") or "").strip().lower() == "team" else "personal"
        dav_account = DavAccount.objects.filter(user=request.user, is_active=True).first()
        if not dav_account:
            django_messages.error(
                request,
                "Account DAV personale non trovato o disattivo. Effettua di nuovo login prima di creare una collezione.",
            )
            return redirect(f"{redirect_base}#dav-external-access")

        principal_value = ""
        if scope == "personal":
            principal_value = dav_account.dav_username
        elif scope == "team":
            team_id = (request.POST.get("dav_team_id") or "").strip()
            if team_id:
                team = DavTeam.objects.filter(owner=request.user, id=team_id, is_active=True).first()
                if not team:
                    django_messages.error(request, "Seleziona un team DAV valido.")
                    return redirect(f"{redirect_base}#dav-external-access")
                principal_value = f"{dav_account.dav_username}/{team.slug}"
            else:
                legacy_is_global_team = (request.POST.get("dav_calendar_principal") or "").strip().lower() == "team"
                if legacy_is_global_team:
                    # Backward compatibility with legacy flow (/dav/team/{collezione}).
                    principal_value = "team"
                else:
                    django_messages.error(request, "Seleziona il team su cui creare la collezione.")
                    return redirect(f"{redirect_base}#dav-external-access")
        else:
            django_messages.error(request, "Tipo collezione non valido.")
            return redirect(f"{redirect_base}#dav-external-access")

        try:
            calendar = create_managed_calendar(
                owner=request.user,
                principal=principal_value,
                calendar_slug=request.POST.get("dav_collection_slug")
                or request.POST.get("dav_calendar_slug")
                or "",
                display_name=request.POST.get("dav_collection_display_name")
                or request.POST.get("dav_calendar_display_name")
                or "",
            )
        except DavProvisioningError as exc:
            django_messages.error(request, f"Creazione collezione DAV fallita: {exc}")
        else:
            django_messages.success(
                request,
                f"Collezione DAV pronta: {calendar.collection_path}",
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


def _dashboard_widgets_for_user(user):
    nav_config, _ = UserNavConfig.objects.get_or_create(user=user)
    config = nav_config.config if isinstance(nav_config.config, dict) else {}
    return _normalize_dashboard_widgets(config.get("dashboard_widgets"))


def _dashboard_preferences_for_user(user):
    nav_config, _ = UserNavConfig.objects.get_or_create(user=user)
    config = nav_config.config if isinstance(nav_config.config, dict) else {}
    return _normalize_dashboard_preferences(config.get("dashboard_preferences"))


def _todos_response_for_user(user, week_value: str | None):
    week_start = _mobile_week_start_for(week_value)
    week_end = week_start + timedelta(days=6)
    items = (
        TodoItem.objects.filter(owner=user, is_active=True, todo__is_active=True)
        .select_related("todo", "category", "project")
        .order_by("weekday", "time_start", "time_end", "title")
    )
    checks = TodoRecurrence.objects.filter(owner=user, week_start=week_start, item__in=items)
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
                "todo_id": item.todo_id,
                "container": item.todo.name,
                "category_id": item.category_id or "",
                "category": item.category.name if item.category_id else "",
                "project": item.project.name if item.project_id else "",
                "status": check.status if check else TodoRecurrence.Status.PLANNED,
            }
        )

    stats = _mobile_todos_stats_from_items(items, check_map)
    return JsonResponse(
        {
            "ok": True,
            "synced_at": timezone.now().isoformat(),
            "week_start": week_start.isoformat(),
            "week_end": week_end.isoformat(),
            "stats": stats,
            "items": payload_items,
            "containers": list(
                TodoList.objects.filter(owner=user, is_active=True)
                .order_by("name")
                .values("id", "name")
            ),
            "categories": list(
                TodoCategory.objects.filter(owner=user, is_active=True)
                .order_by("name")
                .values("id", "name")
            ),
        }
    )


def _todos_check_for_user(user, payload):
    item_id = payload.get("item_id")
    status = (payload.get("status") or "").strip().upper()
    week_start = _mobile_week_start_for(payload.get("week"))

    allowed_statuses = {TodoRecurrence.Status.PLANNED, TodoRecurrence.Status.DONE, TodoRecurrence.Status.SKIPPED}
    if status not in allowed_statuses:
        return _mobile_json_error("invalid_status", status=400)

    item = TodoItem.objects.filter(owner=user, id=item_id).first()
    if not item:
        return _mobile_json_error("item_not_found", status=404)

    check, _created = TodoRecurrence.objects.get_or_create(
        owner=user,
        item=item,
        week_start=week_start,
        defaults={"status": TodoRecurrence.Status.PLANNED},
    )
    check.status = status
    check.save(update_fields=["status", "updated_at"])

    active_items = list(
        TodoItem.objects.filter(owner=user, is_active=True, todo__is_active=True).only("id")
    )
    active_checks = TodoRecurrence.objects.filter(owner=user, week_start=week_start, item__in=active_items)
    active_check_map = {row.item_id: row for row in active_checks}
    stats = _mobile_todos_stats_from_items(active_items, active_check_map)
    return JsonResponse(
        {
            "ok": True,
            "item_id": item.id,
            "status": check.status,
            "stats": stats,
            "week_start": week_start.isoformat(),
        }
    )


def _todos_item_create_for_user(user, payload):
    try:
        todo = get_todo_for_owner(
            owner=user,
            todo_id=payload.get("todo_id"),
            active_only=True,
        )
        category = get_category_for_owner(
            owner=user,
            category_id=payload.get("category_id"),
            active_only=True,
        )
        item = create_todo_item(
            owner=user,
            todo=todo,
            category=category,
            title=payload.get("title"),
            weekday=parse_weekday(payload.get("weekday")),
            time_start=payload.get("time_start"),
            time_end=payload.get("time_end"),
            note=payload.get("note"),
            is_active=True,
        )
    except TodoListCrudError as error:
        code = error.code
        if code in {"todo_not_found", "category_not_found"}:
            return _mobile_json_error(code, status=404)
        return _mobile_json_error(code, status=400)

    return JsonResponse({"ok": True, "item_id": item.id})


def _todos_item_update_for_user(user, payload):
    item_id = payload.get("item_id")
    item = TodoItem.objects.filter(owner=user, id=item_id).first()
    if not item:
        return _mobile_json_error("item_not_found", status=404)

    try:
        todo = get_todo_for_owner(
            owner=user,
            todo_id=payload.get("todo_id"),
            active_only=True,
        )
        category = get_category_for_owner(
            owner=user,
            category_id=payload.get("category_id"),
            active_only=True,
        )
        update_todo_item(
            item=item,
            todo=todo,
            category=category,
            title=payload.get("title"),
            weekday=parse_weekday(payload.get("weekday")),
            time_start=payload.get("time_start"),
            time_end=payload.get("time_end"),
            note=payload.get("note"),
        )
    except TodoListCrudError as error:
        code = error.code
        if code in {"todo_not_found", "category_not_found"}:
            return _mobile_json_error(code, status=404)
        return _mobile_json_error(code, status=400)

    return JsonResponse({"ok": True, "item_id": item.id})


def _todos_item_delete_for_user(user, payload):
    item_id = payload.get("item_id")
    item = TodoItem.objects.filter(owner=user, id=item_id).first()
    if not item:
        return _mobile_json_error("item_not_found", status=404)

    delete_todo_item(item=item)
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
