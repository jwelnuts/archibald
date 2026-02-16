from django.contrib.auth.decorators import login_required
from django.db.models import Sum
from django.shortcuts import get_object_or_404, redirect, render

from .forms import OutcomeForm
from transactions.models import Transaction
from projects.models import Project

# Create your views here.
@login_required
def dashboard(request):
    user = request.user
    recent = (
        Transaction.objects.filter(owner=user, tx_type=Transaction.Type.EXPENSE)
        .select_related("payee", "currency")
        .order_by("-date")[:5]
    )
    totals = Transaction.objects.filter(owner=user, tx_type=Transaction.Type.EXPENSE).aggregate(
        total_amount=Sum("amount")
    )
    counts = {
        "total": Transaction.objects.filter(owner=user, tx_type=Transaction.Type.EXPENSE).count(),
        "with_project": Transaction.objects.filter(
            owner=user, tx_type=Transaction.Type.EXPENSE, project__isnull=False
        ).count(),
        "with_category": Transaction.objects.filter(
            owner=user, tx_type=Transaction.Type.EXPENSE, category__isnull=False
        ).count(),
    }
    return render(
        request,
        "outcome/dashboard.html",
        {
            "recent": recent,
            "totals": totals,
            "counts": counts,
        },
    )


@login_required
def add_outcome(request):
    if request.method == "POST":
        form = OutcomeForm(request.POST, owner=request.user)
        if form.is_valid():
            tx = form.save(commit=False)
            tx.owner = request.user
            tx.tx_type = Transaction.Type.EXPENSE
            tx.save()
            form.save_m2m()
            return redirect("/outcome/")
    else:
        initial = {}
        project_id = request.GET.get("project")
        if project_id:
            project = get_object_or_404(Project, id=project_id, owner=request.user)
            initial["project"] = project
        form = OutcomeForm(owner=request.user, initial=initial)
    return render(request, "outcome/add_outcome.html", {"form": form})


@login_required
def remove_outcome(request):
    tx_id = request.GET.get("id")
    tx = None
    if tx_id:
        tx = get_object_or_404(
            Transaction,
            id=tx_id,
            owner=request.user,
            tx_type=Transaction.Type.EXPENSE,
        )
        if request.method == "POST":
            tx.delete()
            return redirect("/outcome/")
    txs = Transaction.objects.filter(owner=request.user, tx_type=Transaction.Type.EXPENSE).order_by("-date")[:20]
    return render(request, "outcome/remove_outcome.html", {"tx": tx, "txs": txs})


@login_required
def update_outcome(request):
    tx_id = request.GET.get("id")
    tx = None
    if tx_id:
        tx = get_object_or_404(
            Transaction,
            id=tx_id,
            owner=request.user,
            tx_type=Transaction.Type.EXPENSE,
        )
        if request.method == "POST":
            form = OutcomeForm(request.POST, instance=tx, owner=request.user)
            if form.is_valid():
                form.save()
                return redirect("/outcome/")
        else:
            form = OutcomeForm(instance=tx, owner=request.user)
        return render(request, "outcome/update_outcome.html", {"form": form, "tx": tx})
    txs = Transaction.objects.filter(owner=request.user, tx_type=Transaction.Type.EXPENSE).order_by("-date")[:20]
    return render(request, "outcome/update_outcome.html", {"txs": txs})
