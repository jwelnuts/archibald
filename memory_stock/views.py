from django.contrib.auth.decorators import login_required
from django.shortcuts import get_object_or_404, redirect, render

from .forms import MemoryStockItemForm
from .models import MemoryStockItem


@login_required
def dashboard(request):
    show_archived = (request.GET.get("archived") or "").strip().lower() in {"1", "true", "yes", "on"}
    query = (request.GET.get("q") or "").strip()

    qs = MemoryStockItem.objects.filter(owner=request.user)
    if not show_archived:
        qs = qs.filter(is_archived=False)
    if query:
        qs = qs.filter(title__icontains=query)

    rows = list(qs.order_by("-created_at")[:120])

    email_captures = list(
        MemoryStockItem.objects.filter(owner=request.user, is_archived=False)
        .exclude(source_action="")
        .order_by("-created_at")[:20]
    )
    from collections import Counter
    action_counts = Counter(
        MemoryStockItem.objects.filter(owner=request.user, is_archived=False)
        .exclude(source_action="")
        .values_list("source_action", flat=True)
    )

    return render(
        request,
        "memory_stock/dashboard.html",
        {
            "rows": rows,
            "show_archived": show_archived,
            "query": query,
            "email_captures": email_captures,
            "action_counts": dict(action_counts),
        },
    )


@login_required
def add_item(request):
    if request.method == "POST":
        form = MemoryStockItemForm(request.POST)
        if form.is_valid():
            item = form.save(commit=False)
            item.owner = request.user
            item.save()
            return redirect("/memory-stock/")
    else:
        form = MemoryStockItemForm()
    return render(request, "memory_stock/add_item.html", {"form": form})


@login_required
def update_item(request):
    item_id = request.GET.get("id")
    if not item_id:
        return redirect("/memory-stock/")
    item = get_object_or_404(MemoryStockItem, id=item_id, owner=request.user)

    if request.method == "POST":
        form = MemoryStockItemForm(request.POST, instance=item)
        if form.is_valid():
            form.save()
            return redirect("/memory-stock/")
    else:
        form = MemoryStockItemForm(instance=item)

    return render(request, "memory_stock/update_item.html", {"form": form, "item": item})


@login_required
def remove_item(request):
    item_id = request.GET.get("id")
    if not item_id:
        return redirect("/memory-stock/")
    item = get_object_or_404(MemoryStockItem, id=item_id, owner=request.user)
    if request.method == "POST":
        item.delete()
        return redirect("/memory-stock/")
    return render(request, "memory_stock/remove_item.html", {"item": item})


@login_required
def toggle_archive(request):
    if request.method != "POST":
        return redirect("/memory-stock/")
    item = get_object_or_404(MemoryStockItem, id=request.POST.get("id"), owner=request.user)
    item.is_archived = not item.is_archived
    item.save(update_fields=["is_archived", "updated_at"])
    return redirect("/memory-stock/")
