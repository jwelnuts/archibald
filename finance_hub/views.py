from datetime import timedelta

from django.contrib.auth.decorators import login_required
from django.db import transaction
from django.db.models import Sum
from django.shortcuts import get_object_or_404, redirect, render
from django.utils import timezone

from .forms import InvoiceForm, QuoteForm, QuoteLineFormSet, WorkOrderForm
from .models import Invoice, Quote, WorkOrder


@login_required
def dashboard(request):
    user = request.user
    today = timezone.now().date()
    next_week = today + timedelta(days=7)

    quote_qs = Quote.objects.filter(owner=user)
    invoice_qs = Invoice.objects.filter(owner=user)
    work_order_qs = WorkOrder.objects.filter(owner=user)

    quote_totals = quote_qs.filter(status__in=[Quote.Status.SENT, Quote.Status.APPROVED]).aggregate(
        total=Sum("total_amount")
    )
    invoice_open_totals = invoice_qs.filter(status__in=[Invoice.Status.ISSUED, Invoice.Status.OVERDUE]).aggregate(
        total=Sum("total_amount")
    )
    invoice_paid_totals = invoice_qs.filter(status=Invoice.Status.PAID).aggregate(total=Sum("total_amount"))
    work_order_pipeline = work_order_qs.filter(status__in=[WorkOrder.Status.OPEN, WorkOrder.Status.IN_PROGRESS]).aggregate(
        est=Sum("estimated_amount"),
        final=Sum("final_amount"),
    )

    expiring_quotes = quote_qs.filter(
        status__in=[Quote.Status.DRAFT, Quote.Status.SENT],
        valid_until__range=(today, next_week),
    ).order_by("valid_until", "id")[:5]
    overdue_invoices = invoice_qs.filter(
        status__in=[Invoice.Status.ISSUED, Invoice.Status.OVERDUE],
        due_date__lt=today,
    ).order_by("due_date", "id")[:5]
    open_work_orders = work_order_qs.filter(
        status__in=[WorkOrder.Status.OPEN, WorkOrder.Status.IN_PROGRESS, WorkOrder.Status.WAITING]
    ).order_by("-start_date", "-id")[:5]

    counts = {
        "quotes_draft": quote_qs.filter(status=Quote.Status.DRAFT).count(),
        "quotes_sent": quote_qs.filter(status=Quote.Status.SENT).count(),
        "quotes_approved": quote_qs.filter(status=Quote.Status.APPROVED).count(),
        "invoices_issued": invoice_qs.filter(status=Invoice.Status.ISSUED).count(),
        "invoices_overdue": invoice_qs.filter(status__in=[Invoice.Status.OVERDUE]).count()
        + invoice_qs.filter(status=Invoice.Status.ISSUED, due_date__lt=today).count(),
        "invoices_paid": invoice_qs.filter(status=Invoice.Status.PAID).count(),
        "orders_open": work_order_qs.filter(status=WorkOrder.Status.OPEN).count(),
        "orders_in_progress": work_order_qs.filter(status=WorkOrder.Status.IN_PROGRESS).count(),
        "orders_done": work_order_qs.filter(status=WorkOrder.Status.DONE).count(),
    }

    return render(
        request,
        "finance_hub/dashboard.html",
        {
            "today": today,
            "next_week": next_week,
            "counts": counts,
            "expiring_quotes": expiring_quotes,
            "overdue_invoices": overdue_invoices,
            "open_work_orders": open_work_orders,
            "quote_pipeline_total": quote_totals.get("total") or 0,
            "invoice_open_total": invoice_open_totals.get("total") or 0,
            "invoice_paid_total": invoice_paid_totals.get("total") or 0,
            "work_order_pipeline_est": work_order_pipeline.get("est") or 0,
            "work_order_pipeline_final": work_order_pipeline.get("final") or 0,
        },
    )


@login_required
def quotes(request):
    rows = (
        Quote.objects.filter(owner=request.user)
        .select_related("customer", "project", "currency")
        .prefetch_related("lines")
        .order_by("-issue_date", "-id")[:100]
    )
    return render(request, "finance_hub/quotes.html", {"rows": rows})


@login_required
def add_quote(request):
    if request.method == "POST":
        form = QuoteForm(request.POST, owner=request.user)
        temp_item = Quote(owner=request.user)
        line_formset = QuoteLineFormSet(request.POST, instance=temp_item, prefix="lines")
        if form.is_valid() and line_formset.is_valid():
            with transaction.atomic():
                item = form.save(commit=False)
                item.owner = request.user
                item.save()
                line_formset.instance = item
                line_items = line_formset.save(commit=False)
                for deleted in line_formset.deleted_objects:
                    deleted.delete()
                for idx, line in enumerate(line_items, start=1):
                    line.owner = request.user
                    line.quote = item
                    if not line.row_order:
                        line.row_order = idx
                    line.save()
                item.refresh_totals_from_lines(save=True)
            return redirect("/finance/quotes/")
    else:
        form = QuoteForm(owner=request.user)
        line_formset = QuoteLineFormSet(instance=Quote(owner=request.user), prefix="lines")
    return render(request, "finance_hub/quote_form.html", {"form": form, "line_formset": line_formset, "mode": "add"})


@login_required
def update_quote(request):
    item_id = request.GET.get("id")
    item = None
    if item_id:
        item = get_object_or_404(Quote, id=item_id, owner=request.user)
        if request.method == "POST":
            form = QuoteForm(request.POST, instance=item, owner=request.user)
            line_formset = QuoteLineFormSet(request.POST, instance=item, prefix="lines")
            if form.is_valid() and line_formset.is_valid():
                with transaction.atomic():
                    saved_item = form.save()
                    line_items = line_formset.save(commit=False)
                    for deleted in line_formset.deleted_objects:
                        deleted.delete()
                    for idx, line in enumerate(line_items, start=1):
                        line.owner = request.user
                        line.quote = saved_item
                        if not line.row_order:
                            line.row_order = idx
                        line.save()
                    saved_item.refresh_totals_from_lines(save=True)
                return redirect("/finance/quotes/")
        else:
            form = QuoteForm(instance=item, owner=request.user)
            line_formset = QuoteLineFormSet(instance=item, prefix="lines")
        return render(
            request,
            "finance_hub/quote_form.html",
            {"form": form, "line_formset": line_formset, "mode": "update", "item": item},
        )
    rows = Quote.objects.filter(owner=request.user).order_by("-issue_date", "-id")[:20]
    return render(request, "finance_hub/quote_form.html", {"rows": rows, "mode": "select"})


@login_required
def remove_quote(request):
    item_id = request.GET.get("id")
    item = None
    if item_id:
        item = get_object_or_404(Quote, id=item_id, owner=request.user)
        if request.method == "POST":
            item.delete()
            return redirect("/finance/quotes/")
    rows = Quote.objects.filter(owner=request.user).order_by("-issue_date", "-id")[:20]
    return render(request, "finance_hub/quote_remove.html", {"item": item, "rows": rows})


@login_required
def invoices(request):
    rows = Invoice.objects.filter(owner=request.user).select_related(
        "quote", "customer", "project", "account", "currency"
    ).order_by("-issue_date", "-id")[:100]
    return render(request, "finance_hub/invoices.html", {"rows": rows})


@login_required
def add_invoice(request):
    if request.method == "POST":
        form = InvoiceForm(request.POST, owner=request.user)
        if form.is_valid():
            item = form.save(commit=False)
            item.owner = request.user
            item.save()
            return redirect("/finance/invoices/")
    else:
        form = InvoiceForm(owner=request.user)
    return render(request, "finance_hub/invoice_form.html", {"form": form, "mode": "add"})


@login_required
def update_invoice(request):
    item_id = request.GET.get("id")
    item = None
    if item_id:
        item = get_object_or_404(Invoice, id=item_id, owner=request.user)
        if request.method == "POST":
            form = InvoiceForm(request.POST, instance=item, owner=request.user)
            if form.is_valid():
                form.save()
                return redirect("/finance/invoices/")
        else:
            form = InvoiceForm(instance=item, owner=request.user)
        return render(request, "finance_hub/invoice_form.html", {"form": form, "mode": "update", "item": item})
    rows = Invoice.objects.filter(owner=request.user).order_by("-issue_date", "-id")[:20]
    return render(request, "finance_hub/invoice_form.html", {"rows": rows, "mode": "select"})


@login_required
def remove_invoice(request):
    item_id = request.GET.get("id")
    item = None
    if item_id:
        item = get_object_or_404(Invoice, id=item_id, owner=request.user)
        if request.method == "POST":
            item.delete()
            return redirect("/finance/invoices/")
    rows = Invoice.objects.filter(owner=request.user).order_by("-issue_date", "-id")[:20]
    return render(request, "finance_hub/invoice_remove.html", {"item": item, "rows": rows})


@login_required
def work_orders(request):
    rows = WorkOrder.objects.filter(owner=request.user).select_related("customer", "project", "account", "currency").order_by(
        "-start_date", "-id"
    )[:100]
    return render(request, "finance_hub/work_orders.html", {"rows": rows})


@login_required
def add_work_order(request):
    if request.method == "POST":
        form = WorkOrderForm(request.POST, owner=request.user)
        if form.is_valid():
            item = form.save(commit=False)
            item.owner = request.user
            item.save()
            return redirect("/finance/work-orders/")
    else:
        form = WorkOrderForm(owner=request.user)
    return render(request, "finance_hub/work_order_form.html", {"form": form, "mode": "add"})


@login_required
def update_work_order(request):
    item_id = request.GET.get("id")
    item = None
    if item_id:
        item = get_object_or_404(WorkOrder, id=item_id, owner=request.user)
        if request.method == "POST":
            form = WorkOrderForm(request.POST, instance=item, owner=request.user)
            if form.is_valid():
                form.save()
                return redirect("/finance/work-orders/")
        else:
            form = WorkOrderForm(instance=item, owner=request.user)
        return render(request, "finance_hub/work_order_form.html", {"form": form, "mode": "update", "item": item})
    rows = WorkOrder.objects.filter(owner=request.user).order_by("-start_date", "-id")[:20]
    return render(request, "finance_hub/work_order_form.html", {"rows": rows, "mode": "select"})


@login_required
def remove_work_order(request):
    item_id = request.GET.get("id")
    item = None
    if item_id:
        item = get_object_or_404(WorkOrder, id=item_id, owner=request.user)
        if request.method == "POST":
            item.delete()
            return redirect("/finance/work-orders/")
    rows = WorkOrder.objects.filter(owner=request.user).order_by("-start_date", "-id")[:20]
    return render(request, "finance_hub/work_order_remove.html", {"item": item, "rows": rows})
