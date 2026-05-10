from datetime import date, datetime, time
from decimal import Decimal
from urllib.parse import urlencode

from django.db import transaction
from django.db.models import Count, Q
from django.utils import timezone
from django.utils.dateparse import parse_date
from django.utils.html import strip_tags

from contacts.models import Contact, ContactPriceList, ContactToolbox
from contacts.services import ensure_legacy_records_for_contact, upsert_contact
from finance_hub.models import Quote, VatCode
from planner.models import PlannerItem
from projects.models import (
    Project,
    ProjectNote,
    SubProject,
    SubProjectActivity,
)
from todo.models import Task
from transactions.models import Transaction


STORYBOARD_ACTIVITY_KINDS = {
    "all": "Tutto",
    "note": "Appunti",
    "task": "Task",
    "planner": "Reminder",
    "transaction": "Transazioni",
}


def _choice_counts(queryset, field_name, enum_class):
    counts = {
        row[field_name]: row["total"]
        for row in queryset.values(field_name).annotate(total=Count("id"))
    }
    return [
        {"key": member.value, "label": member.label, "total": counts.get(member.value, 0)}
        for member in enum_class
    ]


def _as_sort_datetime(value):
    if isinstance(value, datetime):
        if timezone.is_naive(value):
            return timezone.make_aware(value, timezone.get_current_timezone())
        return value
    if isinstance(value, date):
        return timezone.make_aware(datetime.combine(value, time.min), timezone.get_current_timezone())
    return timezone.now()


def _storyboard_filters_from_request(request):
    params = request.GET if request.method == "GET" else request.POST
    kind = (params.get("kind") or "all").strip().lower()
    if kind not in STORYBOARD_ACTIVITY_KINDS:
        kind = "all"
    query = (params.get("q") or "").strip()
    date_from_raw = (params.get("date_from") or "").strip()
    date_to_raw = (params.get("date_to") or "").strip()
    date_from = parse_date(date_from_raw) if date_from_raw else None
    date_to = parse_date(date_to_raw) if date_to_raw else None
    if date_from and date_to and date_from > date_to:
        date_from, date_to = date_to, date_from
        date_from_raw, date_to_raw = date_from.isoformat(), date_to.isoformat()
    return {
        "kind": kind,
        "q": query,
        "date_from": date_from,
        "date_to": date_to,
        "date_from_raw": date_from_raw if date_from else "",
        "date_to_raw": date_to_raw if date_to else "",
    }


def _storyboard_querystring(project_id, filters):
    params = {"id": project_id}
    if filters.get("kind") and filters["kind"] != "all":
        params["kind"] = filters["kind"]
    if filters.get("q"):
        params["q"] = filters["q"]
    if filters.get("date_from_raw"):
        params["date_from"] = filters["date_from_raw"]
    if filters.get("date_to_raw"):
        params["date_to"] = filters["date_to_raw"]
    return urlencode(params)


def _is_htmx_request(request):
    return request.headers.get("HX-Request") == "true"


def _storyboard_page_context(request, project, note_form=None, task_form=None, planner_form=None, active_form="note"):
    activity_filters = _storyboard_filters_from_request(request)
    activity_context = _build_storyboard_activity_context(request.user, project, activity_filters)
    # Calculate Health and Progress
    subprojects = project.subprojects.filter(is_archived=False)
    total_progress = 0
    if subprojects.exists():
        total_progress = sum(sp.completion_percent for sp in subprojects) // subprojects.count()

    overdue_tasks = Task.objects.filter(owner=request.user, project=project, status=Task.Status.TODO, due_date__lt=timezone.now().date()).count()

    health = "good"
    if overdue_tasks > 0:
        health = "warning"
    if overdue_tasks > 3:
        health = "danger"

    context = {
        "project": project,
        "note_form": note_form,
        "task_form": task_form,
        "planner_form": planner_form,
        "active_form": active_form,
        "project_progress": total_progress,
        "project_health": health,
        "overdue_tasks": overdue_tasks,
    }
    context.update(activity_context)
    return context


def _build_storyboard_activity_context(user, project, filters, per_kind_limit=80, result_limit=120):
    query = filters["q"]
    date_from = filters["date_from"]
    date_to = filters["date_to"]
    selected_kind = filters["kind"]

    notes_qs = ProjectNote.objects.filter(owner=user, project=project)
    if query:
        notes_qs = notes_qs.filter(content__icontains=query)
    if date_from:
        notes_qs = notes_qs.filter(created_at__date__gte=date_from)
    if date_to:
        notes_qs = notes_qs.filter(created_at__date__lte=date_to)

    tasks_qs = Task.objects.filter(owner=user, project=project)
    if query:
        tasks_qs = tasks_qs.filter(Q(title__icontains=query) | Q(note__icontains=query))
    if date_from:
        tasks_qs = tasks_qs.filter(Q(due_date__gte=date_from) | Q(due_date__isnull=True, created_at__date__gte=date_from))
    if date_to:
        tasks_qs = tasks_qs.filter(Q(due_date__lte=date_to) | Q(due_date__isnull=True, created_at__date__lte=date_to))

    planner_qs = PlannerItem.objects.filter(owner=user, project=project)
    if query:
        planner_qs = planner_qs.filter(Q(title__icontains=query) | Q(note__icontains=query))
    if date_from:
        planner_qs = planner_qs.filter(
            Q(due_date__gte=date_from) | Q(due_date__isnull=True, created_at__date__gte=date_from)
        )
    if date_to:
        planner_qs = planner_qs.filter(
            Q(due_date__lte=date_to) | Q(due_date__isnull=True, created_at__date__lte=date_to)
        )

    transactions_qs = Transaction.objects.filter(owner=user, project=project).select_related(
        "currency", "payee", "income_source"
    )
    if query:
        transactions_qs = transactions_qs.filter(
            Q(note__icontains=query) | Q(payee__name__icontains=query) | Q(income_source__name__icontains=query)
        )
    if date_from:
        transactions_qs = transactions_qs.filter(date__gte=date_from)
    if date_to:
        transactions_qs = transactions_qs.filter(date__lte=date_to)

    counts = {
        "note": notes_qs.count(),
        "task": tasks_qs.count(),
        "planner": planner_qs.count(),
        "transaction": transactions_qs.count(),
    }

    items_by_kind = {
        "note": [],
        "task": [],
        "planner": [],
        "transaction": [],
    }

    for note in notes_qs.order_by("-created_at", "-id")[:per_kind_limit]:
        items_by_kind["note"].append(
            {
                "id": note.id,
                "kind": "note",
                "kind_label": "Appunto",
                "sort_at": _as_sort_datetime(note.created_at),
                "display_at": note.created_at,
                "display_has_time": True,
                "title": "Appunto progetto",
                "subtitle": note.created_at.strftime("%d/%m/%Y %H:%M"),
                "description_html": note.content,
                "description_text": strip_tags(note.content).strip(),
                "attachment_url": note.attachment.url if note.attachment else "",
                "attachment_label": "Apri allegato",
                "can_delete": True,
            }
        )

    for task in tasks_qs.order_by("-due_date", "-created_at", "-id")[:per_kind_limit]:
        due_or_created = task.due_date or task.created_at.date()
        items_by_kind["task"].append(
            {
                "kind": "task",
                "kind_label": "Task",
                "sort_at": _as_sort_datetime(due_or_created),
                "display_at": due_or_created,
                "display_has_time": False,
                "title": task.title,
                "subtitle": f"{task.get_status_display()} · Priorita {task.get_priority_display()}",
                "description_text": task.note,
                "description_html": "",
                "attachment_url": "",
                "attachment_label": "",
                "can_delete": False,
            }
        )

    for item in planner_qs.order_by("-due_date", "-created_at", "-id")[:per_kind_limit]:
        due_or_created = item.due_date or item.created_at.date()
        items_by_kind["planner"].append(
            {
                "kind": "planner",
                "kind_label": "Reminder",
                "sort_at": _as_sort_datetime(due_or_created),
                "display_at": due_or_created,
                "display_has_time": False,
                "title": item.title,
                "subtitle": item.get_status_display(),
                "description_text": item.note,
                "description_html": "",
                "attachment_url": "",
                "attachment_label": "",
                "can_delete": False,
            }
        )

    for tx in transactions_qs.order_by("-date", "-id")[:per_kind_limit]:
        actor = tx.payee.name if tx.payee else tx.income_source.name if tx.income_source else ""
        subtitle = f"{tx.get_tx_type_display()} · {tx.amount} {tx.currency.code}"
        if actor:
            subtitle = f"{subtitle} · {actor}"
        items_by_kind["transaction"].append(
            {
                "kind": "transaction",
                "kind_label": "Transazione",
                "sort_at": _as_sort_datetime(tx.date),
                "display_at": tx.date,
                "display_has_time": False,
                "title": subtitle,
                "subtitle": tx.date.strftime("%d/%m/%Y"),
                "description_text": tx.note,
                "description_html": "",
                "attachment_url": tx.attachment.url if tx.attachment else "",
                "attachment_label": "Apri ricevuta",
                "can_delete": False,
            }
        )

    if selected_kind == "all":
        selected_items = []
        for kind in ("transaction", "note", "task", "planner"):
            selected_items.extend(items_by_kind[kind])
    else:
        selected_items = list(items_by_kind[selected_kind])

    selected_items.sort(key=lambda item: item["sort_at"], reverse=True)
    selected_items = selected_items[:result_limit]

    total_count = counts.get(selected_kind, 0) if selected_kind != "all" else sum(counts.values())
    result_count = len(selected_items)
    return {
        "activity_filters": filters,
        "activity_kind_choices": [
            {
                "key": key,
                "label": label,
                "total": (sum(counts.values()) if key == "all" else counts.get(key, 0)),
            }
            for key, label in STORYBOARD_ACTIVITY_KINDS.items()
        ],
        "activity_counts": counts,
        "activity_items": selected_items,
        "activity_result_count": result_count,
        "activity_total_count": total_count,
    }


def _subproject_counts(queryset):
    return {
        "total": queryset.count(),
        "active": queryset.filter(is_archived=False).exclude(status=SubProject.Status.DONE).count(),
        "done": queryset.filter(status=SubProject.Status.DONE).count(),
        "blocked": queryset.filter(status=SubProject.Status.BLOCKED).count(),
    }


def _ensure_default_vat_codes(user):
    defaults = [
        ("22", "IVA ordinaria", Decimal("22.00")),
        ("10", "IVA ridotta", Decimal("10.00")),
        ("4", "IVA super ridotta", Decimal("4.00")),
        ("ESENTE", "Operazione esente", Decimal("0.00")),
    ]
    for code, description, rate in defaults:
        VatCode.objects.get_or_create(
            owner=user,
            code=code,
            defaults={
                "description": description,
                "rate": rate,
                "is_active": True,
            },
        )


def _vat_rates_payload(user):
    rows = VatCode.objects.filter(owner=user, is_active=True).order_by("rate", "code")
    return [
        {
            "id": row.id,
            "code": row.code,
            "rate": str(row.rate),
            "description": row.description,
        }
        for row in rows
    ]


def _sync_contact_from_customer(owner, customer):
    if owner is None or customer is None:
        return
    contact = upsert_contact(
        owner,
        customer.name,
        entity_type=Contact.EntityType.HYBRID,
        email=customer.email,
        phone=customer.phone,
        notes=customer.notes,
        roles={"role_customer"},
    )
    ensure_legacy_records_for_contact(contact)


def _apply_quote_vat_to_line(line, quote):
    vat_rate = quote.vat_code.rate if quote.vat_code_id else Decimal("0.00")
    multiplier = Decimal("1.00") + (vat_rate / Decimal("100.00"))
    line.vat_code = quote.vat_code.code if quote.vat_code_id else ""
    line.gross_amount = ((line.net_amount or Decimal("0.00")) * multiplier).quantize(Decimal("0.01"))


def _sync_quote_lines_vat(quote):
    for line in quote.lines.all():
        _apply_quote_vat_to_line(line, quote)
        line.save(update_fields=["vat_code", "gross_amount", "updated_at"])


def _project_quote_price_lists(user, customer):
    if user is None or customer is None:
        return None, []

    contact = upsert_contact(
        user,
        customer.name,
        entity_type=Contact.EntityType.HYBRID,
        email=customer.email,
        phone=customer.phone,
        notes=customer.notes,
        roles={"role_customer"},
    )
    if contact is None:
        return None, []

    toolbox, _ = ContactToolbox.objects.get_or_create(owner=user, contact=contact)
    price_lists = (
        ContactPriceList.objects.filter(owner=user, toolbox=toolbox, is_active=True)
        .prefetch_related("items")
        .order_by("-updated_at", "-id")
    )
    payload = []
    for price_list in price_lists:
        payload.append(
            {
                "id": price_list.id,
                "title": price_list.title,
                "currency_code": price_list.currency_code,
                "items": [
                    {
                        "code": item.code,
                        "title": item.title,
                        "description": item.description,
                        "min_quantity": str(item.min_quantity),
                        "unit_price": str(item.unit_price),
                    }
                    for item in price_list.items.filter(is_active=True).order_by("row_order", "id")
                ],
            }
        )
    return contact, payload


HERO_ACTIONS_MODULES = {
    "generali": [
        {"key": "back", "label": "Torna ai progetti", "default": True},
        {"key": "edit", "label": "Modifica progetto", "default": True},
        {"key": "config", "label": "Configura tasti", "default": False},
    ],
    "operativi": [
        {"key": "expense", "label": "Inserisci spesa", "default": True},
        {"key": "income", "label": "Inserisci guadagno", "default": True},
        {"key": "quote", "label": "Nuovo preventivo", "default": True},
        {"key": "planner", "label": "Aggiungi promemoria", "default": True},
        {"key": "routine_item", "label": "Aggiungi routine", "default": False},
        {"key": "storyboard", "label": "Storyboard", "default": True},
    ],
}


def _hero_actions_for_project(user, project):
    from .models import ProjectHeroActionsConfig

    config_obj = ProjectHeroActionsConfig.objects.filter(user=user, project=project).first()
    selected = {}
    if config_obj and config_obj.config:
        selected = config_obj.config

    allowed = []
    hidden = []
    for module, actions in HERO_ACTIONS_MODULES.items():
        enabled_keys = selected.get(module)
        for action in actions:
            is_enabled = False
            if enabled_keys is not None:
                is_enabled = action["key"] in enabled_keys
            else:
                is_enabled = action.get("default", False)
            if is_enabled:
                allowed.append(action["key"])
            else:
                hidden.append({**action, "module": module})

    return {
        "allowed_actions": allowed,
        "hidden_actions": hidden,
        "hero_actions_override": selected if config_obj else None,
    }
