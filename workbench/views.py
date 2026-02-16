from django.apps import apps
from django.conf import settings
from django.contrib.auth.decorators import login_required
from django.shortcuts import get_object_or_404, redirect, render

from .forms import WorkbenchItemForm
from .models import DebugChangeLog, WorkbenchItem

# Create your views here.
@login_required
def dashboard(request):
    logs = DebugChangeLog.objects.all().select_related("user").order_by("-created_at")[:5]
    counts = {
        "total_logs": DebugChangeLog.objects.count(),
    }
    return render(
        request,
        "workbench/dashboard.html",
        {
            "logs": logs,
            "counts": counts,
        },
    )


@login_required
def add_item(request):
    if request.method == "POST":
        form = WorkbenchItemForm(request.POST)
        if form.is_valid():
            item = form.save(commit=False)
            item.owner = request.user
            item.save()
            return redirect("/workbench/")
    else:
        form = WorkbenchItemForm()
    return render(request, "workbench/add_item.html", {"form": form})


@login_required
def remove_item(request):
    item_id = request.GET.get("id")
    item = None
    if item_id:
        item = get_object_or_404(WorkbenchItem, id=item_id, owner=request.user)
        if request.method == "POST":
            item.delete()
            return redirect("/workbench/")
    items = WorkbenchItem.objects.filter(owner=request.user).order_by("-created_at")[:20]
    return render(request, "workbench/remove_item.html", {"item": item, "items": items})


@login_required
def update_item(request):
    item_id = request.GET.get("id")
    item = None
    if item_id:
        item = get_object_or_404(WorkbenchItem, id=item_id, owner=request.user)
        if request.method == "POST":
            form = WorkbenchItemForm(request.POST, instance=item)
            if form.is_valid():
                form.save()
                return redirect("/workbench/")
        else:
            form = WorkbenchItemForm(instance=item)
        return render(request, "workbench/update_item.html", {"form": form, "item": item})
    items = WorkbenchItem.objects.filter(owner=request.user).order_by("-created_at")[:20]
    return render(request, "workbench/update_item.html", {"items": items})


@login_required
def debug_logs(request):
    return render(
        request,
        "workbench/debug_logs.html",
        {
            "logs": (
                DebugChangeLog.objects.all()
                .select_related("user")
                .order_by("-created_at")[:200]
            )
        },
    )


@login_required
def db_schema(request):
    allowed_apps = {
        app_label.split(".")[-1]
        for app_label in settings.INSTALLED_APPS
        if not app_label.startswith("django.")
    }
    model_map = {}
    models_info = []
    for model in apps.get_models():
        if model._meta.app_label not in allowed_apps:
            continue
        model_id = f"{model._meta.app_label}_{model.__name__}"
        model_map[model] = model_id
        fields = []
        for field in model._meta.get_fields():
            if field.auto_created and not field.concrete:
                continue
            if field.many_to_many:
                field_type = "ManyToMany"
            else:
                field_type = field.get_internal_type()
            fields.append(
                {
                    "name": field.name,
                    "type": field_type,
                    "null": getattr(field, "null", False),
                    "blank": getattr(field, "blank", False),
                    "relation": getattr(field, "is_relation", False),
                    "to": str(field.remote_field.model) if getattr(field, "remote_field", None) else "",
                }
            )
        models_info.append(
            {
                "app": model._meta.app_label,
                "name": model.__name__,
                "table": model._meta.db_table,
                "fields": fields,
            }
        )
    models_info.sort(key=lambda item: (item["app"], item["name"]))

    mermaid_lines = ["erDiagram"]
    entity_defs = []
    relations = set()

    for model, model_id in model_map.items():
        model_fields = []
        for field in model._meta.get_fields():
            if field.auto_created and not field.concrete:
                continue
            if field.many_to_many:
                field_type = "ManyToMany"
            else:
                field_type = field.get_internal_type()
            model_fields.append((field.name, field_type))
            if field.is_relation and field.remote_field and field.remote_field.model in model_map:
                target_id = model_map[field.remote_field.model]
                label = field.name
                if field.many_to_many:
                    relations.add((model_id, "}o--o{", target_id, label))
                elif field.one_to_one:
                    relations.add((model_id, "||--||", target_id, label))
                elif field.many_to_one:
                    relations.add((target_id, "||--o{", model_id, label))
        entity_defs.append((model_id, model_fields))

    for model_id, model_fields in sorted(entity_defs, key=lambda item: item[0]):
        mermaid_lines.append(f"  {model_id} {{")
        for field_name, field_type in model_fields:
            mermaid_lines.append(f"    {field_type} {field_name}")
        mermaid_lines.append("  }")

    for left, card, right, label in sorted(relations):
        mermaid_lines.append(f"  {left} {card} {right} : {label}")

    mermaid_erd = "\n".join(mermaid_lines)
    return render(
        request,
        "workbench/db_schema.html",
        {"models": models_info, "mermaid_erd": mermaid_erd},
    )
