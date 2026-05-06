import json
from datetime import date as date_lib

from django.contrib.auth.decorators import login_required
from django.db import transaction as db_transaction
from django.http import JsonResponse
from django.shortcuts import get_object_or_404, render
from django.utils import timezone
from django.views.decorators.http import require_http_methods

from core.models import UserNavConfig
from .widget_data import fetch_widget_data

DEFAULT_LAYOUT = [
    {"id": "w1", "type": "subscriptions", "col_span": 4, "row_span": 2},
    {"id": "w2", "type": "projects", "col_span": 4, "row_span": 2},
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
    user = request.user
    display_name = user.first_name if user.first_name else user.username
    initials = display_name[0].upper() if display_name else "?"
    return render(request, "spa_dashboard/shell.html", {
        "user_display_name": display_name,
        "user_initials": initials,
    })


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


@login_required
@require_http_methods(["POST"])
def api_subscription_pay(request):
    from finance_hub.models import Account, Subscription, SubscriptionOccurrence
    from transactions.models import Transaction

    user = request.user
    try:
        payload = json.loads((request.body or b"{}").decode("utf-8"))
    except (json.JSONDecodeError, UnicodeDecodeError):
        return JsonResponse({"ok": False, "error": "invalid_json"}, status=400)

    account_id = payload.get("account_id")
    occurrence_id = payload.get("occurrence_id")
    subscription_id = payload.get("subscription_id")
    due_date_raw = (payload.get("due_date") or "").strip()

    if not account_id:
        return JsonResponse({"ok": False, "error": "account_required"}, status=400)

    account = get_object_or_404(Account, id=account_id, owner=user, is_active=True)

    if occurrence_id:
        occurrence = get_object_or_404(
            SubscriptionOccurrence.objects.select_related("subscription"),
            id=occurrence_id,
            owner=user,
        )
    elif subscription_id:
        subscription = get_object_or_404(
            Subscription.objects.select_related("currency", "project", "category", "payee"),
            id=subscription_id,
            owner=user,
        )
        try:
            due_date = date_lib.fromisoformat(due_date_raw) if due_date_raw else subscription.next_due_date
        except ValueError:
            due_date = subscription.next_due_date
        occurrence, _ = SubscriptionOccurrence.objects.get_or_create(
            owner=user,
            subscription=subscription,
            due_date=due_date,
            defaults={"amount": subscription.amount, "currency": subscription.currency},
        )
    else:
        return JsonResponse({"ok": False, "error": "missing_target"}, status=400)

    if occurrence.transaction_id:
        if occurrence.state != SubscriptionOccurrence.State.PAID:
            occurrence.state = SubscriptionOccurrence.State.PAID
            occurrence.save(update_fields=["state"])
        return JsonResponse({"ok": True, "message": "Pagamento già registrato."})

    subscription = occurrence.subscription
    payment_date = timezone.now().date()
    payment_note = f"Pagamento abbonamento {subscription.name} - scadenza {occurrence.due_date.isoformat()}"

    with db_transaction.atomic():
        tx = Transaction.objects.create(
            owner=user,
            tx_type=Transaction.Type.EXPENSE,
            date=payment_date,
            amount=occurrence.amount,
            currency=occurrence.currency,
            account=account,
            project=subscription.project,
            category=subscription.category,
            payee=subscription.payee,
            note=payment_note,
            source_subscription=subscription,
        )
        occurrence.transaction = tx
        occurrence.state = SubscriptionOccurrence.State.PAID
        occurrence.save(update_fields=["transaction", "state"])

        from finance_hub.views import _compute_next_due_date
        if subscription.next_due_date <= occurrence.due_date:
            subscription.next_due_date = _compute_next_due_date(subscription, occurrence.due_date)
            subscription.save(update_fields=["next_due_date"])

    return JsonResponse({"ok": True, "message": "Pagamento registrato."})
