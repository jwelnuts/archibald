from django.contrib.auth.decorators import login_required
from django.shortcuts import get_object_or_404, redirect, render

from .forms import OutcomeForm
from transactions.models import Transaction
from projects.models import Project

# Create your views here.
@login_required
def dashboard(request):
    return redirect("/transactions/?tx_type=OUT")


@login_required
def add_outcome(request):
    if request.method == "POST":
        form = OutcomeForm(request.POST, request.FILES, owner=request.user)
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
            form = OutcomeForm(request.POST, request.FILES, instance=tx, owner=request.user)
            if form.is_valid():
                form.save()
                return redirect("/outcome/")
        else:
            form = OutcomeForm(instance=tx, owner=request.user)
        return render(request, "outcome/update_outcome.html", {"form": form, "tx": tx})
    txs = Transaction.objects.filter(owner=request.user, tx_type=Transaction.Type.EXPENSE).order_by("-date")[:20]
    return render(request, "outcome/update_outcome.html", {"txs": txs})
