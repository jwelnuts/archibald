import json
import os
import urllib.error
import urllib.request
from importlib.util import find_spec

from django.apps import apps
from django.conf import settings
from django.contrib.auth.decorators import login_required
from django.db import connection
from django.db.migrations.loader import MigrationLoader
from django.http import HttpResponseForbidden
from django.shortcuts import get_object_or_404, redirect, render
from django.urls import Resolver404, resolve

from .app_builder import AppBuilderError, generate_app_from_prompt
from .forms import AppGeneratorForm, WorkbenchItemForm
from .models import DebugChangeLog, WorkbenchItem


def _group_migrations_by_app():
    try:
        loader = MigrationLoader(connection, ignore_no_migrations=True)
    except Exception as exc:
        return {}, {}, str(exc)

    disk_by_app = {}
    applied_by_app = {}
    for app_label, migration_name in loader.disk_migrations:
        disk_by_app.setdefault(app_label, set()).add(migration_name)
    for app_label, migration_name in loader.applied_migrations:
        applied_by_app.setdefault(app_label, set()).add(migration_name)
    return disk_by_app, applied_by_app, ""


def _severity_to_ui(severity):
    if severity == "error":
        return "ERRORE", "dot-red", "health-pill error"
    if severity == "warn":
        return "ATTENZIONE", "dot-amber", "health-pill warn"
    return "OK", "dot-green", "health-pill ok"


def _analyze_generated_app(
    app_label,
    model_name,
    created_at,
    *,
    installed_labels,
    disk_migrations_by_app,
    applied_migrations_by_app,
    migration_state_error,
    table_names,
    table_lookup_error,
):
    app_url = f"/{app_label}/"
    app_path = settings.BASE_DIR / app_label
    alarms = []
    severity = "ok"

    def raise_level(level, message):
        nonlocal severity
        alarms.append({"level": level, "message": message})
        if level == "error":
            severity = "error"
        elif level == "warn" and severity != "error":
            severity = "warn"

    in_settings = app_label in installed_labels
    install_status = "OK"
    if not app_path.exists():
        install_status = "Cartella assente"
        raise_level("error", f"Cartella app mancante: {app_path}")
    elif find_spec(app_label) is None:
        install_status = "Import KO"
        raise_level("error", "Modulo Python non importabile.")
    elif not in_settings:
        install_status = "Non in INSTALLED_APPS"
        raise_level("error", "App non registrata in INSTALLED_APPS.")

    route_status = "OK"
    try:
        resolve(app_url)
    except Resolver404:
        route_status = "Route mancante"
        raise_level("error", "Route non trovata in project urls.")

    if migration_state_error:
        migration_status = "Verifica non disponibile"
        raise_level("warn", f"Impossibile leggere stato migrazioni: {migration_state_error}")
    else:
        disk = disk_migrations_by_app.get(app_label, set())
        applied = applied_migrations_by_app.get(app_label, set())
        pending = sorted(disk - applied)
        if not disk:
            migration_status = "Nessuna migration"
            raise_level("warn", "Manca almeno una migration dell'app.")
        elif pending:
            migration_status = f"{len(pending)} pending"
            raise_level("warn", f"Migrazioni non applicate: {', '.join(pending)}")
        else:
            migration_status = "Allineate"

    app_models = [
        model
        for model in apps.get_models()
        if model._meta.app_label == app_label and model._meta.managed and not model._meta.proxy
    ]
    if table_lookup_error:
        tables_status = "Verifica non disponibile"
        raise_level("warn", f"Impossibile leggere tabelle DB: {table_lookup_error}")
    elif not app_models:
        tables_status = "Nessun model"
        raise_level("warn", "Nessun model gestito trovato per questa app.")
    else:
        missing_tables = [model._meta.db_table for model in app_models if model._meta.db_table not in table_names]
        if missing_tables:
            tables_status = f"Mancano {len(missing_tables)} tabelle"
            raise_level("error", f"Tabelle mancanti: {', '.join(missing_tables)}")
        else:
            tables_status = "OK"

    action_hint = "Pronta all'uso."
    if any("Tabelle mancanti" in alarm["message"] for alarm in alarms) or any(
        "Migrazioni" in alarm["message"] or "migration" in alarm["message"] for alarm in alarms
    ):
        action_hint = f"Esegui: python manage.py makemigrations {app_label} && python manage.py migrate"
    elif any("INSTALLED_APPS" in alarm["message"] for alarm in alarms):
        action_hint = f"Aggiungi '{app_label}' in INSTALLED_APPS."
    elif any("Route non trovata" in alarm["message"] for alarm in alarms):
        action_hint = f"Aggiungi include urls per '{app_label}' in mio_master/urls.py."
    elif any("importabile" in alarm["message"] for alarm in alarms):
        action_hint = "Controlla struttura app e file __init__.py."

    health_label, dot_class, pill_class = _severity_to_ui(severity)
    checks = [
        {"label": "Installazione", "value": install_status},
        {"label": "Route", "value": route_status},
        {"label": "Migrazioni", "value": migration_status},
        {"label": "Tabelle", "value": tables_status},
    ]
    return {
        "app_label": app_label,
        "model_name": model_name or "-",
        "url": app_url,
        "created_at": created_at,
        "severity": severity,
        "health_label": health_label,
        "dot_class": dot_class,
        "pill_class": pill_class,
        "checks": checks,
        "alarms": alarms,
        "action_hint": action_hint,
    }


# Create your views here.
@login_required
def dashboard(request):
    all_logs = DebugChangeLog.objects.all().select_related("user").order_by("-created_at")
    logs = all_logs[:8]
    app_build_history = all_logs.filter(source="workbench.ai_app_generator")
    app_build_logs = app_build_history[:6]
    installed_labels = {entry.split(".")[-1] for entry in settings.INSTALLED_APPS}
    disk_migrations_by_app, applied_migrations_by_app, migration_state_error = _group_migrations_by_app()
    table_names = set()
    table_lookup_error = ""
    try:
        table_names = set(connection.introspection.table_names())
    except Exception as exc:
        table_lookup_error = str(exc)

    generated_apps = []
    seen_apps = set()
    for log in app_build_history:
        app_label = (log.app_label or "").strip()
        if not app_label or app_label in seen_apps:
            continue
        seen_apps.add(app_label)
        generated_apps.append(
            _analyze_generated_app(
                app_label=app_label,
                model_name=log.model_name,
                created_at=log.created_at,
                installed_labels=installed_labels,
                disk_migrations_by_app=disk_migrations_by_app,
                applied_migrations_by_app=applied_migrations_by_app,
                migration_state_error=migration_state_error,
                table_names=table_names,
                table_lookup_error=table_lookup_error,
            )
        )

    generated_error = sum(1 for app in generated_apps if app["severity"] == "error")
    generated_warn = sum(1 for app in generated_apps if app["severity"] == "warn")
    generated_ok = sum(1 for app in generated_apps if app["severity"] == "ok")
    pipeline_alerts = []
    if generated_error:
        pipeline_alerts.append(
            {
                "dot_class": "dot-red",
                "message": f"{generated_error} app generate con errori bloccanti.",
            }
        )
    if generated_warn:
        pipeline_alerts.append(
            {
                "dot_class": "dot-amber",
                "message": f"{generated_warn} app generate con avvisi operativi.",
            }
        )
    if not generated_apps:
        pipeline_alerts.append(
            {
                "dot_class": "dot-blue",
                "message": "Nessuna app generata trovata nei log.",
            }
        )

    gpt_enabled = bool(os.getenv("OPENAI_API_KEY", "").strip())
    if not gpt_enabled:
        pipeline_alerts.append(
            {
                "dot_class": "dot-amber",
                "message": "OPENAI_API_KEY non configurata: generatori AI disabilitati.",
            }
        )

    if migration_state_error:
        pipeline_alerts.append(
            {
                "dot_class": "dot-red",
                "message": f"Verifica migrazioni non disponibile: {migration_state_error}",
            }
        )
    if table_lookup_error:
        pipeline_alerts.append(
            {
                "dot_class": "dot-amber",
                "message": f"Verifica tabelle DB non disponibile: {table_lookup_error}",
            }
        )

    counts = {
        "total_logs": DebugChangeLog.objects.count(),
        "app_builds": DebugChangeLog.objects.filter(
            source="workbench.ai_app_generator"
        ).count(),
        "gpt_enabled": gpt_enabled,
        "generated_ok": generated_ok,
        "generated_warn": generated_warn,
        "generated_error": generated_error,
    }
    archibald_prompt_suggestions = [
        "Progetta un pannello giornaliero personale con KPI, priorita e checklist azioni.",
        "Definisci i campi minimi per un'app di gestione ticket interni con priorita e scadenze.",
        "Prepara un JSON UI pronto per un pannello weekly review con filtri e metriche.",
        "Genera una checklist tecnica per creare una nuova app Django e validarla prima del deploy.",
    ]
    return render(
        request,
        "workbench/dashboard.html",
        {
            "logs": logs,
            "app_build_logs": app_build_logs,
            "generated_apps": generated_apps,
            "pipeline_alerts": pipeline_alerts,
            "counts": counts,
            "archibald_prompt_suggestions": archibald_prompt_suggestions,
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
def ai_app_generator(request):
    if not request.user.is_superuser:
        return HttpResponseForbidden("Solo utenti superuser possono generare nuove app.")

    result = None
    error = None
    if request.method == "POST":
        form = AppGeneratorForm(request.POST)
        if form.is_valid():
            try:
                result = generate_app_from_prompt(
                    app_name=form.cleaned_data["app_name"],
                    prompt=form.cleaned_data["prompt"],
                )
                DebugChangeLog.objects.create(
                    user=request.user,
                    source="workbench.ai_app_generator",
                    action=DebugChangeLog.Action.CUSTOM,
                    app_label=result.app_name,
                    model_name=result.model_name,
                    object_id="-",
                    note=(
                        f"Created app at {result.app_path}. "
                        f"Files: {', '.join(result.created_files)}"
                    )[:2000],
                )
            except AppBuilderError as exc:
                error = str(exc)
    else:
        form = AppGeneratorForm()

    return render(
        request,
        "workbench/ai_app_generator.html",
        {
            "form": form,
            "result": result,
            "error": error,
        },
    )


@login_required
def ai_ui_generator(request):
    context = {"gpt_response": None, "gpt_error": None, "gpt_prompt": ""}

    if request.method == "POST":
        prompt = (request.POST.get("gpt_prompt") or "").strip()
        context["gpt_prompt"] = prompt

        if not prompt:
            context["gpt_error"] = "Inserisci una richiesta valida."
            return render(request, "workbench/ai_ui_generator.html", context)

        api_key = os.getenv("OPENAI_API_KEY")
        if not api_key:
            context["gpt_error"] = "OPENAI_API_KEY non configurata nell'ambiente."
            return render(request, "workbench/ai_ui_generator.html", context)

        model = os.getenv("OPENAI_MODEL", "gpt-4o-mini")
        payload = {
            "model": model,
            "instructions": (
                "Sei un generatore di UI. Rispondi solo con JSON valido "
                "e nessun testo extra."
            ),
            "input": [
                {
                    "role": "user",
                    "content": prompt,
                }
            ],
        }

        req = urllib.request.Request(
            "https://api.openai.com/v1/responses",
            data=json.dumps(payload).encode("utf-8"),
            headers={
                "Content-Type": "application/json",
                "Authorization": f"Bearer {api_key}",
            },
            method="POST",
        )

        try:
            with urllib.request.urlopen(req, timeout=60) as response:
                raw = response.read().decode("utf-8")
                data = json.loads(raw)
                context["gpt_response"] = json.dumps(
                    data, indent=2, ensure_ascii=False
                )
        except urllib.error.HTTPError as exc:
            try:
                error_body = exc.read().decode("utf-8")
            except Exception:
                error_body = ""
            context["gpt_error"] = (
                f"Errore API OpenAI ({exc.code}). {error_body}"
            ).strip()
        except urllib.error.URLError as exc:
            context["gpt_error"] = f"Errore di rete: {exc.reason}"
        except json.JSONDecodeError:
            context["gpt_error"] = "Risposta non JSON valida."
        except Exception as exc:
            context["gpt_error"] = f"Errore inatteso: {exc}"

    return render(request, "workbench/ai_ui_generator.html", context)


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
