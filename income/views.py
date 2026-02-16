from django.contrib.auth.decorators import login_required
from django.db.models import Sum
from django.shortcuts import get_object_or_404, redirect, render

from .forms import IncomeForm
from transactions.models import Transaction
from projects.models import Project

# Create your views here.
@login_required
def dashboard(request):
    user = request.user
    recent = (
        Transaction.objects.filter(owner=user, tx_type=Transaction.Type.INCOME)
        .select_related("income_source", "currency")
        .order_by("-date")[:5]
    )
    totals = Transaction.objects.filter(owner=user, tx_type=Transaction.Type.INCOME).aggregate(
        total_amount=Sum("amount")
    )
    counts = {
        "total": Transaction.objects.filter(owner=user, tx_type=Transaction.Type.INCOME).count(),
        "with_project": Transaction.objects.filter(
            owner=user, tx_type=Transaction.Type.INCOME, project__isnull=False
        ).count(),
        "with_category": Transaction.objects.filter(
            owner=user, tx_type=Transaction.Type.INCOME, category__isnull=False
        ).count(),
    }
    return render(
        request,
        "income/dashboard.html",
        {
            "recent": recent,
            "totals": totals,
            "counts": counts,
        },
    )


@login_required
def add_income(request):
    if request.method == "POST":
        form = IncomeForm(request.POST, owner=request.user)
        if form.is_valid():
            tx = form.save(commit=False)
            tx.owner = request.user
            tx.tx_type = Transaction.Type.INCOME
            tx.save()
            form.save_m2m()
            return redirect("/income/")
    else:
        initial = {}
        project_id = request.GET.get("project")
        if project_id:
            project = get_object_or_404(Project, id=project_id, owner=request.user)
            initial["project"] = project
        form = IncomeForm(owner=request.user, initial=initial)
    return render(request, "income/add_income.html", {"form": form})


@login_required
def remove_income(request):
    tx_id = request.GET.get("id")
    tx = None
    if tx_id:
        tx = get_object_or_404(
            Transaction,
            id=tx_id,
            owner=request.user,
            tx_type=Transaction.Type.INCOME,
        )
        if request.method == "POST":
            tx.delete()
            return redirect("/income/")
    txs = (
        Transaction.objects.filter(owner=request.user, tx_type=Transaction.Type.INCOME)
        .select_related("income_source", "currency")
        .order_by("-date")[:20]
    )
    return render(request, "income/remove_income.html", {"tx": tx, "txs": txs})


@login_required
def update_income(request):
    tx_id = request.GET.get("id")
    tx = None
    if tx_id:
        tx = get_object_or_404(
            Transaction,
            id=tx_id,
            owner=request.user,
            tx_type=Transaction.Type.INCOME,
        )
        if request.method == "POST":
            form = IncomeForm(request.POST, instance=tx, owner=request.user)
            if form.is_valid():
                form.save()
                return redirect("/income/")
        else:
            form = IncomeForm(instance=tx, owner=request.user)
        return render(request, "income/update_income.html", {"form": form, "tx": tx})
    txs = (
        Transaction.objects.filter(owner=request.user, tx_type=Transaction.Type.INCOME)
        .select_related("income_source", "currency")
        .order_by("-date")[:20]
    )
    return render(request, "income/update_income.html", {"txs": txs})
