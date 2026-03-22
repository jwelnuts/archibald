from __future__ import annotations

import base64
import logging
from dataclasses import dataclass
from datetime import datetime, timezone as dt_timezone
from urllib.error import HTTPError, URLError
from urllib.parse import quote
from urllib.request import Request, urlopen

from django.conf import settings
from django.utils import timezone

from core.models import DavAccount

from .models import Task

logger = logging.getLogger(__name__)


@dataclass
class DavSyncOutcome:
    ok: bool
    message: str = ""


def todo_collection_slug() -> str:
    raw = (
        getattr(settings, "CALDAV_DEFAULT_USER_COLLECTION", "")
        or getattr(settings, "CALDAV_TODO_COLLECTION", "")
        or "personal_dav"
    )
    return (raw or "").strip().strip("/") or "personal_dav"


def todo_collection_path_for_user(user) -> str:
    account = DavAccount.objects.filter(user=user, is_active=True).first()
    if not account:
        return ""
    return f"{account.dav_username}/{todo_collection_slug()}"


def todo_collection_url_for_user(user) -> str:
    if not getattr(settings, "CALDAV_ENABLED", False):
        return ""
    base_url = (getattr(settings, "CALDAV_BASE_URL", "") or "").strip()
    if not base_url:
        return ""
    account = DavAccount.objects.filter(user=user, is_active=True).first()
    if not account:
        return ""
    if not base_url.endswith("/"):
        base_url = f"{base_url}/"
    principal = quote(account.dav_username, safe="@._+-")
    collection = quote(todo_collection_slug(), safe="@._+-")
    return f"{base_url}{principal}/{collection}/"


def _service_auth_header() -> str:
    username = (getattr(settings, "CALDAV_SERVICE_USERNAME", "") or "").strip()
    password = (getattr(settings, "CALDAV_SERVICE_PASSWORD", "") or "").strip()
    if not username or not password:
        return ""
    raw = f"{username}:{password}".encode("utf-8")
    return f"Basic {base64.b64encode(raw).decode('ascii')}"


def _dav_request(method: str, url: str, *, body: str = "", headers: dict[str, str] | None = None) -> tuple[int, dict, str]:
    request_headers = {
        "User-Agent": "mio-todo-vtodo-sync/1.0",
    }
    auth_header = _service_auth_header()
    if auth_header:
        request_headers["Authorization"] = auth_header
    if headers:
        request_headers.update(headers)

    payload = body.encode("utf-8") if body else None
    request = Request(url, data=payload, method=method, headers=request_headers)

    try:
        with urlopen(request, timeout=8) as response:
            response_body = response.read().decode("utf-8", errors="replace")
            return int(response.status), dict(response.headers.items()), response_body
    except HTTPError as exc:
        response_body = exc.read().decode("utf-8", errors="replace") if hasattr(exc, "read") else str(exc)
        response_headers = dict(exc.headers.items()) if getattr(exc, "headers", None) else {}
        return int(exc.code), response_headers, response_body
    except URLError as exc:
        raise RuntimeError(f"DAV network error: {exc.reason}") from exc


def _ensure_collection(collection_url: str) -> DavSyncOutcome:
    body = (
        '<?xml version="1.0" encoding="utf-8"?>'
        '<C:mkcalendar xmlns:D="DAV:" xmlns:C="urn:ietf:params:xml:ns:caldav">'
        "<D:set><D:prop><D:displayname>MIO Todo</D:displayname></D:prop></D:set>"
        "</C:mkcalendar>"
    )
    status, _headers, response_body = _dav_request(
        "MKCALENDAR",
        collection_url,
        body=body,
        headers={"Content-Type": "application/xml; charset=utf-8"},
    )
    if status in {200, 201, 204, 405, 409}:
        return DavSyncOutcome(ok=True)
    return DavSyncOutcome(ok=False, message=f"MKCALENDAR {status}: {response_body[:180]}")


def _ics_escape(value: str) -> str:
    return (
        (value or "")
        .replace("\\", "\\\\")
        .replace(";", "\\;")
        .replace(",", "\\,")
        .replace("\r\n", "\n")
        .replace("\r", "\n")
        .replace("\n", "\\n")
    )


def _ical_utc(dt: datetime) -> str:
    if timezone.is_naive(dt):
        dt = timezone.make_aware(dt, timezone.get_current_timezone())
    return dt.astimezone(dt_timezone.utc).strftime("%Y%m%dT%H%M%SZ")


def _task_uid(task: Task) -> str:
    return f"mio-task-{task.owner_id}-{task.id}@miorganizzo"


def _task_href(task: Task) -> str:
    return f"todo-{task.id}.ics"


def _task_status(task: Task) -> str:
    mapping = {
        Task.Status.OPEN: "NEEDS-ACTION",
        Task.Status.IN_PROGRESS: "IN-PROCESS",
        Task.Status.DONE: "COMPLETED",
    }
    return mapping.get(task.status, "NEEDS-ACTION")


def _task_priority(task: Task) -> int:
    mapping = {
        Task.Priority.HIGH: 1,
        Task.Priority.MEDIUM: 5,
        Task.Priority.LOW: 9,
    }
    return mapping.get(task.priority, 5)


def _task_to_vtodo(task: Task) -> str:
    now_utc = timezone.now()
    lines = [
        "BEGIN:VCALENDAR",
        "VERSION:2.0",
        "PRODID:-//MIO//Todo Sync//IT",
        "BEGIN:VTODO",
        f"UID:{_task_uid(task)}",
        f"DTSTAMP:{_ical_utc(now_utc)}",
        f"CREATED:{_ical_utc(task.created_at)}",
        f"LAST-MODIFIED:{_ical_utc(task.updated_at)}",
        f"SUMMARY:{_ics_escape(task.title)}",
        f"STATUS:{_task_status(task)}",
        f"PRIORITY:{_task_priority(task)}",
        f"X-MIO-TASK-ID:{task.id}",
        f"X-MIO-ITEM-TYPE:{task.item_type}",
    ]
    if task.note:
        lines.append(f"DESCRIPTION:{_ics_escape(task.note)}")
    if task.project_id:
        lines.append(f"X-MIO-PROJECT-ID:{task.project_id}")
    if task.category_id:
        lines.append(f"X-MIO-CATEGORY-ID:{task.category_id}")
    if task.due_date:
        if task.due_time:
            due_dt = datetime.combine(task.due_date, task.due_time)
            lines.append(f"DUE:{due_dt.strftime('%Y%m%dT%H%M%S')}")
        else:
            lines.append(f"DUE;VALUE=DATE:{task.due_date.strftime('%Y%m%d')}")
    if task.status == Task.Status.DONE:
        lines.append(f"COMPLETED:{_ical_utc(now_utc)}")
    lines.extend(["END:VTODO", "END:VCALENDAR"])
    return "\r\n".join(lines) + "\r\n"


def _is_sync_configured() -> bool:
    return bool(
        getattr(settings, "CALDAV_ENABLED", False)
        and (getattr(settings, "CALDAV_BASE_URL", "") or "").strip()
        and _service_auth_header()
    )


def push_task_to_vtodo(task: Task, *, ensure_collection: bool = True) -> DavSyncOutcome:
    if not _is_sync_configured():
        return DavSyncOutcome(ok=False, message="CalDAV/VTODO sync non configurata.")

    collection_url = todo_collection_url_for_user(task.owner)
    if not collection_url:
        return DavSyncOutcome(ok=False, message="Account DAV utente non disponibile.")

    if ensure_collection:
        ensure_result = _ensure_collection(collection_url)
        if not ensure_result.ok:
            return ensure_result

    resource_url = f"{collection_url}{quote(_task_href(task), safe='._-')}"
    body = _task_to_vtodo(task)
    status, _headers, response_body = _dav_request(
        "PUT",
        resource_url,
        body=body,
        headers={"Content-Type": "text/calendar; charset=utf-8"},
    )
    if status in {200, 201, 204}:
        return DavSyncOutcome(ok=True)
    return DavSyncOutcome(ok=False, message=f"PUT {status}: {response_body[:180]}")


def delete_task_from_vtodo(task: Task) -> DavSyncOutcome:
    if not _is_sync_configured():
        return DavSyncOutcome(ok=False, message="CalDAV/VTODO sync non configurata.")

    collection_url = todo_collection_url_for_user(task.owner)
    if not collection_url:
        return DavSyncOutcome(ok=False, message="Account DAV utente non disponibile.")

    resource_url = f"{collection_url}{quote(_task_href(task), safe='._-')}"
    status, _headers, response_body = _dav_request("DELETE", resource_url)
    if status in {200, 202, 204, 404}:
        return DavSyncOutcome(ok=True)
    return DavSyncOutcome(ok=False, message=f"DELETE {status}: {response_body[:180]}")


def sync_all_tasks_to_vtodo(user) -> dict[str, int | str]:
    tasks = list(Task.objects.filter(owner=user).order_by("id"))
    if not tasks:
        return {"total": 0, "synced": 0, "failed": 0, "error": ""}

    if not _is_sync_configured():
        return {
            "total": len(tasks),
            "synced": 0,
            "failed": len(tasks),
            "error": "CalDAV/VTODO sync non configurata.",
        }

    collection_url = todo_collection_url_for_user(user)
    if not collection_url:
        return {
            "total": len(tasks),
            "synced": 0,
            "failed": len(tasks),
            "error": "Account DAV utente non disponibile.",
        }

    ensure_result = _ensure_collection(collection_url)
    if not ensure_result.ok:
        return {
            "total": len(tasks),
            "synced": 0,
            "failed": len(tasks),
            "error": ensure_result.message,
        }

    synced = 0
    failed = 0
    first_error = ""
    for task in tasks:
        result = push_task_to_vtodo(task, ensure_collection=False)
        if result.ok:
            synced += 1
            continue
        failed += 1
        if not first_error:
            first_error = result.message
        logger.warning("Todo DAV sync failed for task=%s user=%s: %s", task.id, user.id, result.message)

    return {"total": len(tasks), "synced": synced, "failed": failed, "error": first_error}
