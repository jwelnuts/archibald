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


def _fetch_projects(user, slot):
    from projects.models import Project, SubProject

    active_projects = list(
        Project.objects.filter(owner=user, is_archived=False)
        .prefetch_related("subprojects")
        .order_by("name")[:8]
    )

    projects_serialized = []
    for project in active_projects:
        subs = project.subprojects.filter(is_archived=False)
        counts = {
            "total": subs.count(),
            "in_progress": subs.filter(status=SubProject.Status.IN_PROGRESS).count(),
            "blocked": subs.filter(status=SubProject.Status.BLOCKED).count(),
            "done": subs.filter(status=SubProject.Status.DONE).count(),
            "planned": subs.filter(status=SubProject.Status.PLANNED).count(),
        }
        next_due = (
            subs.exclude(due_date=None)
            .exclude(status=SubProject.Status.DONE)
            .order_by("due_date")
            .values_list("due_date", flat=True)
            .first()
        )
        projects_serialized.append({
            "id": project.id,
            "name": project.name,
            "counts": counts,
            "next_due": next_due.strftime("%d/%m/%Y") if next_due else None,
            "url": f"/projects/view?id={project.id}",
        })

    return {
        "total": len(active_projects),
        "projects": projects_serialized,
    }


def _fetch_transaction_quick(user, slot):
    from transactions.models import Transaction
    from finance_hub.models import Account, Currency
    from projects.models import Category as ProjectCategory, Project

    today = timezone.now().date()
    week_ago = today - timedelta(days=7)

    recent_count = Transaction.objects.filter(
        owner=user, date__gte=week_ago,
    ).count()

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

    projects = list(
        Project.objects.filter(owner=user, is_archived=False)
        .order_by("name")
        .values("id", "name")[:20]
    )
    projects_serialized = [{"id": p["id"], "name": p["name"]} for p in projects]

    categories = list(
        ProjectCategory.objects.filter(owner=user)
        .order_by("name")
        .values("id", "name")[:30]
    )
    categories_serialized = [{"id": c["id"], "name": c["name"]} for c in categories]

    currencies = list(
        Currency.objects.all().order_by("code")
        .values("id", "code")
    )
    currencies_serialized = [{"id": c["id"], "code": c["code"]} for c in currencies]

    tx_types = [
        {"value": "OUT", "label": "Uscita"},
        {"value": "IN", "label": "Entrata"},
        {"value": "XFER", "label": "Trasferimento"},
    ]

    return {
        "recent_count": recent_count,
        "accounts": accounts_serialized,
        "projects": projects_serialized,
        "categories": categories_serialized,
        "currencies": currencies_serialized,
        "tx_types": tx_types,
        "today": today.isoformat(),
    }


WIDGET_FETCHERS = {
    "placeholder": lambda user, slot: {},
    "subscriptions": _fetch_subscriptions,
    "projects": _fetch_projects,
    "transaction_quick": _fetch_transaction_quick,
}


def fetch_widget_data(user, slot):
    fetcher = WIDGET_FETCHERS.get(slot["type"])
    if fetcher is None:
        return {}
    return fetcher(user, slot)
