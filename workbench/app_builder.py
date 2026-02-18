from __future__ import annotations

import json
import keyword
import os
import re
import urllib.error
import urllib.request
from dataclasses import dataclass, field
from pathlib import Path

from django.conf import settings


APP_NAME_RE = re.compile(r"^[a-z][a-z0-9_]{1,39}$")
NAME_RE = re.compile(r"^[a-z][a-z0-9_]{0,39}$")
MODEL_RE = re.compile(r"^[A-Z][A-Za-z0-9]{1,39}$")
SUPPORTED_FIELD_KINDS = {"char", "text", "integer", "decimal", "date", "datetime", "boolean", "choice"}


class AppBuilderError(Exception):
    """Errore controllato durante la generazione di una app Django."""


@dataclass
class FieldSpec:
    name: str
    kind: str
    required: bool = False
    choices: list[str] = field(default_factory=list)


@dataclass
class AppSpec:
    app_title: str
    model_name: str
    model_plural: str
    description: str
    fields: list[FieldSpec]


@dataclass
class AppBuildResult:
    app_name: str
    app_path: Path
    summary: str
    model_name: str
    created_files: list[str]
    used_gpt: bool
    warnings: list[str]
    settings_updated: bool
    urls_updated: bool


def generate_app_from_prompt(app_name: str, prompt: str) -> AppBuildResult:
    normalized_name = normalize_app_name(app_name)
    target_dir = settings.BASE_DIR / normalized_name
    if target_dir.exists():
        raise AppBuilderError(f"La cartella dell'app esiste gia: {target_dir}")

    spec, used_gpt, warnings = build_app_spec(normalized_name, prompt)
    files = build_app_files(normalized_name, spec)
    created_files = write_app_files(target_dir, files)

    settings_updated = ensure_app_in_settings(normalized_name)
    urls_updated = ensure_app_in_project_urls(normalized_name)

    return AppBuildResult(
        app_name=normalized_name,
        app_path=target_dir,
        summary=spec.description,
        model_name=spec.model_name,
        created_files=created_files,
        used_gpt=used_gpt,
        warnings=warnings,
        settings_updated=settings_updated,
        urls_updated=urls_updated,
    )


def normalize_app_name(raw_name: str) -> str:
    name = (raw_name or "").strip().lower().replace("-", "_")
    name = re.sub(r"[^a-z0-9_]", "", name)
    if not APP_NAME_RE.match(name):
        raise AppBuilderError(
            "Nome app non valido. Usa solo lettere minuscole, numeri e underscore (es: report_builder)."
        )
    if keyword.iskeyword(name):
        raise AppBuilderError("Il nome app coincide con una keyword Python.")

    installed_labels = {entry.split(".")[-1] for entry in settings.INSTALLED_APPS}
    if name in installed_labels:
        raise AppBuilderError(f"L'app '{name}' e gia presente in INSTALLED_APPS.")

    return name


def build_app_spec(app_name: str, prompt: str) -> tuple[AppSpec, bool, list[str]]:
    warnings: list[str] = []
    prompt = (prompt or "").strip()
    if not prompt:
        raise AppBuilderError("Inserisci una descrizione funzionale dell'app.")

    try:
        raw_spec = request_openai_spec(app_name, prompt)
        spec = parse_spec(raw_spec, app_name)
        return spec, True, warnings
    except AppBuilderError as exc:
        warnings.append(str(exc))
        fallback = parse_spec(heuristic_spec(app_name, prompt), app_name)
        return fallback, False, warnings


def request_openai_spec(app_name: str, prompt: str) -> dict:
    api_key = os.getenv("OPENAI_API_KEY", "").strip()
    if not api_key:
        raise AppBuilderError("OPENAI_API_KEY non configurata: uso fallback locale.")

    model = os.getenv("OPENAI_MODEL", "gpt-4o-mini")
    instructions = (
        "Sei un generatore di specifiche per app Django. "
        "Rispondi SOLO con JSON valido senza markdown. "
        "Schema richiesto: "
        "{"
        '"app_title": string, '
        '"description": string, '
        '"model_name": string (PascalCase), '
        '"model_plural": string, '
        '"fields": [ '
        "{"
        '"name": string snake_case, '
        '"kind": one of [char,text,integer,decimal,date,datetime,boolean,choice], '
        '"required": boolean, '
        '"choices": [string] opzionale solo per kind=choice'
        "}"
        "]"
        "}. "
        "Limiti: massimo 6 campi. Mantieni campi semplici e utili. "
        "Almeno un campo deve essere obbligatorio."
    )

    payload = {
        "model": model,
        "instructions": instructions,
        "input": [
            {
                "role": "user",
                "content": (
                    f"Nome app richiesto: {app_name}\n"
                    f"Richiesta utente:\n{prompt}\n"
                    "Genera la specifica."
                ),
            }
        ],
    }

    req = urllib.request.Request(
        "https://api.openai.com/v1/responses",
        data=json.dumps(payload).encode("utf-8"),
        headers={
            "Authorization": f"Bearer {api_key}",
            "Content-Type": "application/json",
        },
        method="POST",
    )

    try:
        with urllib.request.urlopen(req, timeout=90) as resp:
            body = resp.read().decode("utf-8")
            data = json.loads(body)
    except urllib.error.HTTPError as exc:
        detail = exc.read().decode("utf-8") if exc.fp else ""
        raise AppBuilderError(f"Errore API OpenAI ({exc.code}): {detail}") from exc
    except urllib.error.URLError as exc:
        raise AppBuilderError(f"Errore rete OpenAI: {exc.reason}") from exc
    except json.JSONDecodeError as exc:
        raise AppBuilderError(f"Risposta API non JSON: {exc}") from exc

    text = extract_output_text(data)
    if not text:
        raise AppBuilderError("Risposta OpenAI vuota.")

    try:
        parsed = json.loads(text)
    except json.JSONDecodeError as exc:
        compact = text[:400].replace("\n", " ")
        raise AppBuilderError(f"JSON OpenAI non valido: {compact}") from exc

    if not isinstance(parsed, dict):
        raise AppBuilderError("Il JSON OpenAI non e un oggetto.")
    return parsed


def extract_output_text(data: dict) -> str:
    if not isinstance(data, dict):
        return ""
    direct = data.get("output_text")
    if isinstance(direct, str) and direct.strip():
        return direct.strip()

    for item in data.get("output", []):
        if not isinstance(item, dict):
            continue
        if item.get("type") != "message":
            continue
        for block in item.get("content", []):
            if not isinstance(block, dict):
                continue
            if block.get("type") in {"output_text", "text"}:
                text = block.get("text", "")
                if isinstance(text, str) and text.strip():
                    return text.strip()
    return ""


def heuristic_spec(app_name: str, prompt: str) -> dict:
    lowered = prompt.lower()
    fields = [
        {"name": "title", "kind": "char", "required": True},
    ]

    if any(word in lowered for word in ("stato", "status", "fase", "workflow")):
        fields.append(
            {
                "name": "status",
                "kind": "choice",
                "required": True,
                "choices": ["TODO", "IN_PROGRESS", "DONE"],
            }
        )
    if any(word in lowered for word in ("importo", "amount", "budget", "costo", "prezzo")):
        fields.append({"name": "amount", "kind": "decimal", "required": False})
    if any(word in lowered for word in ("data", "deadline", "scadenza", "due")):
        fields.append({"name": "due_date", "kind": "date", "required": False})

    fields.append({"name": "notes", "kind": "text", "required": False})

    return {
        "app_title": app_name.replace("_", " ").title(),
        "description": f"App generata da prompt: {prompt[:120]}",
        "model_name": snake_to_pascal(app_name.rstrip("s") or app_name),
        "model_plural": app_name.replace("_", " ").title(),
        "fields": fields[:6],
    }


def parse_spec(raw_spec: dict, app_name: str) -> AppSpec:
    app_title = str(raw_spec.get("app_title") or app_name.replace("_", " ").title()).strip()
    description = str(raw_spec.get("description") or f"Gestione {app_title}").strip()

    model_name_raw = str(raw_spec.get("model_name") or snake_to_pascal(app_name)).strip()
    model_name = sanitize_model_name(model_name_raw)
    model_plural = str(raw_spec.get("model_plural") or f"{model_name}s").strip()

    fields_raw = raw_spec.get("fields", [])
    if not isinstance(fields_raw, list):
        fields_raw = []

    fields: list[FieldSpec] = []
    seen_names: set[str] = set()

    for entry in fields_raw[:8]:
        if not isinstance(entry, dict):
            continue
        raw_name = str(entry.get("name") or "").strip().lower().replace("-", "_")
        field_name = re.sub(r"[^a-z0-9_]", "", raw_name)
        if not NAME_RE.match(field_name):
            continue
        if keyword.iskeyword(field_name) or field_name in {"id", "owner", "created_at", "updated_at"}:
            continue

        kind = str(entry.get("kind") or "char").strip().lower()
        if kind not in SUPPORTED_FIELD_KINDS:
            continue

        if field_name in seen_names:
            continue
        seen_names.add(field_name)

        required = bool(entry.get("required", False))
        choices: list[str] = []
        if kind == "choice":
            raw_choices = entry.get("choices", [])
            if isinstance(raw_choices, list):
                for choice in raw_choices[:8]:
                    text = str(choice).strip().upper().replace(" ", "_")
                    text = re.sub(r"[^A-Z0-9_]", "", text)
                    if text:
                        choices.append(text)
            if not choices:
                choices = ["OPEN", "DONE"]
        fields.append(FieldSpec(name=field_name, kind=kind, required=required, choices=choices))

    if not fields:
        fields = [
            FieldSpec(name="title", kind="char", required=True),
            FieldSpec(name="notes", kind="text", required=False),
        ]

    if not any(field.required for field in fields):
        fields[0].required = True

    if len(fields) > 6:
        fields = fields[:6]

    return AppSpec(
        app_title=app_title,
        model_name=model_name,
        model_plural=model_plural,
        description=description,
        fields=fields,
    )


def sanitize_model_name(raw_name: str) -> str:
    if MODEL_RE.match(raw_name):
        return raw_name
    cleaned = re.sub(r"[^A-Za-z0-9]", "", raw_name)
    if not cleaned:
        return "Item"
    repaired = cleaned[0].upper() + cleaned[1:]
    if not MODEL_RE.match(repaired):
        return "Item"
    return repaired


def snake_to_pascal(name: str) -> str:
    parts = [chunk for chunk in name.replace("-", "_").split("_") if chunk]
    if not parts:
        return "Item"
    return "".join(chunk[:1].upper() + chunk[1:] for chunk in parts)


def build_app_files(app_name: str, spec: AppSpec) -> dict[str, str]:
    model_fields = build_model_fields(spec.fields)
    filter_fields = ", ".join([f'"{field.name}"' for field in spec.fields])

    model_main_label = spec.fields[0].name

    models_py_lines = [
        "from django.db import models",
        "",
        "from common.models import OwnedModel, TimeStampedModel",
        "",
        "",
        f"class {spec.model_name}(OwnedModel, TimeStampedModel):",
    ]
    models_py_lines.extend(model_fields)
    models_py_lines.extend(
        [
            "",
            "    class Meta:",
            "        indexes = [",
            "            models.Index(fields=[\"owner\", \"created_at\"]),",
            "        ]",
            "",
            "    def __str__(self):",
            f"        return str(self.{model_main_label})",
            "",
        ]
    )
    models_py = "\n".join(models_py_lines)

    forms_py = (
        "from django import forms\n"
        "\n"
        f"from .models import {spec.model_name}\n"
        "\n"
        "\n"
        f"class {spec.model_name}Form(forms.ModelForm):\n"
        "    class Meta:\n"
        f"        model = {spec.model_name}\n"
        f"        fields = ({filter_fields},)\n"
    )

    views_py = (
        "from django.contrib.auth.decorators import login_required\n"
        "from django.shortcuts import get_object_or_404, redirect, render\n"
        "\n"
        f"from .forms import {spec.model_name}Form\n"
        f"from .models import {spec.model_name}\n"
        "\n"
        "\n"
        "def _format_value(value):\n"
        "    if value is None:\n"
        "        return \"-\"\n"
        "    if hasattr(value, \"isoformat\"):\n"
        "        try:\n"
        "            return value.isoformat()\n"
        "        except Exception:\n"
        "            return str(value)\n"
        "    return str(value)\n"
        "\n"
        "\n"
        "@login_required\n"
        "def dashboard(request):\n"
        f"    queryset = {spec.model_name}.objects.filter(owner=request.user).order_by(\"-created_at\")[:50]\n"
        f"    display_fields = [{filter_fields}]\n"
        "    rows = [\n"
        "        {\n"
        "            \"id\": item.id,\n"
        "            \"values\": [_format_value(getattr(item, field, None)) for field in display_fields],\n"
        "        }\n"
        "        for item in queryset\n"
        "    ]\n"
        "    return render(\n"
        "        request,\n"
        f"        \"{app_name}/dashboard.html\",\n"
        "        {\n"
        "            \"rows\": rows,\n"
        "            \"display_fields\": display_fields,\n"
        "        },\n"
        "    )\n"
        "\n"
        "\n"
        "@login_required\n"
        "def add_item(request):\n"
        "    if request.method == \"POST\":\n"
        f"        form = {spec.model_name}Form(request.POST)\n"
        "        if form.is_valid():\n"
        "            item = form.save(commit=False)\n"
        "            item.owner = request.user\n"
        "            item.save()\n"
        f"            return redirect(\"/{app_name}/\")\n"
        "    else:\n"
        f"        form = {spec.model_name}Form()\n"
        f"    return render(request, \"{app_name}/add_item.html\", {{\"form\": form}})\n"
        "\n"
        "\n"
        "@login_required\n"
        "def update_item(request):\n"
        "    item_id = request.GET.get(\"id\")\n"
        "    if not item_id:\n"
        f"        return redirect(\"/{app_name}/\")\n"
        f"    item = get_object_or_404({spec.model_name}, id=item_id, owner=request.user)\n"
        "    if request.method == \"POST\":\n"
        f"        form = {spec.model_name}Form(request.POST, instance=item)\n"
        "        if form.is_valid():\n"
        "            form.save()\n"
        f"            return redirect(\"/{app_name}/\")\n"
        "    else:\n"
        f"        form = {spec.model_name}Form(instance=item)\n"
        "    return render(\n"
        "        request,\n"
        f"        \"{app_name}/update_item.html\",\n"
        "        {\n"
        "            \"form\": form,\n"
        "            \"item\": item,\n"
        "        },\n"
        "    )\n"
        "\n"
        "\n"
        "@login_required\n"
        "def remove_item(request):\n"
        "    item_id = request.GET.get(\"id\")\n"
        "    if not item_id:\n"
        f"        return redirect(\"/{app_name}/\")\n"
        f"    item = get_object_or_404({spec.model_name}, id=item_id, owner=request.user)\n"
        "    if request.method == \"POST\":\n"
        "        item.delete()\n"
        f"        return redirect(\"/{app_name}/\")\n"
        "    return render(\n"
        "        request,\n"
        f"        \"{app_name}/remove_item.html\",\n"
        "        {\"item\": item},\n"
        "    )\n"
    )

    urls_py = (
        "from django.urls import path\n"
        "\n"
        "from . import views\n"
        "\n"
        "urlpatterns = [\n"
        "    path(\"\", views.dashboard, name=\"" + app_name + "-dashboard\"),\n"
        "    path(\"api/add\", views.add_item, name=\"" + app_name + "-add\"),\n"
        "    path(\"api/update\", views.update_item, name=\"" + app_name + "-update\"),\n"
        "    path(\"api/remove\", views.remove_item, name=\"" + app_name + "-remove\"),\n"
        "]\n"
    )

    apps_py = (
        "from django.apps import AppConfig\n"
        "\n"
        "\n"
        f"class {snake_to_pascal(app_name)}Config(AppConfig):\n"
        "    default_auto_field = \"django.db.models.BigAutoField\"\n"
        f"    name = \"{app_name}\"\n"
    )

    admin_py = (
        "from django.contrib import admin\n"
        "\n"
        f"from .models import {spec.model_name}\n"
        "\n"
        "\n"
        f"@admin.register({spec.model_name})\n"
        f"class {spec.model_name}Admin(admin.ModelAdmin):\n"
        f"    list_display = ({filter_fields}, \"owner\", \"created_at\")\n"
        "    search_fields = (\"owner__username\",)\n"
    )

    tests_py = (
        "from django.test import TestCase\n"
        "\n"
        "\n"
        "class SmokeTest(TestCase):\n"
        "    def test_truth(self):\n"
        "        self.assertTrue(True)\n"
    )

    dashboard_tpl = (
        DASHBOARD_TEMPLATE.replace("__APP_NAME__", app_name)
        .replace("__APP_TITLE__", spec.app_title)
        .replace("__MODEL_PLURAL__", spec.model_plural)
    )

    add_tpl = (
        FORM_TEMPLATE.replace("__APP_NAME__", app_name)
        .replace("__APP_TITLE__", spec.app_title)
        .replace("__ACTION__", "Nuovo elemento")
    )
    update_tpl = (
        FORM_TEMPLATE.replace("__APP_NAME__", app_name)
        .replace("__APP_TITLE__", spec.app_title)
        .replace("__ACTION__", "Aggiorna elemento")
    )

    remove_tpl = REMOVE_TEMPLATE.replace("__APP_NAME__", app_name).replace("__APP_TITLE__", spec.app_title)
    base_tpl = BASE_TEMPLATE.replace("__APP_TITLE__", spec.app_title).replace("__APP_NAME__", app_name)

    styles_css = (
        "body {\n"
        "  font-family: system-ui, -apple-system, Segoe UI, Roboto, sans-serif;\n"
        "  margin: 0;\n"
        "  background: #f6f7fb;\n"
        "  color: #1f2937;\n"
        "}\n"
        ".shell { max-width: 1100px; margin: 0 auto; padding: 24px; }\n"
        ".top { display: flex; justify-content: space-between; align-items: center; margin-bottom: 20px; }\n"
        ".top h1 { margin: 0; font-size: 1.6rem; }\n"
        ".btn { display: inline-block; padding: 8px 12px; border: 1px solid #cbd5e1; border-radius: 8px; text-decoration: none; color: inherit; background: white; }\n"
        ".btn.primary { background: #111827; color: white; border-color: #111827; }\n"
        ".panel { background: white; border: 1px solid #e5e7eb; border-radius: 12px; padding: 16px; margin-bottom: 16px; }\n"
        ".table { width: 100%; border-collapse: collapse; }\n"
        ".table th, .table td { border-bottom: 1px solid #e5e7eb; text-align: left; padding: 8px; font-size: 0.95rem; }\n"
        ".form p { margin: 0 0 12px; }\n"
        ".actions { display: flex; gap: 10px; margin-top: 10px; }\n"
        ".warn { border: 1px solid #f59e0b; background: #fffbeb; color: #92400e; padding: 10px; border-radius: 8px; }\n"
    )

    return {
        "__init__.py": "",
        "apps.py": apps_py,
        "admin.py": admin_py,
        "models.py": models_py,
        "forms.py": forms_py,
        "views.py": views_py,
        "urls.py": urls_py,
        "tests.py": tests_py,
        "migrations/__init__.py": "",
        f"templates/{app_name}/base.html": base_tpl,
        f"templates/{app_name}/dashboard.html": dashboard_tpl,
        f"templates/{app_name}/add_item.html": add_tpl,
        f"templates/{app_name}/update_item.html": update_tpl,
        f"templates/{app_name}/remove_item.html": remove_tpl,
        f"static/{app_name}/styles.css": styles_css,
    }


def build_model_fields(fields: list[FieldSpec]) -> list[str]:
    lines: list[str] = []
    for spec in fields:
        if spec.kind == "char":
            attrs = ["max_length=160"]
            if not spec.required:
                attrs.append("blank=True")
            lines.append(f"    {spec.name} = models.CharField({', '.join(attrs)})")
        elif spec.kind == "text":
            attrs = []
            if not spec.required:
                attrs.append("blank=True")
            attrs_text = ", ".join(attrs)
            if attrs_text:
                lines.append(f"    {spec.name} = models.TextField({attrs_text})")
            else:
                lines.append(f"    {spec.name} = models.TextField()")
        elif spec.kind == "integer":
            attrs = []
            if not spec.required:
                attrs.extend(["null=True", "blank=True"])
            attrs_text = ", ".join(attrs)
            if attrs_text:
                lines.append(f"    {spec.name} = models.IntegerField({attrs_text})")
            else:
                lines.append(f"    {spec.name} = models.IntegerField()")
        elif spec.kind == "decimal":
            attrs = ["max_digits=12", "decimal_places=2"]
            if not spec.required:
                attrs.extend(["null=True", "blank=True"])
            lines.append(f"    {spec.name} = models.DecimalField({', '.join(attrs)})")
        elif spec.kind == "date":
            attrs = []
            if not spec.required:
                attrs.extend(["null=True", "blank=True"])
            attrs_text = ", ".join(attrs)
            if attrs_text:
                lines.append(f"    {spec.name} = models.DateField({attrs_text})")
            else:
                lines.append(f"    {spec.name} = models.DateField()")
        elif spec.kind == "datetime":
            attrs = []
            if not spec.required:
                attrs.extend(["null=True", "blank=True"])
            attrs_text = ", ".join(attrs)
            if attrs_text:
                lines.append(f"    {spec.name} = models.DateTimeField({attrs_text})")
            else:
                lines.append(f"    {spec.name} = models.DateTimeField()")
        elif spec.kind == "boolean":
            default = "False" if not spec.required else "True"
            lines.append(f"    {spec.name} = models.BooleanField(default={default})")
        elif spec.kind == "choice":
            const_name = f"{spec.name.upper()}_CHOICES"
            choices = spec.choices or ["OPEN", "DONE"]
            lines.append(f"    {const_name} = [")
            for choice in choices:
                label = choice.replace("_", " ").title()
                lines.append(f'        ("{choice}", "{label}"),')
            lines.append("    ]")
            attrs = [f"max_length={max(len(choice) for choice in choices)}", f"choices={const_name}"]
            if spec.required:
                attrs.append(f'default="{choices[0]}"')
            else:
                attrs.append("blank=True")
            lines.append(f"    {spec.name} = models.CharField({', '.join(attrs)})")

    return lines


def write_app_files(app_dir: Path, files: dict[str, str]) -> list[str]:
    app_dir.mkdir(parents=True, exist_ok=False)
    created_files: list[str] = []

    for relative_path, content in files.items():
        destination = app_dir / relative_path
        destination.parent.mkdir(parents=True, exist_ok=True)
        destination.write_text((content or "").rstrip() + "\n", encoding="utf-8")
        rel_to_base = destination.relative_to(settings.BASE_DIR)
        created_files.append(str(rel_to_base))

    created_files.sort()
    return created_files


def project_settings_path() -> Path:
    module_parts = settings.SETTINGS_MODULE.split(".")
    if len(module_parts) < 2:
        raise AppBuilderError("SETTINGS_MODULE non valido.")
    package = module_parts[0]
    filename = f"{module_parts[-1]}.py"
    return settings.BASE_DIR / package / filename


def project_urls_path() -> Path:
    module_parts = settings.ROOT_URLCONF.split(".")
    if len(module_parts) < 2:
        raise AppBuilderError("ROOT_URLCONF non valido.")
    package = module_parts[0]
    filename = f"{module_parts[-1]}.py"
    return settings.BASE_DIR / package / filename


def ensure_app_in_settings(app_name: str) -> bool:
    path = project_settings_path()
    source = path.read_text(encoding="utf-8")

    token_single = f"'{app_name}'"
    token_double = f'"{app_name}"'
    if token_single in source or token_double in source:
        return False

    marker = "INSTALLED_APPS = ["
    start = source.find(marker)
    if start < 0:
        raise AppBuilderError("Impossibile trovare INSTALLED_APPS in settings.py")

    end = source.find("]", start)
    if end < 0:
        raise AppBuilderError("Lista INSTALLED_APPS non valida in settings.py")

    entry = f"    '{app_name}',\n"
    updated = source[:end] + entry + source[end:]
    path.write_text(updated, encoding="utf-8")
    return True


def ensure_app_in_project_urls(app_name: str) -> bool:
    path = project_urls_path()
    source = path.read_text(encoding="utf-8")

    route_entry = f"path('{app_name}/', include('{app_name}.urls'))"
    if route_entry in source:
        return False

    if "from django.urls import include, path" not in source:
        if "from django.urls import path" in source:
            source = source.replace("from django.urls import path", "from django.urls import include, path")
        elif "from django.urls import" in source:
            source = source.replace("from django.urls import", "from django.urls import include,")
        else:
            source = "from django.urls import include, path\n" + source

    marker = "urlpatterns = ["
    start = source.find(marker)
    if start < 0:
        raise AppBuilderError("Impossibile trovare urlpatterns in urls.py")

    end = source.find("]", start)
    if end < 0:
        raise AppBuilderError("Lista urlpatterns non valida in urls.py")

    entry = f"    path('{app_name}/', include('{app_name}.urls')),\n"
    updated = source[:end] + entry + source[end:]
    path.write_text(updated, encoding="utf-8")
    return True


BASE_TEMPLATE = """{% load static %}
<!doctype html>
<html lang="it">
  <head>
    <meta charset="utf-8">
    <meta name="viewport" content="width=device-width, initial-scale=1">
    <title>__APP_TITLE__</title>
    <link rel="stylesheet" href="{% static '__APP_NAME__/styles.css' %}">
  </head>
  <body>
    <main class="shell">
      <header class="top">
        <h1>__APP_TITLE__</h1>
        <a class="btn" href="/">Dashboard</a>
      </header>
      {% block content %}{% endblock %}
    </main>
  </body>
</html>
"""


DASHBOARD_TEMPLATE = """{% extends '__APP_NAME__/base.html' %}

{% block content %}
  <section class="panel">
    <p>Modulo: __APP_TITLE__</p>
    <p>Gestione: __MODEL_PLURAL__</p>
    <div class="actions">
      <a class="btn primary" href="./api/add">Nuovo</a>
    </div>
  </section>

  <section class="panel">
    {% if rows %}
      <table class="table">
        <thead>
          <tr>
            {% for field in display_fields %}
              <th>{{ field }}</th>
            {% endfor %}
            <th>Azioni</th>
          </tr>
        </thead>
        <tbody>
          {% for row in rows %}
            <tr>
              {% for value in row.values %}
                <td>{{ value }}</td>
              {% endfor %}
              <td>
                <a class="btn" href="./api/update?id={{ row.id }}">Modifica</a>
                <a class="btn" href="./api/remove?id={{ row.id }}">Rimuovi</a>
              </td>
            </tr>
          {% endfor %}
        </tbody>
      </table>
    {% else %}
      <div class="warn">Nessun elemento disponibile.</div>
    {% endif %}
  </section>
{% endblock %}
"""


FORM_TEMPLATE = """{% extends '__APP_NAME__/base.html' %}

{% block content %}
  <section class="panel">
    <h2>__ACTION__</h2>
    <form method="post" class="form">
      {% csrf_token %}
      {{ form.as_p }}
      <div class="actions">
        <button class="btn primary" type="submit">Salva</button>
        <a class="btn" href="../">Annulla</a>
      </div>
    </form>
  </section>
{% endblock %}
"""


REMOVE_TEMPLATE = """{% extends '__APP_NAME__/base.html' %}

{% block content %}
  <section class="panel">
    <h2>Rimuovi elemento</h2>
    <p>Confermi l'eliminazione di: <strong>{{ item }}</strong>?</p>
    <form method="post">
      {% csrf_token %}
      <div class="actions">
        <button class="btn primary" type="submit">Conferma</button>
        <a class="btn" href="../">Annulla</a>
      </div>
    </form>
  </section>
{% endblock %}
"""
