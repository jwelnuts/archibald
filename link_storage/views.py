from django.contrib.auth.decorators import login_required
from django.shortcuts import get_object_or_404, redirect, render

from .forms import LinkForm
from .models import Link


def _format_value(value):
    if value is None:
        return "-"
    if hasattr(value, "isoformat"):
        try:
            return value.isoformat()
        except Exception:
            return str(value)
    return str(value)


@login_required
def dashboard(request):
    queryset = Link.objects.filter(owner=request.user).order_by("-created_at")[:50]
    display_fields = ["url", "category", "importance", "note"]
    rows = [
        {
            "id": item.id,
            "values": [_format_value(getattr(item, field, None)) for field in display_fields],
        }
        for item in queryset
    ]
    return render(
        request,
        "link_storage/dashboard.html",
        {
            "rows": rows,
            "display_fields": display_fields,
        },
    )


@login_required
def add_item(request):
    if request.method == "POST":
        form = LinkForm(request.POST)
        if form.is_valid():
            item = form.save(commit=False)
            item.owner = request.user
            item.save()
            return redirect("/link_storage/")
    else:
        form = LinkForm()
    return render(request, "link_storage/add_item.html", {"form": form})


@login_required
def update_item(request):
    item_id = request.GET.get("id")
    if not item_id:
        return redirect("/link_storage/")
    item = get_object_or_404(Link, id=item_id, owner=request.user)
    if request.method == "POST":
        form = LinkForm(request.POST, instance=item)
        if form.is_valid():
            form.save()
            return redirect("/link_storage/")
    else:
        form = LinkForm(instance=item)
    return render(
        request,
        "link_storage/update_item.html",
        {
            "form": form,
            "item": item,
        },
    )


@login_required
def remove_item(request):
    item_id = request.GET.get("id")
    if not item_id:
        return redirect("/link_storage/")
    item = get_object_or_404(Link, id=item_id, owner=request.user)
    if request.method == "POST":
        item.delete()
        return redirect("/link_storage/")
    return render(
        request,
        "link_storage/remove_item.html",
        {"item": item},
    )
