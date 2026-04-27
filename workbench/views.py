import json
import os
from pathlib import Path
import re
import urllib.error
import urllib.request
from urllib.parse import quote, urljoin

from django.conf import settings
from django.contrib import messages
from django.contrib.auth import get_user_model
from django.contrib.auth.decorators import login_required
from django.core.management.base import CommandError
from django.db import connection
from django.http import HttpResponseForbidden
from django.shortcuts import get_object_or_404, redirect, render
from django.views.decorators.http import require_POST

from .forms import WorkbenchItemForm
from .models import DebugChangeLog, WorkbenchItem

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


@login_required
def dashboard(request):
    all_logs = DebugChangeLog.objects.all().select_related("user").order_by("-created_at")
    logs = all_logs[:8]

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
def api_endpoints(request):
    resolver = get_resolver()
    rows = []
    for raw_path, pattern in _iter_url_patterns(resolver.url_patterns):
        normalized = raw_path.lstrip("^").rstrip("$")
        if not normalized.startswith("/"):
            normalized = f"/{normalized}"
        if not _is_api_endpoint(normalized):
            continue
        callback = pattern.callback
        view_name = getattr(callback, "__name__", callback.__class__.__name__)
        module_name = getattr(callback, "__module__", "")
        rows.append(
            {
                "path": normalized,
                "name": pattern.name or "-",
                "methods": ", ".join(_methods_for_pattern(pattern)),
                "view_name": view_name,
                "module_name": module_name,
            }
        )

    rows.sort(key=lambda row: row["path"])
    return render(
        request,
        "workbench/api_endpoints.html",
        {"endpoints": rows, "total_endpoints": len(rows)},
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


@login_required
def radicale_debug(request):
    from core.models import DavAccount
    from core.dav import DavProvisioningError, sync_radicale_users_file

    base_url = _normalize_caldav_url(getattr(settings, "CALDAV_BASE_URL", ""))
    service_username = (getattr(settings, "CALDAV_SERVICE_USERNAME", "") or "").strip()
    service_password = (getattr(settings, "CALDAV_SERVICE_PASSWORD", "") or "").strip()
    users_file_value = (getattr(settings, "RADICALE_USERS_FILE", "") or "").strip()
    lock_file_value = (getattr(settings, "RADICALE_USERS_LOCK_FILE", "") or "").strip()
    users_path = Path(users_file_value) if users_file_value else None
    lock_path = Path(lock_file_value) if lock_file_value else (Path(f"{users_path}.lock") if users_path else None)

    if request.method == "POST":
        action = (request.POST.get("action") or "").strip()
        try:
            if action == "sync_users_file":
                sync_radicale_users_file()
                messages.success(request, "File utenti Radicale sincronizzato.")
            elif action == "create_user_calendar":
                principal = _normalize_dav_principal(request.POST.get("principal") or "")
                calendar_slug = _normalize_collection_slug(request.POST.get("calendar_slug") or "")
                display_name = (request.POST.get("display_name") or "").strip()
                account = DavAccount.objects.filter(dav_username=principal).first()
                if not account:
                    messages.error(request, f"Principal DAV non trovato: {principal}")
                    return redirect("/workbench/debug/radicale")
                _ensure_calendar_collection(
                    users_path=users_path,
                    principal=principal,
                    calendar_slug=calendar_slug,
                    display_name=display_name,
                )
                messages.success(request, f"Calendario '{calendar_slug}' creato per {principal}.")
            elif action == "create_team_calendar":
                calendar_slug = _normalize_collection_slug(request.POST.get("calendar_slug") or "")
                display_name = (request.POST.get("display_name") or "").strip()
                _ensure_calendar_collection(
                    users_path=users_path,
                    principal="team",
                    calendar_slug=calendar_slug,
                    display_name=display_name,
                )
                messages.success(request, f"Calendario team '{calendar_slug}' creato.")
            else:
                messages.error(request, "Azione DAV non supportata.")
        except (DavProvisioningError, ValueError) as exc:
            messages.error(request, f"Operazione DAV fallita: {exc}")
        except Exception as exc:
            messages.error(request, f"Errore inatteso operazione DAV: {exc}")
        return redirect("/workbench/debug/radicale")

    users_file_info = {
        "path": str(users_path) if users_path else "",
        "exists": False,
        "size": 0,
        "permissions": "-",
        "line_count": 0,
        "preview": [],
        "error": "",
    }
    if users_path:
        try:
            users_file_info["exists"] = users_path.exists()
            if users_path.exists():
                stat = users_path.stat()
                users_file_info["size"] = stat.st_size
                users_file_info["permissions"] = oct(stat.st_mode & 0o777)
                lines = [line.strip() for line in users_path.read_text(encoding="utf-8").splitlines() if line.strip()]
                usernames = [line.split(":", 1)[0].strip() for line in lines if ":" in line]
                users_file_info["line_count"] = len(usernames)
                users_file_info["preview"] = usernames[:8]
        except Exception as exc:
            users_file_info["error"] = str(exc)

    probes = []
    if base_url:
        probes.append(
            {
                "name": "Base URL (anonimo)",
                "result": _probe_http_endpoint(base_url),
            }
        )
        probes.append(
            {
                "name": ".well-known/caldav (anonimo)",
                "result": _probe_http_endpoint(urljoin(base_url, "/.well-known/caldav")),
            }
        )
        if service_username and service_password:
            probes.append(
                {
                    "name": "Base URL (service account)",
                    "result": _probe_http_endpoint(
                        base_url,
                        username=service_username,
                        password=service_password,
                    ),
                }
            )
            service_principal_url = urljoin(base_url, f"{quote(service_username, safe='@._+-')}/")
            probes.append(
                {
                    "name": "Principal service",
                    "result": _probe_http_endpoint(
                        service_principal_url,
                        username=service_username,
                        password=service_password,
                    ),
                }
            )
    probes_ok_count = sum(1 for probe in probes if probe["result"]["ok"])

    dav_accounts = (
        DavAccount.objects.select_related("user")
        .order_by("dav_username")
    )
    app_user_count = get_user_model().objects.count()
    active_accounts_count = dav_accounts.filter(is_active=True).count()
    inactive_accounts_count = dav_accounts.filter(is_active=False).count()
    collections_snapshot = _load_collections_snapshot(users_path)

    context = {
        "caldav_enabled": bool(getattr(settings, "CALDAV_ENABLED", False)),
        "caldav_base_url": base_url,
        "caldav_login_domain": (getattr(settings, "CALDAV_LOGIN_DOMAIN", "") or "").strip(),
        "caldav_default_team_collection": (getattr(settings, "CALDAV_DEFAULT_TEAM_COLLECTION", "") or "").strip(),
        "service_username": service_username or "-",
        "service_password_masked": _mask_secret(service_password),
        "service_password_configured": bool(service_password),
        "service_username_configured": bool(service_username),
        "radicale_users_file": str(users_path) if users_path else "-",
        "radicale_users_lock_file": str(lock_path) if lock_path else "-",
        "users_file_info": users_file_info,
        "probes": probes,
        "probes_ok_count": probes_ok_count,
        "app_user_count": app_user_count,
        "active_accounts_count": active_accounts_count,
        "inactive_accounts_count": inactive_accounts_count,
        "collections_snapshot": collections_snapshot,
        "dav_accounts": dav_accounts[:120],
    }
    return render(request, "workbench/radicale_debug.html", context)
