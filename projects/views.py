from django.contrib.auth.decorators import login_required
from django.db.models import Count
from django.shortcuts import get_object_or_404, redirect, render

from .category_forms import CategoryForm
from .customer_forms import CustomerForm
from .note_forms import ProjectNoteForm
from .forms import ProjectForm
from .models import Category, Customer, Project, ProjectNote, ProjectHeroActionsConfig
from core.hero_actions import HERO_ACTIONS
from core.models import UserHeroActionsConfig

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


# Create your views here.
@login_required
def dashboard(request):
    user = request.user
    active_projects = Project.objects.filter(owner=user, is_archived=False).order_by("name")[:5]
    counts = {
        "active": Project.objects.filter(owner=user, is_archived=False).count(),
        "archived": Project.objects.filter(owner=user, is_archived=True).count(),
        "categories": Category.objects.filter(owner=user).count(),
    }
    return render(
        request,
        "projects/dashboard.html",
        {
            "active_projects": active_projects,
            "counts": counts,
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
def project_detail(request):
    project_id = request.GET.get("id")
    if not project_id:
        return redirect("/projects/")

    project = get_object_or_404(Project, id=project_id, owner=request.user)

    from planner.models import PlannerItem
    from subscriptions.models import Subscription
    from transactions.models import Transaction
    from routines.models import RoutineItem

    tx_qs = Transaction.objects.filter(owner=request.user, project=project)
    sub_qs = Subscription.objects.filter(owner=request.user, project=project)
    planner_qs = PlannerItem.objects.filter(owner=request.user, project=project)
    routine_qs = RoutineItem.objects.filter(owner=request.user, project=project, is_active=True)

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
        "routine_items": routine_qs.order_by("weekday", "time_start", "time_end", "title")[:5],
        "counts": {
            "transactions": tx_qs.count(),
            "subscriptions": sub_qs.count(),
            "planner_items": planner_qs.count(),
            "routine_items": routine_qs.count(),
        },
        "tx_type_counts": _choice_counts(tx_qs, "tx_type", Transaction.Type),
        "sub_status_counts": _choice_counts(sub_qs, "status", Subscription.Status),
        "planner_status_counts": _choice_counts(planner_qs, "status", PlannerItem.Status),
        "hero_actions_override": override_config,
        "allowed_actions": allowed_actions,
        "hidden_actions": hidden_actions,
    }
    return render(request, "projects/project_detail.html", context)


@login_required
def project_storyboard(request):
    project_id = request.GET.get("id")
    if not project_id:
        return redirect("/projects/")

    project = get_object_or_404(Project, id=project_id, owner=request.user)

    if request.method == "POST":
        note_form = ProjectNoteForm(request.POST, request.FILES)
        if note_form.is_valid():
            note = note_form.save(commit=False)
            note.owner = request.user
            note.project = project
            note.save()
            return redirect(f"/projects/storyboard?id={project.id}")
    else:
        note_form = ProjectNoteForm()

    from planner.models import PlannerItem
    from transactions.models import Transaction

    transactions = (
        Transaction.objects.filter(owner=request.user, project=project)
        .select_related("currency", "payee", "income_source")
        .order_by("-date", "-id")[:50]
    )
    planner_items = (
        PlannerItem.objects.filter(owner=request.user, project=project)
        .order_by("-due_date", "-created_at", "-id")[:50]
    )

    actions = []
    for tx in transactions:
        label = f"{tx.get_tx_type_display()} · {tx.amount} {tx.currency.code}"
        if tx.payee:
            label = f"{label} · {tx.payee.name}"
        elif tx.income_source:
            label = f"{label} · {tx.income_source.name}"
        actions.append({
            "date": tx.date,
            "title": "Transazione",
            "label": label,
            "note": tx.note,
        })

    for item in planner_items:
        date = item.due_date or item.created_at.date()
        actions.append({
            "date": date,
            "title": "Planner",
            "label": f"{item.title} · {item.get_status_display()}",
            "note": item.note,
        })

    actions.sort(key=lambda row: row["date"], reverse=True)

    notes = (
        ProjectNote.objects.filter(owner=request.user, project=project)
        .order_by("-created_at")
    )
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
        "notes": notes,
        "actions": actions,
        "hero_actions_override": override_config,
        "allowed_actions": allowed_actions,
        "hidden_actions": hidden_actions,
    }
    return render(request, "projects/storyboard.html", context)


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
def customers(request):
    customers_list = Customer.objects.filter(owner=request.user).order_by("name")
    return render(request, "projects/customers.html", {"customers": customers_list})


@login_required
def add_customer(request):
    if request.method == "POST":
        form = CustomerForm(request.POST)
        if form.is_valid():
            customer = form.save(commit=False)
            customer.owner = request.user
            customer.save()
            return redirect("/projects/customers/")
    else:
        form = CustomerForm()
    return render(request, "projects/add_customer.html", {"form": form})


@login_required
def update_customer(request):
    customer_id = request.GET.get("id")
    customer = None
    if customer_id:
        customer = get_object_or_404(Customer, id=customer_id, owner=request.user)
        if request.method == "POST":
            form = CustomerForm(request.POST, instance=customer)
            if form.is_valid():
                form.save()
                return redirect("/projects/customers/")
        else:
            form = CustomerForm(instance=customer)
        return render(request, "projects/update_customer.html", {"form": form, "customer": customer})
    customers_list = Customer.objects.filter(owner=request.user).order_by("name")[:20]
    return render(request, "projects/update_customer.html", {"customers": customers_list})


@login_required
def remove_customer(request):
    customer_id = request.GET.get("id")
    customer = None
    if customer_id:
        customer = get_object_or_404(Customer, id=customer_id, owner=request.user)
        if request.method == "POST":
            customer.delete()
            return redirect("/projects/customers/")
    customers_list = Customer.objects.filter(owner=request.user).order_by("name")[:20]
    return render(request, "projects/remove_customer.html", {"customer": customer, "customers": customers_list})


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
