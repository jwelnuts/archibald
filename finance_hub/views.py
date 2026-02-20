from datetime import timedelta
from decimal import Decimal

from contacts.models import Contact
from contacts.services import ensure_legacy_records_for_contact, upsert_contact
from django.contrib.auth.decorators import login_required
from django.db import transaction
from django.db.models import Sum
from django.shortcuts import get_object_or_404, redirect, render
from django.utils import timezone

from .forms import InvoiceForm, QuoteForm, QuoteLineFormSet, VatCodeForm, WorkOrderForm
from .models import Invoice, Quote, VatCode, WorkOrder


def _sync_contact_from_customer(owner, customer):
    if owner is None or customer is None:
        return
    contact = upsert_contact(
        owner,
        customer.name,
        entity_type=Contact.EntityType.HYBRID,
        email=customer.email,
        phone=customer.phone,
        notes=customer.notes,
        roles={"role_customer"},
    )
    ensure_legacy_records_for_contact(contact)


def _ensure_default_vat_codes(user):
    defaults = [
        ("22", "IVA ordinaria", Decimal("22.00")),
        ("10", "IVA ridotta", Decimal("10.00")),
        ("4", "IVA super ridotta", Decimal("4.00")),
        ("ESENTE", "Operazione esente", Decimal("0.00")),
    ]
    for code, description, rate in defaults:
        VatCode.objects.get_or_create(
            owner=user,
            code=code,
            defaults={
                "description": description,
                "rate": rate,
                "is_active": True,
            },
        )


def _vat_rates_payload(user):
    rows = VatCode.objects.filter(owner=user, is_active=True).order_by("rate", "code")
    return [
        {
            "id": row.id,
            "code": row.code,
            "rate": str(row.rate),
            "description": row.description,
        }
        for row in rows
    ]


def _apply_quote_vat_to_line(line, quote):
    vat_rate = quote.vat_code.rate if quote.vat_code_id else Decimal("0.00")
    multiplier = Decimal("1.00") + (vat_rate / Decimal("100.00"))
    line.vat_code = quote.vat_code.code if quote.vat_code_id else ""
    line.gross_amount = ((line.net_amount or Decimal("0.00")) * multiplier).quantize(Decimal("0.01"))


def _sync_quote_lines_vat(quote):
    for line in quote.lines.all():
        _apply_quote_vat_to_line(line, quote)
        line.save(update_fields=["vat_code", "gross_amount", "updated_at"])


@login_required
def dashboard(request):
    user = request.user
    _ensure_default_vat_codes(user)
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
    _ensure_default_vat_codes(request.user)
    rows = (
        Quote.objects.filter(owner=request.user)
        .select_related("customer", "project", "currency", "vat_code")
        .prefetch_related("lines")
        .order_by("-issue_date", "-id")[:100]
    )
    return render(request, "finance_hub/quotes.html", {"rows": rows})


@login_required
def add_quote(request):
    _ensure_default_vat_codes(request.user)
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
                    _apply_quote_vat_to_line(line, item)
                    line.save()
                _sync_quote_lines_vat(item)
                item.refresh_totals_from_lines(save=True)
                _sync_contact_from_customer(request.user, item.customer)
            return redirect("/finance/quotes/")
    else:
        form = QuoteForm(owner=request.user)
        line_formset = QuoteLineFormSet(instance=Quote(owner=request.user), prefix="lines")
    return render(
        request,
        "finance_hub/quote_form.html",
        {
            "form": form,
            "line_formset": line_formset,
            "mode": "add",
            "vat_rates": _vat_rates_payload(request.user),
        },
    )


@login_required
def update_quote(request):
    _ensure_default_vat_codes(request.user)
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
                        _apply_quote_vat_to_line(line, saved_item)
                        line.save()
                    _sync_quote_lines_vat(saved_item)
                    saved_item.refresh_totals_from_lines(save=True)
                    _sync_contact_from_customer(request.user, saved_item.customer)
                return redirect("/finance/quotes/")
        else:
            form = QuoteForm(instance=item, owner=request.user)
            line_formset = QuoteLineFormSet(instance=item, prefix="lines")
        return render(
            request,
            "finance_hub/quote_form.html",
            {
                "form": form,
                "line_formset": line_formset,
                "mode": "update",
                "item": item,
                "vat_rates": _vat_rates_payload(request.user),
            },
        )
    rows = Quote.objects.filter(owner=request.user).order_by("-issue_date", "-id")[:20]
    return render(request, "finance_hub/quote_form.html", {"rows": rows, "mode": "select"})


@login_required
def remove_quote(request):
    _ensure_default_vat_codes(request.user)
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
    _ensure_default_vat_codes(request.user)
    rows = Invoice.objects.filter(owner=request.user).select_related(
        "quote", "customer", "project", "account", "currency"
    ).order_by("-issue_date", "-id")[:100]
    return render(request, "finance_hub/invoices.html", {"rows": rows})


@login_required
def add_invoice(request):
    _ensure_default_vat_codes(request.user)
    if request.method == "POST":
        form = InvoiceForm(request.POST, owner=request.user)
        if form.is_valid():
            item = form.save(commit=False)
            item.owner = request.user
            item.save()
            _sync_contact_from_customer(request.user, item.customer)
            return redirect("/finance/invoices/")
    else:
        form = InvoiceForm(owner=request.user)
    return render(request, "finance_hub/invoice_form.html", {"form": form, "mode": "add"})


@login_required
def update_invoice(request):
    _ensure_default_vat_codes(request.user)
    item_id = request.GET.get("id")
    item = None
    if item_id:
        item = get_object_or_404(Invoice, id=item_id, owner=request.user)
        if request.method == "POST":
            form = InvoiceForm(request.POST, instance=item, owner=request.user)
            if form.is_valid():
                saved_item = form.save()
                _sync_contact_from_customer(request.user, saved_item.customer)
                return redirect("/finance/invoices/")
        else:
            form = InvoiceForm(instance=item, owner=request.user)
        return render(request, "finance_hub/invoice_form.html", {"form": form, "mode": "update", "item": item})
    rows = Invoice.objects.filter(owner=request.user).order_by("-issue_date", "-id")[:20]
    return render(request, "finance_hub/invoice_form.html", {"rows": rows, "mode": "select"})


@login_required
def remove_invoice(request):
    _ensure_default_vat_codes(request.user)
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
    _ensure_default_vat_codes(request.user)
    rows = WorkOrder.objects.filter(owner=request.user).select_related("customer", "project", "account", "currency").order_by(
        "-start_date", "-id"
    )[:100]
    return render(request, "finance_hub/work_orders.html", {"rows": rows})


@login_required
def add_work_order(request):
    _ensure_default_vat_codes(request.user)
    if request.method == "POST":
        form = WorkOrderForm(request.POST, owner=request.user)
        if form.is_valid():
            item = form.save(commit=False)
            item.owner = request.user
            item.save()
            _sync_contact_from_customer(request.user, item.customer)
            return redirect("/finance/work-orders/")
    else:
        form = WorkOrderForm(owner=request.user)
    return render(request, "finance_hub/work_order_form.html", {"form": form, "mode": "add"})


@login_required
def update_work_order(request):
    _ensure_default_vat_codes(request.user)
    item_id = request.GET.get("id")
    item = None
    if item_id:
        item = get_object_or_404(WorkOrder, id=item_id, owner=request.user)
        if request.method == "POST":
            form = WorkOrderForm(request.POST, instance=item, owner=request.user)
            if form.is_valid():
                saved_item = form.save()
                _sync_contact_from_customer(request.user, saved_item.customer)
                return redirect("/finance/work-orders/")
        else:
            form = WorkOrderForm(instance=item, owner=request.user)
        return render(request, "finance_hub/work_order_form.html", {"form": form, "mode": "update", "item": item})
    rows = WorkOrder.objects.filter(owner=request.user).order_by("-start_date", "-id")[:20]
    return render(request, "finance_hub/work_order_form.html", {"rows": rows, "mode": "select"})


@login_required
def remove_work_order(request):
    _ensure_default_vat_codes(request.user)
    item_id = request.GET.get("id")
    item = None
    if item_id:
        item = get_object_or_404(WorkOrder, id=item_id, owner=request.user)
        if request.method == "POST":
            item.delete()
            return redirect("/finance/work-orders/")
    rows = WorkOrder.objects.filter(owner=request.user).order_by("-start_date", "-id")[:20]
    return render(request, "finance_hub/work_order_remove.html", {"item": item, "rows": rows})


@login_required
def vat_codes(request):
    _ensure_default_vat_codes(request.user)
    edit_id = request.GET.get("id")
    edit_item = get_object_or_404(VatCode, id=edit_id, owner=request.user) if edit_id else None

    if request.method == "POST":
        action = (request.POST.get("action") or "save").strip().lower()
        if action == "delete":
            item_id = request.POST.get("item_id")
            if item_id:
                item = get_object_or_404(VatCode, id=item_id, owner=request.user)
                item.delete()
            return redirect("/finance/vat-codes/")

        item_id = request.POST.get("item_id")
        instance = get_object_or_404(VatCode, id=item_id, owner=request.user) if item_id else edit_item
        form = VatCodeForm(request.POST, instance=instance)
        form.instance.owner = request.user
        if form.is_valid():
            item = form.save(commit=False)
            item.owner = request.user
            item.save()
            return redirect("/finance/vat-codes/")
    else:
        form = VatCodeForm(instance=edit_item)

    rows = VatCode.objects.filter(owner=request.user).order_by("rate", "code", "id")
    return render(
        request,
        "finance_hub/vat_codes.html",
        {
            "form": form,
            "rows": rows,
            "edit_item": edit_item,
        },
    )
