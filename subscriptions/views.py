from calendar import monthrange
from datetime import date, timedelta

from django.contrib.auth.decorators import login_required
from django.db import transaction
from django.shortcuts import get_object_or_404, redirect, render
from django.utils import timezone
from django.views.decorators.http import require_POST

from transactions.models import Transaction

from .forms import SubscriptionForm
from .models import Account, Subscription, SubscriptionOccurrence


def _add_months(anchor: date, months: int) -> date:
    month_index = anchor.month - 1 + months
    year = anchor.year + month_index // 12
    month = month_index % 12 + 1
    day = min(anchor.day, monthrange(year, month)[1])
    return date(year, month, day)


def _compute_next_due_date(subscription: Subscription, paid_due_date: date) -> date:
    step = max(subscription.interval or 1, 1)
    if subscription.interval_unit == Subscription.IntervalUnit.DAY:
        return paid_due_date + timedelta(days=step)
    if subscription.interval_unit == Subscription.IntervalUnit.WEEK:
        return paid_due_date + timedelta(days=step * 7)
    if subscription.interval_unit == Subscription.IntervalUnit.YEAR:
        return _add_months(paid_due_date, step * 12)
    return _add_months(paid_due_date, step)

# Create your views here.
@login_required
def dashboard(request):
    user = request.user
    today = timezone.now().date()
    upcoming = list(
        SubscriptionOccurrence.objects.filter(
            owner=user,
            subscription__status=Subscription.Status.ACTIVE,
            state=SubscriptionOccurrence.State.PLANNED,
        )
        .select_related("subscription")
        .order_by("due_date")[:5]
    )
    using_occurrences = True
    if not upcoming:
        upcoming = list(
            Subscription.objects.filter(owner=user, status=Subscription.Status.ACTIVE)
            .order_by("next_due_date")[:5]
        )
        using_occurrences = False
    overdue = list(
        SubscriptionOccurrence.objects.filter(
            owner=user,
            due_date__lt=today,
            subscription__status=Subscription.Status.ACTIVE,
            state=SubscriptionOccurrence.State.PLANNED,
        )
        .select_related("subscription")
        .order_by("-due_date")[:5]
    )
    if not overdue:
        overdue = list(
            Subscription.objects.filter(
                owner=user,
                next_due_date__lt=today,
                status=Subscription.Status.ACTIVE,
            )
            .order_by("-next_due_date")[:5]
        )
    total_due = None
    next_due_date = None
    if upcoming:
        if using_occurrences:
            total_due = sum([item.amount for item in upcoming])
            next_due_date = upcoming[0].due_date
        else:
            total_due = sum([item.amount for item in upcoming])
            next_due_date = upcoming[0].next_due_date
    counts = {
        "active": Subscription.objects.filter(owner=user, status=Subscription.Status.ACTIVE).count(),
        "paused": Subscription.objects.filter(owner=user, status=Subscription.Status.PAUSED).count(),
        "canceled": Subscription.objects.filter(owner=user, status=Subscription.Status.CANCELED).count(),
    }
    accounts = Account.objects.filter(owner=user, is_active=True).order_by("name")
    return render(
        request,
        "subscriptions/dashboard.html",
        {
            "upcoming": upcoming,
            "overdue": overdue,
            "counts": counts,
            "total_due": total_due,
            "next_due_date": next_due_date,
            "accounts": accounts,
        },
    )

@login_required
def add_sub(request):
    if request.method == "POST":
        form = SubscriptionForm(request.POST, owner=request.user)
        if form.is_valid():
            sub = form.save(commit=False)
            sub.owner = request.user
            if not sub.currency_id:
                from .models import Currency
                sub.currency, _ = Currency.objects.get_or_create(code="EUR", defaults={"name": "Euro"})
            sub.save()
            form.save_m2m()
            return redirect("/subs/")
    else:
        form = SubscriptionForm(owner=request.user)
    return render(request, "subscriptions/add_sub.html", {"form": form})

@login_required
def remove_sub(request):
    sub_id = request.GET.get("id")
    sub = None
    if sub_id:
        sub = get_object_or_404(Subscription, id=sub_id, owner=request.user)
        if request.method == "POST":
            sub.delete()
            return redirect("/subs/")
    subs = Subscription.objects.filter(owner=request.user).order_by("name")[:20]
    return render(request, "subscriptions/remove_sub.html", {"sub": sub, "subs": subs})

@login_required
def update_sub(request):
    sub_id = request.GET.get("id")
    sub = None
    if sub_id:
        sub = get_object_or_404(Subscription, id=sub_id, owner=request.user)
        if request.method == "POST":
            if request.POST.get("action") == "cancel":
                sub.status = Subscription.Status.CANCELED
                sub.save(update_fields=["status"])
                return redirect("/subs/")
            form = SubscriptionForm(request.POST, instance=sub, owner=request.user)
            if form.is_valid():
                sub = form.save(commit=False)
                if not sub.currency_id:
                    from .models import Currency
                    sub.currency, _ = Currency.objects.get_or_create(code="EUR", defaults={"name": "Euro"})
                sub.save()
                form.save_m2m()
                return redirect("/subs/")
        else:
            form = SubscriptionForm(instance=sub, owner=request.user)
        return render(request, "subscriptions/update_sub.html", {"form": form, "sub": sub})
    subs = Subscription.objects.filter(owner=request.user).order_by("name")[:20]
    return render(request, "subscriptions/update_sub.html", {"subs": subs})


@login_required
@require_POST
def pay_subscription(request):
    user = request.user
    account_id = request.POST.get("account_id")
    occurrence_id = request.POST.get("occurrence_id")
    subscription_id = request.POST.get("subscription_id")
    due_date_raw = (request.POST.get("due_date") or "").strip()

    if not account_id:
        return redirect("/subs/")

    account = get_object_or_404(Account, id=account_id, owner=user, is_active=True)

    occurrence = None
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
            due_date = date.fromisoformat(due_date_raw) if due_date_raw else subscription.next_due_date
        except ValueError:
            due_date = subscription.next_due_date
        occurrence, _ = SubscriptionOccurrence.objects.get_or_create(
            owner=user,
            subscription=subscription,
            due_date=due_date,
            defaults={
                "amount": subscription.amount,
                "currency": subscription.currency,
            },
        )
    else:
        return redirect("/subs/")

    if occurrence.transaction_id:
        if occurrence.state != SubscriptionOccurrence.State.PAID:
            occurrence.state = SubscriptionOccurrence.State.PAID
            occurrence.save(update_fields=["state"])
        return redirect("/subs/")

    subscription = occurrence.subscription
    payment_date = timezone.now().date()
    payment_note = f"Pagamento abbonamento {subscription.name} - scadenza {occurrence.due_date.isoformat()}"

    with transaction.atomic():
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

        if subscription.next_due_date <= occurrence.due_date:
            subscription.next_due_date = _compute_next_due_date(subscription, occurrence.due_date)
            subscription.save(update_fields=["next_due_date"])

    return redirect("/subs/")
