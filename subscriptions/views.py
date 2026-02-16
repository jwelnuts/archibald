from django.contrib.auth.decorators import login_required
from django.shortcuts import get_object_or_404, redirect, render
from django.utils import timezone

from .forms import SubscriptionForm
from .models import Subscription, SubscriptionOccurrence

# Create your views here.
@login_required
def dashboard(request):
    user = request.user
    today = timezone.now().date()
    upcoming = list(
        SubscriptionOccurrence.objects.filter(owner=user, subscription__status=Subscription.Status.ACTIVE)
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
    return render(
        request,
        "subscriptions/dashboard.html",
        {
            "upcoming": upcoming,
            "overdue": overdue,
            "counts": counts,
            "total_due": total_due,
            "next_due_date": next_due_date,
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
