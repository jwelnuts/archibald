from django.contrib.auth.decorators import login_required
from django.db.models import Sum
from django.shortcuts import render

from .models import Transaction


@login_required
def dashboard(request):
    user = request.user
    qs = (
        Transaction.objects.filter(owner=user)
        .select_related("payee", "income_source", "currency", "account", "project", "category")
    )

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
    grid_rows = []
    for tx in recent:
        update_url = ""
        remove_url = ""
        counterparty = "-"
        if tx.tx_type == Transaction.Type.INCOME:
            update_url = f"/income/api/update?id={tx.id}"
            remove_url = f"/income/api/remove?id={tx.id}"
            if tx.income_source:
                counterparty = tx.income_source.name
            elif tx.payee:
                counterparty = tx.payee.name
        elif tx.tx_type == Transaction.Type.EXPENSE:
            update_url = f"/outcome/api/update?id={tx.id}"
            remove_url = f"/outcome/api/remove?id={tx.id}"
            if tx.payee:
                counterparty = tx.payee.name

        grid_rows.append(
            {
                "id": tx.id,
                "date": tx.date.isoformat(),
                "type": tx.get_tx_type_display(),
                "type_code": tx.tx_type,
                "counterparty": counterparty,
                "note": tx.note or "",
                "amount": str(tx.amount),
                "currency": tx.currency.code,
                "account": str(tx.account),
                "project": tx.project.name if tx.project else "-",
                "category": tx.category.name if tx.category else "-",
                "attachment_url": tx.attachment.url if tx.attachment else "",
                "update_url": update_url,
                "remove_url": remove_url,
                "filter_type_url": f"/transactions/?type={tx.tx_type}",
            }
        )

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
            "grid_rows": grid_rows,
        },
    )
