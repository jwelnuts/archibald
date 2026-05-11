# core/mobile_api_views.py
from datetime import date, timedelta
import json
import logging

from django.conf import settings
from django.contrib.auth import authenticate, get_user_model
from django.views.decorators.csrf import csrf_exempt
from django.views.decorators.http import require_http_methods
from django.http import JsonResponse
from django.utils import timezone

from core.dav import DavProvisioningError, ensure_user_dav_access
from core.helpers import (
    _mobile_json_error,
    _mobile_parse_json,
    _mobile_hash_token,
    _mobile_access_ttl_seconds,
    _mobile_refresh_ttl_days,
    _mobile_create_session,
    _mobile_payload,
    _mobile_bearer_token,
    _mobile_authenticate_request,
    _dashboard_snapshot_context,
    _todos_response_for_user,
    _todos_check_for_user,
    _todos_item_create_for_user,
    _todos_item_update_for_user,
    _todos_item_delete_for_user,
    _projects_response_for_user,
    _agenda_response_for_user,
)
from core.models import MobileApiSession

logger = logging.getLogger(__name__)


@csrf_exempt
@require_http_methods(["POST"])
def mobile_auth_login(request):
    payload = _mobile_parse_json(request)
    if payload is None:
        return _mobile_json_error("invalid_json", status=400)

    identity = (payload.get("identity") or payload.get("email") or payload.get("username") or "").strip()
    password = (payload.get("password") or "").strip()
    device_label = (payload.get("device_label") or "").strip()

    if not identity or not password:
        return _mobile_json_error("missing_credentials", status=400)

    user_model = get_user_model()
    user_by_email = user_model.objects.filter(email__iexact=identity).first()
    auth_username = user_by_email.username if user_by_email else identity
    user = authenticate(request, username=auth_username, password=password)
    if not user or not user.is_active:
        return _mobile_json_error("invalid_credentials", status=401)

    if settings.CALDAV_ENABLED:
        try:
            ensure_user_dav_access(user, raw_password=password)
        except DavProvisioningError as exc:
            logger.warning("DAV sync failed during mobile login for user=%s: %s", user.id, exc)

    session, access_token, refresh_token = _mobile_create_session(user, request, device_label=device_label)
    return JsonResponse(_mobile_payload(user, access_token, refresh_token, session))


@csrf_exempt
@require_http_methods(["POST"])
def mobile_auth_refresh(request):
    payload = _mobile_parse_json(request)
    if payload is None:
        return _mobile_json_error("invalid_json", status=400)

    refresh_token = (payload.get("refresh_token") or "").strip()
    if not refresh_token:
        return _mobile_json_error("missing_refresh_token", status=400)

    now = timezone.now()
    session = (
        MobileApiSession.objects.select_related("user")
        .filter(
            refresh_token_hash=_mobile_hash_token(refresh_token),
            revoked_at__isnull=True,
            refresh_expires_at__gt=now,
        )
        .first()
    )
    if not session:
        return _mobile_json_error("invalid_or_expired_refresh_token", status=401)

    access_token, new_refresh_token = _mobile_issue_tokens()
    session.access_token_hash = _mobile_hash_token(access_token)
    session.refresh_token_hash = _mobile_hash_token(new_refresh_token)
    session.access_expires_at = now + timedelta(seconds=_mobile_access_ttl_seconds())
    session.refresh_expires_at = now + timedelta(days=_mobile_refresh_ttl_days())
    session.last_used_at = now
    session.save(
        update_fields=[
            "access_token_hash",
            "refresh_token_hash",
            "access_expires_at",
            "refresh_expires_at",
            "last_used_at",
            "updated_at",
        ]
    )

    return JsonResponse(_mobile_payload(session.user, access_token, new_refresh_token, session))


@csrf_exempt
@require_http_methods(["POST"])
def mobile_auth_logout(request):
    payload = _mobile_parse_json(request)
    if payload is None:
        payload = {}

    now = timezone.now()
    session = None
    access_token = _mobile_bearer_token(request)
    if access_token:
        session = (
            MobileApiSession.objects.filter(
                access_token_hash=_mobile_hash_token(access_token),
                revoked_at__isnull=True,
            )
            .order_by("-id")
            .first()
        )

    if not session:
        refresh_token = (payload.get("refresh_token") or "").strip()
        if refresh_token:
            session = (
                MobileApiSession.objects.filter(
                    refresh_token_hash=_mobile_hash_token(refresh_token),
                    revoked_at__isnull=True,
                )
                .order_by("-id")
                .first()
            )

    if session:
        session.revoked_at = now
        session.save(update_fields=["revoked_at", "updated_at"])

    return JsonResponse({"ok": True})


@require_http_methods(["GET"])
def mobile_dashboard(request):
    session, error = _mobile_authenticate_request(request)
    if error:
        return error

    snapshot_context = _dashboard_snapshot_context(session.user)
    snapshot = snapshot_context["snapshot"]
    today = date.today()
    events = []
    for row in snapshot_context["focus_rows"][:8]:
        due_date = row.get("due_date")
        events.append(
            {
                "kind": row.get("kind"),
                "title": row.get("title"),
                "due_date": due_date.isoformat() if due_date else "",
                "url": row.get("url", ""),
                "warn": bool(due_date and due_date < today),
            }
        )

    return JsonResponse(
        {
            "ok": True,
            "synced_at": timezone.now().isoformat(),
            "metrics": {
                "open_tasks": snapshot["open_tasks"],
                "planner_queue": snapshot["planner_planned"],
                "alerts_open": snapshot["overdue_tasks"],
                "due_subscriptions_week": snapshot["due_subscriptions_week"],
            },
            "snapshot": {
                "tasks_today": snapshot["tasks_today"],
                "month_transactions": snapshot["month_transactions"],
                "month_income": snapshot["month_income"],
                "month_expense": snapshot["month_expense"],
                "month_balance": snapshot["month_balance"],
            },
            "events": events,
            "user": {
                "id": session.user.id,
                "username": session.user.username,
                "email": session.user.email,
            },
        }
    )


@require_http_methods(["GET"])
def mobile_todos(request):
    session, error = _mobile_authenticate_request(request)
    if error:
        return error
    return _todos_response_for_user(session.user, request.GET.get("week"))


@csrf_exempt
@require_http_methods(["POST"])
def mobile_todos_check(request):
    payload = _mobile_parse_json(request)
    if payload is None:
        return _mobile_json_error("invalid_json", status=400)
    session, error = _mobile_authenticate_request(request)
    if error:
        return error
    return _todos_check_for_user(session.user, payload)


@csrf_exempt
@require_http_methods(["POST"])
def mobile_todos_item_create(request):
    payload = _mobile_parse_json(request)
    if payload is None:
        return _mobile_json_error("invalid_json", status=400)
    session, error = _mobile_authenticate_request(request)
    if error:
        return error
    return _todos_item_create_for_user(session.user, payload)


@csrf_exempt
@require_http_methods(["POST"])
def mobile_todos_item_update(request):
    payload = _mobile_parse_json(request)
    if payload is None:
        return _mobile_json_error("invalid_json", status=400)
    session, error = _mobile_authenticate_request(request)
    if error:
        return error
    return _todos_item_update_for_user(session.user, payload)


@csrf_exempt
@require_http_methods(["POST"])
def mobile_todos_item_delete(request):
    payload = _mobile_parse_json(request)
    if payload is None:
        return _mobile_json_error("invalid_json", status=400)
    session, error = _mobile_authenticate_request(request)
    if error:
        return error
    return _todos_item_delete_for_user(session.user, payload)


@require_http_methods(["GET"])
def mobile_projects(request):
    session, error = _mobile_authenticate_request(request)
    if error:
        return error
    return _projects_response_for_user(session.user)


@require_http_methods(["GET"])
def mobile_agenda(request):
    session, error = _mobile_authenticate_request(request)
    if error:
        return error
    return _agenda_response_for_user(
        session.user,
        request.GET.get("start"),
        request.GET.get("duration"),
    )
