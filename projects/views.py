from datetime import date, datetime, time
from decimal import Decimal
from urllib.parse import urlencode

from django.contrib.auth.decorators import login_required
from django.db import transaction
from django.db.models import Count, Max, Min, Q, Sum
from django.shortcuts import get_object_or_404, redirect, render
from django.utils import timezone
from django.utils.dateparse import parse_date
from django.utils.html import strip_tags

from contacts.models import Contact, ContactPriceList, ContactToolbox
from contacts.services import ensure_legacy_records_for_contact, upsert_contact
from finance_hub.forms import QuoteForm, QuoteLineFormSet
from finance_hub.models import Quote, VatCode
from .category_forms import CategoryForm
from .note_forms import ProjectNoteForm
from .forms import ProjectForm, ProjectPlannerQuickForm, SubProjectActivityForm, SubProjectForm
from .models import (
    Category,
    Customer,
    Project,
    ProjectHeroActionsConfig,
    ProjectNote,
    SubProject,
    SubProjectActivity,
)
from .storyboard_forms import StoryboardPlannerForm, StoryboardTaskForm
from core.hero_actions import HERO_ACTIONS
from core.models import UserHeroActionsConfig


STORYBOARD_ACTIVITY_KINDS = {
    "all": "Tutto",
    "note": "Appunti",
    "task": "Task",
    "planner": "Reminder",
    "transaction": "Transazioni",
}


# Helpers
def _choice_counts(queryset, field_name, enum_class):
    counts = {
        row[field_name]: row["total"]
        for row in queryset.values(field_name).annotate(total=Count("id"))
    }
    return [
        {"key": member.value, "label": member.label, "total": counts.get(member.value, 0)}
        for member in enum_class
    ]


def _resolve_hero_actions(user, module, override_config=None):
    if override_config and override_config.get("_configured"):
        override_list = override_config.get(module)
        if isinstance(override_list, list):
            return set(override_list)
    user_config = UserHeroActionsConfig.objects.filter(user=user).first()
    if user_config and user_config.config.get("_configured"):
        allowed = user_config.config.get(module, [])
        if isinstance(allowed, list):
            return set(allowed)
    defaults = HERO_ACTIONS.get(module, [])
    return {action["key"] for action in defaults if action.get("default")}


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


def _build_storyboard_activity_context(user, project, filters, per_kind_limit=80, result_limit=120):
    from planner.models import PlannerItem
    from todo.models import Task
    from transactions.models import Transaction

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


# Create your views here.
@login_required
def dashboard(request):
    user = request.user
    scope = (request.GET.get("scope") or "active").strip().lower()
    if scope not in {"active", "archived", "all"}:
        scope = "active"

    projects_qs = Project.objects.filter(owner=user).select_related("customer", "category").order_by("is_archived", "name")
    if scope == "active":
        projects_qs = projects_qs.filter(is_archived=False)
    elif scope == "archived":
        projects_qs = projects_qs.filter(is_archived=True)

    project_ids = list(projects_qs.values_list("id", flat=True))
    project_rows = []
    if project_ids:
        from planner.models import PlannerItem
        from routines.models import RoutineItem
        from subscriptions.models import Subscription
        from todo.models import Task
        from transactions.models import Transaction

        tx_map = {
            row["project_id"]: row
            for row in (
                Transaction.objects.filter(owner=user, project_id__in=project_ids)
                .values("project_id")
                .annotate(
                    total=Count("id"),
                    income=Sum("amount", filter=Q(tx_type=Transaction.Type.INCOME)),
                    expense=Sum("amount", filter=Q(tx_type=Transaction.Type.EXPENSE)),
                    last_date=Max("date"),
                )
            )
        }
        sub_map = {
            row["project_id"]: row
            for row in (
                Subscription.objects.filter(owner=user, project_id__in=project_ids)
                .values("project_id")
                .annotate(
                    total=Count("id"),
                    active=Count("id", filter=Q(status=Subscription.Status.ACTIVE)),
                    next_due=Min("next_due_date", filter=Q(status=Subscription.Status.ACTIVE)),
                )
            )
        }
        todo_map = {
            row["project_id"]: row
            for row in (
                Task.objects.filter(owner=user, project_id__in=project_ids)
                .values("project_id")
                .annotate(
                    total=Count("id"),
                    open_count=Count("id", filter=Q(status__in=[Task.Status.OPEN, Task.Status.IN_PROGRESS])),
                )
            )
        }
        planner_map = {
            row["project_id"]: row
            for row in (
                PlannerItem.objects.filter(owner=user, project_id__in=project_ids)
                .values("project_id")
                .annotate(
                    total=Count("id"),
                    planned=Count("id", filter=Q(status=PlannerItem.Status.PLANNED)),
                )
            )
        }
        routine_map = {
            row["project_id"]: row
            for row in (
                RoutineItem.objects.filter(owner=user, project_id__in=project_ids)
                .values("project_id")
                .annotate(
                    total=Count("id"),
                    active=Count("id", filter=Q(is_active=True)),
                )
            )
        }

        for project in projects_qs:
            tx = tx_map.get(project.id, {})
            subs = sub_map.get(project.id, {})
            todo = todo_map.get(project.id, {})
            planner = planner_map.get(project.id, {})
            routine = routine_map.get(project.id, {})

            income_total = tx.get("income") or 0
            expense_total = tx.get("expense") or 0
            project_rows.append(
                {
                    "project": project,
                    "customer_name": project.customer.name if project.customer else "Nessun cliente",
                    "category_name": project.category.name if project.category else "Nessuna categoria",
                    "tx_total": tx.get("total", 0),
                    "income_total": income_total,
                    "expense_total": expense_total,
                    "balance": income_total - expense_total,
                    "last_tx_date": tx.get("last_date"),
                    "subscriptions_total": subs.get("total", 0),
                    "subscriptions_active": subs.get("active", 0),
                    "next_subscription_due": subs.get("next_due"),
                    "todo_open": todo.get("open_count", 0),
                    "todo_total": todo.get("total", 0),
                    "planner_planned": planner.get("planned", 0),
                    "planner_total": planner.get("total", 0),
                    "routines_active": routine.get("active", 0),
                }
            )

    counts = {
        "active": Project.objects.filter(owner=user, is_archived=False).count(),
        "archived": Project.objects.filter(owner=user, is_archived=True).count(),
        "categories": Category.objects.filter(owner=user).count(),
        "customers": Contact.objects.filter(owner=user, role_customer=True).count(),
    }
    summary = {
        "visible_projects": len(project_rows),
        "income_total": sum((row["income_total"] for row in project_rows), Decimal("0")),
        "expense_total": sum((row["expense_total"] for row in project_rows), Decimal("0")),
        "tx_total": sum((row["tx_total"] for row in project_rows), 0),
        "todo_open_total": sum((row["todo_open"] for row in project_rows), 0),
        "todo_total": sum((row["todo_total"] for row in project_rows), 0),
        "planner_planned_total": sum((row["planner_planned"] for row in project_rows), 0),
        "planner_total": sum((row["planner_total"] for row in project_rows), 0),
        "subs_active_total": sum((row["subscriptions_active"] for row in project_rows), 0),
        "subs_total": sum((row["subscriptions_total"] for row in project_rows), 0),
        "routines_active_total": sum((row["routines_active"] for row in project_rows), 0),
    }
    summary["balance_total"] = summary["income_total"] - summary["expense_total"]
    return render(
        request,
        "projects/dashboard.html",
        {
            "project_rows": project_rows,
            "counts": counts,
            "summary": summary,
            "scope": scope,
        },
    )


@login_required
def add_project(request):
    if request.method == "POST":
        form = ProjectForm(request.POST, owner=request.user)
        if form.is_valid():
            project = form.save(commit=False)
            project.owner = request.user
            project.save()
            return redirect("/projects/")
    else:
        form = ProjectForm(owner=request.user)
    return render(request, "projects/add_project.html", {"form": form})


@login_required
def remove_project(request):
    project_id = request.GET.get("id")
    project = None
    if project_id:
        project = get_object_or_404(Project, id=project_id, owner=request.user)
        if request.method == "POST":
            project.delete()
            return redirect("/projects/")
    projects = Project.objects.filter(owner=request.user).order_by("name")[:20]
    return render(request, "projects/remove_project.html", {"project": project, "projects": projects})


@login_required
def update_project(request):
    project_id = request.GET.get("id")
    project = None
    if project_id:
        project = get_object_or_404(Project, id=project_id, owner=request.user)
        if request.method == "POST":
            form = ProjectForm(request.POST, instance=project, owner=request.user)
            if form.is_valid():
                form.save()
                return redirect("/projects/")
        else:
            form = ProjectForm(instance=project, owner=request.user)
        return render(request, "projects/update_project.html", {"form": form, "project": project})
    projects = Project.objects.filter(owner=request.user).order_by("name")[:20]
    return render(request, "projects/update_project.html", {"projects": projects})


@login_required
def add_project_quote(request):
    project_id = request.GET.get("project") or request.POST.get("project_id")
    if not project_id:
        return redirect("/projects/")

    project = get_object_or_404(Project.objects.select_related("customer"), id=project_id, owner=request.user)
    locked_customer = project.customer
    _ensure_default_vat_codes(request.user)
    price_lists_contact, price_lists_payload = _project_quote_price_lists(request.user, locked_customer)

    form_initial = {
        "project": project.id,
        "customer": locked_customer.id if locked_customer else None,
        "title": f"Preventivo {project.name}",
    }

    if request.method == "POST":
        form = QuoteForm(request.POST, owner=request.user, initial=form_initial)
        temp_item = Quote(owner=request.user, project=project, customer=locked_customer)
        line_formset = QuoteLineFormSet(request.POST, instance=temp_item, prefix="lines")
        if form.is_valid() and line_formset.is_valid():
            with transaction.atomic():
                item = form.save(commit=False)
                item.owner = request.user
                item.project = project
                if locked_customer:
                    item.customer = locked_customer
                item.save()
                line_formset.instance = item
                line_items = line_formset.save(commit=False)
                for deleted in line_formset.deleted_objects:
                    deleted.delete()
                for idx, line in enumerate(line_items, start=1):
                    line.owner = request.user
                    line.quote = item
                    if not line.row_order:
                        line.row_order = idx
                    _apply_quote_vat_to_line(line, item)
                    line.save()
                _sync_quote_lines_vat(item)
                item.refresh_totals_from_lines(save=True)
                _sync_contact_from_customer(request.user, item.customer)
            return redirect(f"/projects/view?id={project.id}")
    else:
        form = QuoteForm(owner=request.user, initial=form_initial)
        temp_item = Quote(owner=request.user, project=project, customer=locked_customer)
        line_formset = QuoteLineFormSet(instance=temp_item, prefix="lines")

    return render(
        request,
        "finance_hub/quote_form.html",
        {
            "form": form,
            "line_formset": line_formset,
            "mode": "add",
            "vat_rates": _vat_rates_payload(request.user),
            "project_quote_mode": True,
            "locked_project": project,
            "locked_customer": locked_customer,
            "project_quote_back_url": f"/projects/view?id={project.id}",
            "price_lists_contact": price_lists_contact,
            "price_lists_payload": price_lists_payload,
        },
    )


@login_required
def project_detail(request):
    project_id = request.GET.get("id")
    if not project_id:
        return redirect("/projects/")

    project = get_object_or_404(Project, id=project_id, owner=request.user)

    from planner.models import PlannerItem
    from subscriptions.models import Subscription
    from transactions.models import Transaction
    from routines.models import RoutineItem

    planner_modal_open = False
    if request.method == "POST":
        action = (request.POST.get("action") or "").strip()
        if action == "add_project_planner_item":
            planner_quick_form = ProjectPlannerQuickForm(request.POST, owner=request.user)
            if planner_quick_form.is_valid():
                planner_item = planner_quick_form.save(commit=False)
                planner_item.owner = request.user
                planner_item.project = project
                planner_item.save()
                due = planner_item.due_date.strftime("%d/%m/%Y") if planner_item.due_date else "senza scadenza"
                note_parts = [
                    f"Promemoria creato: {planner_item.title}",
                    f"Scadenza: {due}",
                    f"Stato: {planner_item.get_status_display()}",
                ]
                if planner_item.note:
                    note_parts.append(f"Note: {planner_item.note}")
                ProjectNote.objects.create(
                    owner=request.user,
                    project=project,
                    content="<br>".join(note_parts),
                )
                return redirect(f"/projects/view?id={project.id}")
            planner_modal_open = True
        elif action == "update_project_planner_status":
            planner_item_id = request.POST.get("planner_item_id")
            status = (request.POST.get("status") or "").strip()
            allowed_status = {value for value, _label in PlannerItem.Status.choices}
            planner_item = get_object_or_404(
                PlannerItem,
                id=planner_item_id,
                owner=request.user,
                project=project,
            )
            if status in allowed_status and planner_item.status != status:
                planner_item.status = status
                planner_item.save(update_fields=["status", "updated_at"])
            return redirect(f"/projects/view?id={project.id}")
        elif action == "update_project_subscription_status":
            sub_id = request.POST.get("subscription_id")
            status = (request.POST.get("status") or "").strip()
            allowed_status = {value for value, _label in Subscription.Status.choices}
            subscription = get_object_or_404(
                Subscription,
                id=sub_id,
                owner=request.user,
                project=project,
            )
            if status in allowed_status and subscription.status != status:
                subscription.status = status
                subscription.save(update_fields=["status", "updated_at"])
            return redirect(f"/projects/view?id={project.id}")
        elif action == "update_project_subproject_status":
            subproject_id = request.POST.get("subproject_id")
            status = (request.POST.get("status") or "").strip()
            allowed_status = {value for value, _label in SubProject.Status.choices}
            subproject = get_object_or_404(
                SubProject,
                id=subproject_id,
                owner=request.user,
                project=project,
            )
            if status in allowed_status and subproject.status != status:
                subproject.status = status
                subproject.save(update_fields=["status", "updated_at"])
            return redirect(f"/projects/view?id={project.id}")
        else:
            planner_quick_form = ProjectPlannerQuickForm(owner=request.user)
    else:
        planner_quick_form = ProjectPlannerQuickForm(
            owner=request.user,
            initial={"status": PlannerItem.Status.PLANNED},
        )

    tx_qs = Transaction.objects.filter(owner=request.user, project=project)
    sub_qs = Subscription.objects.filter(owner=request.user, project=project)
    planner_qs = PlannerItem.objects.filter(owner=request.user, project=project)
    quote_qs = Quote.objects.filter(owner=request.user, project=project)
    routine_qs = RoutineItem.objects.filter(owner=request.user, project=project, is_active=True)
    subproject_qs = (
        SubProject.objects.filter(owner=request.user, project=project)
        .annotate(
            activities_total=Count("activities"),
            activities_done=Count(
                "activities",
                filter=Q(activities__status=SubProjectActivity.Status.DONE),
            ),
        )
        .order_by("is_archived", "due_date", "title")
    )

    override = ProjectHeroActionsConfig.objects.filter(user=request.user, project=project).first()
    override_config = override.config if override else {}
    module_key = "projects_detail"
    allowed_actions = _resolve_hero_actions(request.user, module_key, override_config)
    actions_meta = HERO_ACTIONS.get(module_key, [])
    hidden_actions = [
        {"key": action["key"], "label": action["label"]}
        for action in actions_meta
        if action["key"] not in allowed_actions
    ]
    context = {
        "project": project,
        "transactions": tx_qs.select_related("currency").order_by("-date", "-id")[:5],
        "subscriptions": sub_qs.select_related("currency").order_by("next_due_date", "id")[:5],
        "planner_items": planner_qs.order_by("due_date", "id")[:5],
        "quotes": quote_qs.select_related("currency", "customer").order_by("-issue_date", "-id")[:5],
        "routine_items": routine_qs.order_by("weekday", "time_start", "time_end", "title")[:5],
        "counts": {
            "transactions": tx_qs.count(),
            "subscriptions": sub_qs.count(),
            "planner_items": planner_qs.count(),
            "quotes": quote_qs.count(),
            "routine_items": routine_qs.count(),
            "subprojects": subproject_qs.count(),
        },
        "tx_type_counts": _choice_counts(tx_qs, "tx_type", Transaction.Type),
        "sub_status_counts": _choice_counts(sub_qs, "status", Subscription.Status),
        "planner_status_counts": _choice_counts(planner_qs, "status", PlannerItem.Status),
        "subprojects": subproject_qs[:6],
        "subproject_counts": _subproject_counts(subproject_qs),
        "planner_quick_form": planner_quick_form,
        "planner_modal_open": planner_modal_open,
        "hero_actions_override": override_config,
        "allowed_actions": allowed_actions,
        "hidden_actions": hidden_actions,
    }
    return render(request, "projects/project_detail.html", context)


@login_required
def add_subproject(request):
    project_id = request.GET.get("project") or request.POST.get("project_id")
    if not project_id:
        return redirect("/projects/")
    project = get_object_or_404(Project, id=project_id, owner=request.user)

    if request.method == "POST":
        form = SubProjectForm(request.POST)
        if form.is_valid():
            subproject = form.save(commit=False)
            subproject.owner = request.user
            subproject.project = project
            subproject.save()
            return redirect(f"/projects/subprojects/view?id={subproject.id}")
    else:
        form = SubProjectForm()

    return render(
        request,
        "projects/subproject_form.html",
        {
            "project": project,
            "form": form,
            "mode": "add",
        },
    )


@login_required
def update_subproject(request):
    subproject_id = request.GET.get("id") or request.POST.get("subproject_id")
    if not subproject_id:
        return redirect("/projects/")
    subproject = get_object_or_404(
        SubProject.objects.select_related("project"),
        id=subproject_id,
        owner=request.user,
    )

    if request.method == "POST":
        form = SubProjectForm(request.POST, instance=subproject)
        if form.is_valid():
            form.save()
            return redirect(f"/projects/subprojects/view?id={subproject.id}")
    else:
        form = SubProjectForm(instance=subproject)

    return render(
        request,
        "projects/subproject_form.html",
        {
            "project": subproject.project,
            "subproject": subproject,
            "form": form,
            "mode": "update",
        },
    )


@login_required
def subproject_detail(request):
    subproject_id = request.GET.get("id")
    if not subproject_id:
        return redirect("/projects/")
    subproject = get_object_or_404(
        SubProject.objects.select_related("project"),
        id=subproject_id,
        owner=request.user,
    )

    activity_form = SubProjectActivityForm(prefix="activity")
    if request.method == "POST":
        action = (request.POST.get("action") or "").strip()
        if action == "create_activity":
            activity_form = SubProjectActivityForm(request.POST, prefix="activity")
            if activity_form.is_valid():
                activity = activity_form.save(commit=False)
                activity.owner = request.user
                activity.subproject = subproject
                activity.save()
                return redirect(f"/projects/subprojects/view?id={subproject.id}")
        elif action == "update_activity_status":
            activity_id = request.POST.get("activity_id")
            status = (request.POST.get("status") or "").strip()
            allowed_status = {value for value, _label in SubProjectActivity.Status.choices}
            activity = get_object_or_404(
                SubProjectActivity,
                id=activity_id,
                owner=request.user,
                subproject=subproject,
            )
            if status in allowed_status and activity.status != status:
                activity.status = status
                activity.save(update_fields=["status", "updated_at"])
            return redirect(f"/projects/subprojects/view?id={subproject.id}")
        elif action == "remove_activity":
            activity_id = request.POST.get("activity_id")
            activity = get_object_or_404(
                SubProjectActivity,
                id=activity_id,
                owner=request.user,
                subproject=subproject,
            )
            activity.delete()
            return redirect(f"/projects/subprojects/view?id={subproject.id}")

    activities_qs = SubProjectActivity.objects.filter(owner=request.user, subproject=subproject).order_by("ordering", "id")
    context = {
        "subproject": subproject,
        "project": subproject.project,
        "activity_form": activity_form,
        "activities": activities_qs,
        "activity_status_choices": SubProjectActivity.Status.choices,
        "activity_status_counts": _choice_counts(activities_qs, "status", SubProjectActivity.Status),
    }
    return render(request, "projects/subproject_detail.html", context)


@login_required
def project_storyboard(request):
    project_id = request.GET.get("id")
    if not project_id:
        return redirect("/projects/")

    project = get_object_or_404(Project, id=project_id, owner=request.user)

    active_form = "note"
    if request.method == "POST":
        form_kind = (request.POST.get("form_kind") or "note").strip().lower()
        active_form = form_kind if form_kind in {"note", "task", "planner"} else "note"

        if active_form == "task":
            note_form = ProjectNoteForm()
            planner_form = StoryboardPlannerForm(prefix="planner")
            task_form = StoryboardTaskForm(request.POST, prefix="task")
            if task_form.is_valid():
                task = task_form.save(commit=False)
                task.owner = request.user
                task.project = project
                task.save()
                return redirect(f"/projects/storyboard?id={project.id}")
        elif active_form == "planner":
            note_form = ProjectNoteForm()
            task_form = StoryboardTaskForm(prefix="task")
            planner_form = StoryboardPlannerForm(request.POST, prefix="planner")
            if planner_form.is_valid():
                planner_item = planner_form.save(commit=False)
                planner_item.owner = request.user
                planner_item.project = project
                planner_item.save()
                return redirect(f"/projects/storyboard?id={project.id}")
        else:
            task_form = StoryboardTaskForm(prefix="task")
            planner_form = StoryboardPlannerForm(prefix="planner")
            note_form = ProjectNoteForm(request.POST, request.FILES)
            if note_form.is_valid():
                note = note_form.save(commit=False)
                note.owner = request.user
                note.project = project
                note.save()
                return redirect(f"/projects/storyboard?id={project.id}")
    else:
        note_form = ProjectNoteForm()
        task_form = StoryboardTaskForm(prefix="task")
        planner_form = StoryboardPlannerForm(prefix="planner")
    activity_filters = _storyboard_filters_from_request(request)
    activity_context = _build_storyboard_activity_context(request.user, project, activity_filters)
    override = ProjectHeroActionsConfig.objects.filter(user=request.user, project=project).first()
    override_config = override.config if override else {}
    module_key = "projects_storyboard"
    allowed_actions = _resolve_hero_actions(request.user, module_key, override_config)
    actions_meta = HERO_ACTIONS.get(module_key, [])
    hidden_actions = [
        {"key": action["key"], "label": action["label"]}
        for action in actions_meta
        if action["key"] not in allowed_actions
    ]
    context = {
        "project": project,
        "note_form": note_form,
        "task_form": task_form,
        "planner_form": planner_form,
        "active_form": active_form,
        "hero_actions_override": override_config,
        "allowed_actions": allowed_actions,
        "hidden_actions": hidden_actions,
    }
    context.update(activity_context)
    return render(request, "projects/storyboard.html", context)


@login_required
def project_storyboard_log(request):
    project_id = request.GET.get("id")
    if not project_id:
        return redirect("/projects/")

    project = get_object_or_404(Project, id=project_id, owner=request.user)
    activity_filters = _storyboard_filters_from_request(request)
    context = {"project": project}
    context.update(_build_storyboard_activity_context(request.user, project, activity_filters))
    return render(request, "projects/partials/storyboard_log.html", context)


@login_required
def project_storyboard_delete_note(request):
    if request.method != "POST":
        return redirect("/projects/")

    project_id = request.POST.get("id")
    note_id = request.POST.get("note_id")
    if not project_id or not note_id:
        return redirect("/projects/")

    project = get_object_or_404(Project, id=project_id, owner=request.user)
    note = get_object_or_404(ProjectNote, id=note_id, project=project, owner=request.user)
    note.delete()

    filters = _storyboard_filters_from_request(request)
    querystring = _storyboard_querystring(project.id, filters)
    return redirect(f"/projects/storyboard?{querystring}")


@login_required
def project_hero_actions(request):
    project_id = request.GET.get("id")
    if not project_id:
        return redirect("/projects/")
    project = get_object_or_404(Project, id=project_id, owner=request.user)
    config_obj, _ = ProjectHeroActionsConfig.objects.get_or_create(user=request.user, project=project)
    modules = {
        "projects_detail": HERO_ACTIONS.get("projects_detail", []),
        "projects_storyboard": HERO_ACTIONS.get("projects_storyboard", []),
    }
    if request.method == "POST":
        new_config = {}
        for module, actions in modules.items():
            enabled = []
            for action in actions:
                key = f"{module}:{action['key']}"
                if request.POST.get(key) == "on":
                    enabled.append(action["key"])
            new_config[module] = enabled
        new_config["_configured"] = True
        config_obj.config = new_config
        config_obj.save(update_fields=["config"])
        return redirect(f"/projects/view?id={project.id}")

    selected = config_obj.config or {}
    if selected and not selected.get("_configured"):
        for module, actions in modules.items():
            if module not in selected:
                selected[module] = [a["key"] for a in actions if a.get("default")]
        selected["_configured"] = True
        config_obj.config = selected
        config_obj.save(update_fields=["config"])

    context = {
        "project": project,
        "actions": modules,
        "selected": selected,
    }
    return render(request, "projects/hero_actions.html", context)


@login_required
def categories(request):
    categories_list = Category.objects.filter(owner=request.user).order_by("name")
    return render(request, "projects/categories.html", {"categories": categories_list})


@login_required
def add_category(request):
    if request.method == "POST":
        form = CategoryForm(request.POST, owner=request.user)
        if form.is_valid():
            category = form.save(commit=False)
            category.owner = request.user
            category.save()
            return redirect("/projects/categories/")
    else:
        form = CategoryForm(owner=request.user)
    return render(request, "projects/add_category.html", {"form": form})


@login_required
def update_category(request):
    category_id = request.GET.get("id")
    category = None
    if category_id:
        category = get_object_or_404(Category, id=category_id, owner=request.user)
        if request.method == "POST":
            form = CategoryForm(request.POST, instance=category, owner=request.user)
            if form.is_valid():
                form.save()
                return redirect("/projects/categories/")
        else:
            form = CategoryForm(instance=category, owner=request.user)
        return render(request, "projects/update_category.html", {"form": form, "category": category})
    categories_list = Category.objects.filter(owner=request.user).order_by("name")[:20]
    return render(request, "projects/update_category.html", {"categories": categories_list})


@login_required
def remove_category(request):
    category_id = request.GET.get("id")
    category = None
    if category_id:
        category = get_object_or_404(Category, id=category_id, owner=request.user)
        if request.method == "POST":
            category.delete()
            return redirect("/projects/categories/")
    categories_list = Category.objects.filter(owner=request.user).order_by("name")[:20]
    return render(request, "projects/remove_category.html", {"category": category, "categories": categories_list})
