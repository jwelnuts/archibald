from django.utils import timezone
from datetime import timedelta


def _fetch_subscriptions(user, slot):
    from finance_hub.models import Subscription, SubscriptionOccurrence

    today = timezone.now().date()

    counts = {
        "active": Subscription.objects.filter(owner=user, status=Subscription.Status.ACTIVE).count(),
        "paused": Subscription.objects.filter(owner=user, status=Subscription.Status.PAUSED).count(),
        "canceled": Subscription.objects.filter(owner=user, status=Subscription.Status.CANCELED).count(),
    }

    upcoming = list(
        SubscriptionOccurrence.objects.filter(
            owner=user,
            subscription__status=Subscription.Status.ACTIVE,
            state=SubscriptionOccurrence.State.PLANNED,
        )
        .select_related("subscription", "currency")
        .order_by("due_date")[:5]
    )

    using_occurrences = True
    if not upcoming:
        upcoming = list(
            Subscription.objects.filter(
                owner=user,
                status=Subscription.Status.ACTIVE,
                next_due_date__gte=today,
            )
            .select_related("currency")
            .order_by("next_due_date")[:5]
        )
        using_occurrences = False

    upcoming_serialized = []
    for item in upcoming:
        if using_occurrences:
            upcoming_serialized.append({
                "date": item.due_date.strftime("%d/%m/%Y"),
                "due_date_raw": item.due_date.isoformat(),
                "occurrence_id": item.id,
                "subscription_id": None,
                "name": item.subscription.name,
                "amount": str(item.amount),
                "currency": item.currency.code if item.currency else "EUR",
            })
        else:
            d = item.next_due_date
            upcoming_serialized.append({
                "date": d.strftime("%d/%m/%Y") if d else "—",
                "due_date_raw": d.isoformat() if d else "",
                "occurrence_id": None,
                "subscription_id": item.id,
                "name": item.name,
                "amount": str(item.amount),
                "currency": item.currency.code if item.currency else "EUR",
            })

    total_due = sum(float(s["amount"]) for s in upcoming_serialized) if upcoming_serialized else 0
    next_due_date = upcoming_serialized[0]["date"] if upcoming_serialized else None

    from finance_hub.models import Account
    accounts = list(
        Account.objects.filter(owner=user, is_active=True)
        .select_related("currency")
        .order_by("name")
        .values("id", "name", "currency__code")
    )
    accounts_serialized = [
        {"id": a["id"], "name": a["name"], "currency": a["currency__code"] or "EUR"}
        for a in accounts
    ]

    return {
        "counts": counts,
        "upcoming": upcoming_serialized,
        "total_due": f"{total_due:.2f}",
        "next_due_date": next_due_date,
        "accounts": accounts_serialized,
    }


WIDGET_FETCHERS = {
    "placeholder": lambda user, slot: {},
    "subscriptions": _fetch_subscriptions,
}


def fetch_widget_data(user, slot):
    fetcher = WIDGET_FETCHERS.get(slot["type"])
    if fetcher is None:
        return {}
    return fetcher(user, slot)
