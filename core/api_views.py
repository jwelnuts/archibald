# core/api_views.py
import json

from django.views.decorators.csrf import csrf_exempt
from django.views.decorators.http import require_http_methods

from core.helpers import (
    _mobile_json_error,
    _mobile_parse_json,
    _api_authenticate_request,
    _routines_response_for_user,
    _routines_check_for_user,
    _routines_item_create_for_user,
    _routines_item_update_for_user,
    _routines_item_delete_for_user,
    _projects_response_for_user,
    _agenda_response_for_user,
)


@require_http_methods(["GET"])
def api_routines(request):
    session, error = _api_authenticate_request(request)
    if error:
        return error
    return _routines_response_for_user(session.user, request.GET.get("week"))


@csrf_exempt
@require_http_methods(["POST"])
def api_routines_check(request):
    payload = _mobile_parse_json(request)
    if payload is None:
        return _mobile_json_error("invalid_json", status=400)
    session, error = _api_authenticate_request(request)
    if error:
        return error
    return _routines_check_for_user(session.user, payload)


@csrf_exempt
@require_http_methods(["POST"])
def api_routines_item_create(request):
    payload = _mobile_parse_json(request)
    if payload is None:
        return _mobile_json_error("invalid_json", status=400)
    session, error = _api_authenticate_request(request)
    if error:
        return error
    return _routines_item_create_for_user(session.user, payload)


@csrf_exempt
@require_http_methods(["POST"])
def api_routines_item_update(request):
    payload = _mobile_parse_json(request)
    if payload is None:
        return _mobile_json_error("invalid_json", status=400)
    session, error = _api_authenticate_request(request)
    if error:
        return error
    return _routines_item_update_for_user(session.user, payload)


@csrf_exempt
@require_http_methods(["POST"])
def api_routines_item_delete(request):
    payload = _mobile_parse_json(request)
    if payload is None:
        return _mobile_json_error("invalid_json", status=400)
    session, error = _api_authenticate_request(request)
    if error:
        return error
    return _routines_item_delete_for_user(session.user, payload)


@require_http_methods(["GET"])
def api_projects(request):
    session, error = _api_authenticate_request(request)
    if error:
        return error
    return _projects_response_for_user(session.user)


@require_http_methods(["GET"])
def api_agenda(request):
    session, error = _api_authenticate_request(request)
    if error:
        return error
    return _agenda_response_for_user(
        session.user,
        request.GET.get("start"),
        request.GET.get("duration"),
    )
