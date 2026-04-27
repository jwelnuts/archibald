import base64
import json
import os
from pathlib import Path
import re
import urllib.error
import urllib.request
from urllib.parse import quote, urljoin
from importlib.util import find_spec

from django.apps import apps
from django.conf import settings
from django.db import connection
from django.db.migrations.loader import MigrationLoader
from django.urls import URLPattern, URLResolver, Resolver404, get_resolver, resolve


_DAV_PRINCIPAL_SANITIZER = re.compile(r"[^a-z0-9._@+-]+")
_DAV_COLLECTION_SANITIZER = re.compile(r"[^a-z0-9._-]+")


def _normalize_caldav_url(raw_url):
    value = (raw_url or "").strip()
    if not value:
        return ""
    return value if value.endswith("/") else f"{value}/"


def _probe_http_endpoint(url, *, username="", password="", timeout_seconds=3):
    if not url:
        return {
            "url": "",
            "ok": False,
            "status_code": None,
            "status_label": "N/D",
            "detail": "URL non configurata.",
        }

    headers = {"User-Agent": "mio-workbench-radicale-debug"}
    if username and password:
        token = base64.b64encode(f"{username}:{password}".encode("utf-8")).decode("ascii")
        headers["Authorization"] = f"Basic {token}"
    request = urllib.request.Request(url, headers=headers, method="GET")
    try:
        with urllib.request.urlopen(request, timeout=timeout_seconds) as response:
            status_code = int(getattr(response, "status", 200))
            content_type = response.headers.get("Content-Type", "")
            return {
                "url": url,
                "ok": status_code < 500,
                "status_code": status_code,
                "status_label": f"HTTP {status_code}",
                "detail": content_type or "Connessione riuscita.",
            }
    except urllib.error.HTTPError as exc:
        status_code = int(exc.code)
        content_type = ""
        if getattr(exc, "headers", None):
            content_type = exc.headers.get("Content-Type", "")
        return {
            "url": url,
            "ok": status_code < 500,
            "status_code": status_code,
            "status_label": f"HTTP {status_code}",
            "detail": content_type or str(exc.reason),
        }
    except urllib.error.URLError as exc:
        return {
            "url": url,
            "ok": False,
            "status_code": None,
            "status_label": "Network error",
            "detail": str(exc.reason),
        }
    except Exception as exc:
        return {
            "url": url,
            "ok": False,
            "status_code": None,
            "status_label": "Errore",
            "detail": str(exc),
        }


def _mask_secret(value):
    if not value:
        return "-"
    if len(value) <= 6:
        return "***"
    return f"{value[:2]}***{value[-2:]}"


def _normalize_dav_principal(value):
    candidate = _DAV_PRINCIPAL_SANITIZER.sub("-", (value or "").strip().lower()).strip("-")
    if not candidate:
        raise ValueError("Principal DAV non valido.")
    return candidate


def _normalize_collection_slug(value):
    candidate = _DAV_COLLECTION_SANITIZER.sub("-", (value or "").strip().lower()).strip("-.")
    if not candidate:
        raise ValueError("Nome calendario non valido.")
    return candidate


def _radicale_collections_root(users_path):
    if users_path:
        return users_path.parent / "collections" / "collection-root"
    return Path("/radicale-data/collections/collection-root")


def _sync_owner_from_reference(path, reference):
    if not reference or not reference.exists():
        return
    try:
        stat = reference.stat()
        os.chown(path, stat.st_uid, stat.st_gid)
    except OSError:
        return


def _ensure_calendar_collection(*, users_path, principal, calendar_slug, display_name=""):
    collections_root = _radicale_collections_root(users_path)
    principal_value = _normalize_dav_principal(principal)
    calendar_value = _normalize_collection_slug(calendar_slug)

    principal_dir = collections_root / principal_value
    calendar_dir = principal_dir / calendar_value
    principal_dir.mkdir(parents=True, exist_ok=True)
    calendar_dir.mkdir(parents=True, exist_ok=True)
    _sync_owner_from_reference(principal_dir, users_path)
    _sync_owner_from_reference(calendar_dir, users_path)

    props_payload = {"tag": "VCALENDAR"}
    display_name_value = (display_name or "").strip()
    if display_name_value:
        props_payload["D:displayname"] = display_name_value[:120]

    props_path = calendar_dir / ".Radicale.props"
    props_path.write_text(json.dumps(props_payload, ensure_ascii=True, separators=(",", ":")), encoding="utf-8")
    _sync_owner_from_reference(props_path, users_path)
    return calendar_dir, props_path


def _load_collections_snapshot(users_path):
    root = _radicale_collections_root(users_path)
    result = {
        "root": str(root),
        "exists": root.exists(),
        "principals": [],
        "error": "",
    }
    if not root.exists():
        return result

    try:
        principal_rows = []
        for principal_dir in sorted(root.iterdir(), key=lambda item: item.name):
            if not principal_dir.is_dir():
                continue
            collections = []
            for child in sorted(principal_dir.iterdir(), key=lambda item: item.name):
                if not child.is_dir():
                    continue
                props_path = child / ".Radicale.props"
                tag = "-"
                if props_path.exists():
                    try:
                        data = json.loads(props_path.read_text(encoding="utf-8"))
                        tag = str(data.get("tag") or "-")
                    except Exception:
                        tag = "ERR"
                collections.append(
                    {
                        "name": child.name,
                        "tag": tag,
                    }
                )
            principal_rows.append(
                {
                    "name": principal_dir.name,
                    "collections": collections,
                }
            )
        result["principals"] = principal_rows
        return result
    except Exception as exc:
        result["error"] = str(exc)
        return result


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


def _iter_url_patterns(urlpatterns, prefix=""):
    for entry in urlpatterns:
        chunk = str(entry.pattern or "")
        full_path = f"{prefix}{chunk}"
        if isinstance(entry, URLResolver):
            yield from _iter_url_patterns(entry.url_patterns, full_path)
            continue
        if isinstance(entry, URLPattern):
            yield full_path, entry


def _is_api_endpoint(path_value):
    segments = [seg for seg in path_value.strip("/").split("/") if seg]
    return "api" in segments or path_value.startswith("api/") or "/api/" in path_value


def _methods_for_pattern(pattern):
    callback = pattern.callback
    actions = getattr(callback, "actions", None)
    if actions:
        methods = sorted({method.upper() for method in actions.keys()})
        if methods:
            return methods

    view_class = getattr(callback, "view_class", None)
    if view_class and hasattr(view_class, "http_method_names"):
        methods = [
            method.upper()
            for method in view_class.http_method_names
            if method not in {"head", "options", "trace"}
        ]
        if methods:
            return sorted(set(methods))

    allowed = getattr(callback, "allowed_methods", None)
    if allowed:
        methods = [m.upper() for m in allowed if m]
        if methods:
            return sorted(set(methods))

    return ["N/D"]


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
