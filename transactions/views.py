from django.contrib.auth.decorators import login_required
from django.db.models import Sum
from django.shortcuts import render

from .models import Transaction


@login_required
def dashboard(request):
    user = request.user
    qs = Transaction.objects.filter(owner=user).select_related("payee", "currency", "account")

    tx_type = request.GET.get("type")
    if tx_type in {Transaction.Type.INCOME, Transaction.Type.EXPENSE, Transaction.Type.TRANSFER}:
        qs = qs.filter(tx_type=tx_type)

    date_from = request.GET.get("from")
    if date_from:
        qs = qs.filter(date__gte=date_from)
    date_to = request.GET.get("to")
    if date_to:
        qs = qs.filter(date__lte=date_to)

    qs = qs.order_by("-date", "-created_at")
    recent = qs[:50]

    totals = (
        Transaction.objects.filter(owner=user)
        .values("tx_type")
        .annotate(total=Sum("amount"))
    )
    totals_map = {row["tx_type"]: row["total"] for row in totals}

    counts = {
        "all": Transaction.objects.filter(owner=user).count(),
        "income": Transaction.objects.filter(owner=user, tx_type=Transaction.Type.INCOME).count(),
        "expense": Transaction.objects.filter(owner=user, tx_type=Transaction.Type.EXPENSE).count(),
        "transfer": Transaction.objects.filter(owner=user, tx_type=Transaction.Type.TRANSFER).count(),
    }

    return render(
        request,
        "transactions/dashboard.html",
        {
            "recent": recent,
            "counts": counts,
            "totals": totals_map,
            "filters": {"type": tx_type or "", "from": date_from or "", "to": date_to or ""},
        },
    )
