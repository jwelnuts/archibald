from django.contrib.auth.decorators import login_required
from django.shortcuts import get_object_or_404, redirect, render

from .forms import LabEntryForm
from .models import LabEntry


@login_required
def dashboard(request):
    status_filter = (request.GET.get("status") or "").upper()
    entries = LabEntry.objects.filter(owner=request.user).order_by("-updated_at")
    if status_filter in LabEntry.Status.values:
        entries = entries.filter(status=status_filter)

    status_cards = [
        {
            "code": status,
            "label": label,
            "count": LabEntry.objects.filter(owner=request.user, status=status).count(),
        }
        for status, label in LabEntry.Status.choices
    ]
    return render(
        request,
        "ai_lab/dashboard.html",
        {
            "entries": entries[:100],
            "status_filter": status_filter,
            "status_choices": LabEntry.Status.choices,
            "status_cards": status_cards,
        },
    )


@login_required
def add_item(request):
    if request.method == "POST":
        form = LabEntryForm(request.POST)
        if form.is_valid():
            item = form.save(commit=False)
            item.owner = request.user
            item.save()
            return redirect("/ai-lab/")
    else:
        form = LabEntryForm()
    return render(request, "ai_lab/add_item.html", {"form": form})


@login_required
def update_item(request):
    item_id = request.GET.get("id")
    if not item_id:
        return redirect("/ai-lab/")
    item = get_object_or_404(LabEntry, id=item_id, owner=request.user)
    if request.method == "POST":
        form = LabEntryForm(request.POST, instance=item)
        if form.is_valid():
            form.save()
            return redirect("/ai-lab/")
    else:
        form = LabEntryForm(instance=item)
    return render(request, "ai_lab/update_item.html", {"form": form, "item": item})


@login_required
def remove_item(request):
    item_id = request.GET.get("id")
    if not item_id:
        return redirect("/ai-lab/")
    item = get_object_or_404(LabEntry, id=item_id, owner=request.user)
    if request.method == "POST":
        item.delete()
        return redirect("/ai-lab/")
    return render(request, "ai_lab/remove_item.html", {"item": item})
