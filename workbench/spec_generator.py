from __future__ import annotations

import json
import os
import re
import urllib.error
import urllib.request
from dataclasses import dataclass, field

import keyword

from workbench.constants import APP_NAME_RE, NAME_RE, MODEL_RE, SUPPORTED_FIELD_KINDS
from workbench.utils import AppBuilderError, AppSpec, FieldSpec, extract_output_text, normalize_app_name, sanitize_model_name, snake_to_pascal


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
                    f"Richiesta utente: {prompt}\n"
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