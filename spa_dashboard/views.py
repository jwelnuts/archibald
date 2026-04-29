import json

from django.contrib.auth.decorators import login_required
from django.http import JsonResponse
from django.shortcuts import render
from django.views.decorators.http import require_http_methods

from core.models import UserNavConfig
from .widget_data import fetch_widget_data

DEFAULT_LAYOUT = [
    {"id": "w1", "type": "placeholder", "col_span": 4, "row_span": 1},
    {"id": "w2", "type": "placeholder", "col_span": 4, "row_span": 1},
    {"id": "w3", "type": "placeholder", "col_span": 4, "row_span": 1},
]


def _get_spa_layout(user):
    nav_config = UserNavConfig.objects.filter(user=user).first()
    if nav_config and isinstance(nav_config.config, dict):
        saved = nav_config.config.get("spa_layout")
        if isinstance(saved, list) and saved:
            return saved
    return DEFAULT_LAYOUT


def _save_spa_layout(user, layout):
    nav_config, _ = UserNavConfig.objects.get_or_create(user=user)
    config = nav_config.config if isinstance(nav_config.config, dict) else {}
    config["spa_layout"] = layout
    nav_config.config = config
    nav_config.save(update_fields=["config"])


@login_required
def shell(request):
    return render(request, "spa_dashboard/shell.html")


@login_required
@require_http_methods(["GET"])
def api_layout_get(request):
    layout = _get_spa_layout(request.user)
    return JsonResponse({"layout": layout})


@login_required
@require_http_methods(["POST"])
def api_layout_save(request):
    try:
        payload = json.loads((request.body or b"{}").decode("utf-8"))
    except (json.JSONDecodeError, UnicodeDecodeError):
        return JsonResponse({"ok": False, "error": "invalid_json"}, status=400)

    layout = payload.get("layout")
    if not isinstance(layout, list):
        return JsonResponse({"ok": False, "error": "invalid_payload"}, status=400)

    for slot in layout:
        if not isinstance(slot, dict) or "id" not in slot or "type" not in slot:
            return JsonResponse({"ok": False, "error": "invalid_slot"}, status=400)

    _save_spa_layout(request.user, layout)
    return JsonResponse({"ok": True})


@login_required
@require_http_methods(["GET"])
def api_widget_data(request, widget_id):
    layout = _get_spa_layout(request.user)
    slot = next((s for s in layout if s["id"] == widget_id), None)
    if slot is None:
        return JsonResponse({"error": "not_found"}, status=404)

    data = fetch_widget_data(request.user, slot)
    return JsonResponse({"widget_id": widget_id, "type": slot["type"], "data": data})
