from datetime import timedelta
from datetime import date as date_lib
from calendar import monthrange
from decimal import Decimal
import json
from urllib.parse import quote as urlquote

from contacts.models import Contact, ContactDeliveryAddress
from contacts.services import ensure_legacy_records_for_contact, upsert_contact
from django.contrib.auth.decorators import login_required
from django.db import transaction
from django.db.models import Max, Sum
from django.http import HttpResponse
from django.shortcuts import get_object_or_404, redirect, render
from django.urls import reverse
from django.utils import timezone
from django.views.decorators.http import require_POST
from projects.models import Customer, Project

from .forms import InvoiceForm, PublicQuoteConfirmationForm, QuoteForm, QuoteLineFormSet, VatCodeForm, WorkOrderForm, SubscriptionForm
from .models import Currency, Tag, Account, Subscription, SubscriptionOccurrence, Invoice, Quote, VatCode, WorkOrder
from .quote_pdf import build_quote_pdf_bytes


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


def _client_ip(request):
    forwarded = (request.META.get("HTTP_X_FORWARDED_FOR") or "").strip()
    if forwarded:
        return forwarded.split(",")[0].strip()
    return (request.META.get("REMOTE_ADDR") or "").strip() or None


def _quote_public_urls(request, token):
    public_url = request.build_absolute_uri(reverse("finance-hub-quotes-public", args=[token]))
    public_pdf_url = request.build_absolute_uri(reverse("finance-hub-quotes-public-pdf", args=[token]))
    return public_url, public_pdf_url


def _public_quote_form_initial(item):
    customer = item.customer
    delivery = item.delivery_address
    return {
        "signer_name": item.customer_signed_name or "",
        "customer_name": customer.name if customer else "",
        "customer_email": customer.email if customer else "",
        "customer_phone": customer.phone if customer else "",
        "customer_notes": customer.notes if customer else "",
        "delivery_label": delivery.label if delivery else "",
        "delivery_recipient_name": delivery.recipient_name if delivery else "",
        "delivery_line1": delivery.line1 if delivery else "",
        "delivery_line2": delivery.line2 if delivery else "",
        "delivery_postal_code": delivery.postal_code if delivery else "",
        "delivery_city": delivery.city if delivery else "",
        "delivery_province": delivery.province if delivery else "",
        "delivery_country": delivery.country if delivery else "Italia",
        "reject_reason": item.customer_decision_note or "",
    }


def _apply_public_quote_customer_updates(item, cleaned_data):
    name = (cleaned_data.get("customer_name") or "").strip()
    email = (cleaned_data.get("customer_email") or "").strip()
    phone = (cleaned_data.get("customer_phone") or "").strip()
    notes = (cleaned_data.get("customer_notes") or "").strip()

    customer = item.customer
    if not name:
        return customer

    existing = (
        Customer.objects.filter(owner=item.owner, name=name)
        .exclude(id=customer.id if customer else None)
        .first()
    )
    if existing:
        customer = existing
    elif customer is None:
        customer = Customer(owner=item.owner, name=name)
    else:
        customer.name = name

    customer.email = email
    customer.phone = phone
    customer.notes = notes
    customer.save()
    _sync_contact_from_customer(item.owner, customer)
    item.customer = customer
    return customer


def _apply_public_quote_delivery_updates(item, cleaned_data, customer):
    if not cleaned_data.get("has_delivery_address"):
        item.delivery_address = None
        return

    label = (cleaned_data.get("delivery_label") or "").strip() or "Destinazione principale"
    recipient_name = (cleaned_data.get("delivery_recipient_name") or "").strip()
    line1 = (cleaned_data.get("delivery_line1") or "").strip()
    line2 = (cleaned_data.get("delivery_line2") or "").strip()
    postal_code = (cleaned_data.get("delivery_postal_code") or "").strip()
    city = (cleaned_data.get("delivery_city") or "").strip()
    province = (cleaned_data.get("delivery_province") or "").strip()
    country = (cleaned_data.get("delivery_country") or "").strip() or "Italia"

    delivery = item.delivery_address
    contact = delivery.contact if delivery and delivery.contact_id else None
    if contact is None:
        contact_name = customer.name if customer else (cleaned_data.get("customer_name") or "").strip()
        contact = upsert_contact(
            item.owner,
            contact_name,
            entity_type=Contact.EntityType.HYBRID,
            email=customer.email if customer else cleaned_data.get("customer_email", ""),
            phone=customer.phone if customer else cleaned_data.get("customer_phone", ""),
            notes=customer.notes if customer else cleaned_data.get("customer_notes", ""),
            roles={"role_customer"},
        )
        ensure_legacy_records_for_contact(contact)

    if contact is None:
        item.delivery_address = None
        return

    if delivery is None:
        max_order = (
            ContactDeliveryAddress.objects.filter(owner=item.owner, contact=contact).aggregate(value=Max("row_order"))[
                "value"
            ]
            or 0
        )
        delivery = ContactDeliveryAddress(
            owner=item.owner,
            contact=contact,
            row_order=max_order + 1,
            is_default=False,
            is_active=True,
        )

    delivery.contact = contact
    delivery.label = label
    delivery.recipient_name = recipient_name
    delivery.line1 = line1
    delivery.line2 = line2
    delivery.postal_code = postal_code
    delivery.city = city
    delivery.province = province
    delivery.country = country
    delivery.is_active = True
    delivery.save()
    item.delivery_address = delivery


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
        .select_related(
            "customer",
            "delivery_address",
            "delivery_address__contact",
            "project",
            "currency",
            "vat_code",
            "payment_method",
            "shipping_method",
        )
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
        quote_public_url = None
        quote_public_pdf_url = None
        if item.has_active_public_access():
            quote_public_url, quote_public_pdf_url = _quote_public_urls(request, item.public_access_token)
        return render(
            request,
            "finance_hub/quote_form.html",
            {
                "form": form,
                "line_formset": line_formset,
                "mode": "update",
                "item": item,
                "vat_rates": _vat_rates_payload(request.user),
                "quote_share_url": f"/finance/quotes/share?id={item.id}",
                "quote_public_url": quote_public_url,
                "quote_public_pdf_url": quote_public_pdf_url,
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
def share_quote(request):
    quote_id = request.GET.get("id")
    item = get_object_or_404(Quote.objects.select_related("customer"), id=quote_id, owner=request.user)
    force_new = request.GET.get("renew") == "1"
    token = item.issue_public_access(force_new=force_new)
    public_url, public_pdf_url = _quote_public_urls(request, token)
    customer_email = item.customer.email if item.customer and item.customer.email else ""
    subject = f"Preventivo {item.code or item.title}"
    body = (
        f"Ciao,\n\n"
        f"ti condivido il preventivo \"{item.title}\".\n"
        f"Puoi visualizzarlo, scaricarlo in PDF e confermarlo da qui:\n{public_url}\n\n"
        f"Grazie."
    )
    mailto_url = ""
    if customer_email:
        mailto_url = f"mailto:{urlquote(customer_email)}?subject={urlquote(subject)}&body={urlquote(body)}"

    return render(
        request,
        "finance_hub/quote_share_link.html",
        {
            "item": item,
            "public_url": public_url,
            "public_pdf_url": public_pdf_url,
            "expires_at": item.public_access_expires_at,
            "mailto_url": mailto_url,
        },
    )


@login_required
def quote_pdf(request):
    quote_id = request.GET.get("id")
    item = get_object_or_404(
        Quote.objects.select_related(
            "customer",
            "delivery_address",
            "delivery_address__contact",
            "project",
            "currency",
            "vat_code",
            "payment_method",
            "shipping_method",
        ).prefetch_related("lines"),
        id=quote_id,
        owner=request.user,
    )
    payload = build_quote_pdf_bytes(item)
    filename = (item.code or f"quote-{item.id}").replace(" ", "_")
    response = HttpResponse(payload, content_type="application/pdf")
    response["Content-Disposition"] = f'attachment; filename="{filename}.pdf"'
    return response


def public_quote_confirm(request, token):
    item = (
        Quote.objects.select_related(
            "customer",
            "delivery_address",
            "delivery_address__contact",
            "project",
            "currency",
            "vat_code",
            "payment_method",
            "shipping_method",
        )
        .prefetch_related("lines")
        .filter(public_access_token=token)
        .first()
    )
    if item is None:
        return render(request, "finance_hub/quote_public_confirm.html", {"invalid_link": True}, status=404)
    if not item.has_active_public_access():
        return render(
            request,
            "finance_hub/quote_public_confirm.html",
            {"invalid_link": True, "item": item},
            status=410,
        )

    decision_locked = bool(item.customer_signed_at or item.status in {Quote.Status.APPROVED, Quote.Status.REJECTED})
    just_confirmed = False
    just_rejected = False
    decision = ""
    public_form = PublicQuoteConfirmationForm(initial=_public_quote_form_initial(item))

    if request.method == "POST" and not decision_locked:
        decision = (request.POST.get("decision") or "").strip().lower()
        public_form = PublicQuoteConfirmationForm(request.POST, decision=decision)
        if public_form.is_valid():
            with transaction.atomic():
                customer = _apply_public_quote_customer_updates(item, public_form.cleaned_data)
                _apply_public_quote_delivery_updates(item, public_form.cleaned_data, customer)

                item.customer_signed_name = (public_form.cleaned_data.get("signer_name") or "").strip()
                item.customer_signed_at = timezone.now()
                item.customer_signed_ip = _client_ip(request)
                item.customer_signed_user_agent = (request.META.get("HTTP_USER_AGENT") or "")[:255]

                if public_form.current_decision == "reject":
                    item.status = Quote.Status.REJECTED
                    item.customer_decision_note = (public_form.cleaned_data.get("reject_reason") or "").strip()
                    just_rejected = True
                else:
                    item.status = Quote.Status.APPROVED
                    item.customer_decision_note = ""
                    just_confirmed = True

                item.save(
                    update_fields=[
                        "customer_id",
                        "delivery_address_id",
                        "customer_signed_name",
                        "customer_signed_at",
                        "customer_signed_ip",
                        "customer_signed_user_agent",
                        "customer_decision_note",
                        "status",
                        "updated_at",
                    ]
                )
            decision_locked = True
            decision = public_form.current_decision

    public_pdf_url = reverse("finance-hub-quotes-public-pdf", args=[token])
    return render(
        request,
        "finance_hub/quote_public_confirm.html",
        {
            "item": item,
            "invalid_link": False,
            "just_confirmed": just_confirmed,
            "just_rejected": just_rejected,
            "decision_locked": decision_locked,
            "decision": decision,
            "public_form": public_form,
            "public_pdf_url": public_pdf_url,
        },
    )


def public_quote_pdf(request, token):
    item = (
        Quote.objects.select_related(
            "customer",
            "delivery_address",
            "delivery_address__contact",
            "project",
            "currency",
            "vat_code",
            "payment_method",
            "shipping_method",
        )
        .prefetch_related("lines")
        .filter(public_access_token=token)
        .first()
    )
    if item is None or not item.has_active_public_access():
        return HttpResponse("Link non valido o scaduto.", status=404)

    payload = build_quote_pdf_bytes(item)
    filename = (item.code or f"quote-{item.id}").replace(" ", "_")
    response = HttpResponse(payload, content_type="application/pdf")
    response["Content-Disposition"] = f'attachment; filename="{filename}.pdf"'
    return response


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


def _safe_next_url(value: str) -> str:
    value = (value or "").strip()
    if value.startswith("/"):
        return value
    return ""


def _add_months(anchor: date_lib, months: int) -> date_lib:
    month_index = anchor.month - 1 + months
    year = anchor.year + month_index // 12
    month = month_index % 12 + 1
    day = min(anchor.day, monthrange(year, month)[1])
    return date_lib(year, month, day)


def _compute_next_due_date(subscription: Subscription, paid_due_date: date_lib) -> date_lib:
    step = max(subscription.interval or 1, 1)
    if subscription.interval_unit == Subscription.IntervalUnit.DAY:
        return paid_due_date + timedelta(days=step)
    if subscription.interval_unit == Subscription.IntervalUnit.WEEK:
        return paid_due_date + timedelta(days=step * 7)
    if subscription.interval_unit == Subscription.IntervalUnit.YEAR:
        return _add_months(paid_due_date, step * 12)
    return _add_months(paid_due_date, step)


def _is_htmx(request) -> bool:
    return request.headers.get("HX-Request") == "true"


def _dashboard_context(user):
    today = timezone.now().date()
    upcoming = list(
        SubscriptionOccurrence.objects.filter(
            owner=user,
            subscription__status=Subscription.Status.ACTIVE,
            state=SubscriptionOccurrence.State.PLANNED,
        )
        .select_related("subscription", "currency")
        .order_by("due_date")[:8]
    )
    using_occurrences = True
    if not upcoming:
        upcoming = list(
            Subscription.objects.filter(owner=user, status=Subscription.Status.ACTIVE)
            .select_related("currency")
            .order_by("next_due_date")[:8]
        )
        using_occurrences = False

    overdue = list(
        SubscriptionOccurrence.objects.filter(
            owner=user,
            due_date__lt=today,
            subscription__status=Subscription.Status.ACTIVE,
            state=SubscriptionOccurrence.State.PLANNED,
        )
        .select_related("subscription", "currency")
        .order_by("due_date")[:8]
    )
    if not overdue:
        overdue = list(
            Subscription.objects.filter(
                owner=user,
                next_due_date__lt=today,
                status=Subscription.Status.ACTIVE,
            )
            .select_related("currency")
            .order_by("next_due_date")[:8]
        )

    total_due = None
    next_due_date = None
    if upcoming:
        if using_occurrences:
            total_due = sum([item.amount for item in upcoming])
            next_due_date = upcoming[0].due_date
        else:
            total_due = sum([item.amount for item in upcoming])
            next_due_date = upcoming[0].next_due_date

    counts = {
        "active": Subscription.objects.filter(owner=user, status=Subscription.Status.ACTIVE).count(),
        "paused": Subscription.objects.filter(owner=user, status=Subscription.Status.PAUSED).count(),
        "canceled": Subscription.objects.filter(owner=user, status=Subscription.Status.CANCELED).count(),
    }
    accounts = Account.objects.filter(owner=user, is_active=True).select_related("currency").order_by("name")
    return {
        "upcoming": upcoming,
        "overdue": overdue,
        "counts": counts,
        "total_due": total_due,
        "next_due_date": next_due_date,
        "accounts": accounts,
    }


@login_required
def subscriptions_dashboard(request):
    return render(request, "subscriptions/dashboard.html", _dashboard_context(request.user))


@login_required
def dashboard_board(request):
    return render(request, "subscriptions/partials/dashboard_board.html", _dashboard_context(request.user))


@login_required
def add_sub(request):
    from projects.models import Project
    next_url = _safe_next_url(request.GET.get("next") or request.POST.get("next"))
    if request.method == "POST":
        form = SubscriptionForm(request.POST, owner=request.user)
        if form.is_valid():
            sub = form.save(commit=False)
            sub.owner = request.user
            if not sub.currency_id:
                sub.currency, _ = Currency.objects.get_or_create(code="EUR", defaults={"name": "Euro"})
            sub.save()
            form.save_m2m()
            return redirect(next_url or "/subs/")
    else:
        initial = {}
        project_id = (request.GET.get("project") or "").strip()
        if project_id:
            project = Project.objects.filter(id=project_id, owner=request.user).first()
            if project:
                initial["project"] = project
        form = SubscriptionForm(owner=request.user, initial=initial)
    return render(request, "subscriptions/add_sub.html", {"form": form, "next": next_url})


@login_required
def remove_sub(request):
    sub_id = request.GET.get("id")
    sub = None
    if sub_id:
        sub = get_object_or_404(Subscription, id=sub_id, owner=request.user)
        if request.method == "POST":
            sub.delete()
            return redirect("/subs/")
    subs = Subscription.objects.filter(owner=request.user).order_by("name")[:20]
    return render(request, "subscriptions/remove_sub.html", {"sub": sub, "subs": subs})


@login_required
def update_sub(request):
    sub_id = request.GET.get("id")
    sub = None
    if sub_id:
        sub = get_object_or_404(Subscription, id=sub_id, owner=request.user)
        if request.method == "POST":
            if request.POST.get("action") == "cancel":
                sub.status = Subscription.Status.CANCELED
                sub.save(update_fields=["status"])
                return redirect("/subs/")
            form = SubscriptionForm(request.POST, instance=sub, owner=request.user)
            if form.is_valid():
                sub = form.save(commit=False)
                if not sub.currency_id:
                    sub.currency, _ = Currency.objects.get_or_create(code="EUR", defaults={"name": "Euro"})
                sub.save()
                form.save_m2m()
                return redirect("/subs/")
        else:
            form = SubscriptionForm(instance=sub, owner=request.user)
        return render(request, "subscriptions/update_sub.html", {"form": form, "sub": sub})
    subs = Subscription.objects.filter(owner=request.user).order_by("name")[:20]
    return render(request, "subscriptions/update_sub.html", {"subs": subs})


@login_required
@require_POST
def pay_subscription(request):
    from transactions.models import Transaction
    user = request.user
    account_id = request.POST.get("account_id")
    occurrence_id = request.POST.get("occurrence_id")
    subscription_id = request.POST.get("subscription_id")
    due_date_raw = (request.POST.get("due_date") or "").strip()

    if not account_id:
        return redirect("/subs/")

    account = get_object_or_404(Account, id=account_id, owner=user, is_active=True)

    occurrence = None
    if occurrence_id:
        occurrence = get_object_or_404(
            SubscriptionOccurrence.objects.select_related("subscription"),
            id=occurrence_id,
            owner=user,
        )
    elif subscription_id:
        subscription = get_object_or_404(
            Subscription.objects.select_related("currency", "project", "category", "payee"),
            id=subscription_id,
            owner=user,
        )
        try:
            due_date = date_lib.fromisoformat(due_date_raw) if due_date_raw else subscription.next_due_date
        except ValueError:
            due_date = subscription.next_due_date
        occurrence, _ = SubscriptionOccurrence.objects.get_or_create(
            owner=user,
            subscription=subscription,
            due_date=due_date,
            defaults={
                "amount": subscription.amount,
                "currency": subscription.currency,
            },
        )
    else:
        return redirect("/subs/")

    if occurrence.transaction_id:
        if occurrence.state != SubscriptionOccurrence.State.PAID:
            occurrence.state = SubscriptionOccurrence.State.PAID
            occurrence.save(update_fields=["state"])
        if _is_htmx(request):
            response = render(request, "subscriptions/partials/dashboard_board.html", _dashboard_context(user))
            response["HX-Trigger"] = json.dumps({"subs:paid": {"message": "Pagamento gia registrato."}})
            return response
        return redirect("/subs/")

    subscription = occurrence.subscription
    payment_date = timezone.now().date()
    payment_note = f"Pagamento abbonamento {subscription.name} - scadenza {occurrence.due_date.isoformat()}"

    with transaction.atomic():
        tx = Transaction.objects.create(
            owner=user,
            tx_type=Transaction.Type.EXPENSE,
            date=payment_date,
            amount=occurrence.amount,
            currency=occurrence.currency,
            account=account,
            project=subscription.project,
            category=subscription.category,
            payee=subscription.payee,
            note=payment_note,
            source_subscription=subscription,
        )
        occurrence.transaction = tx
        occurrence.state = SubscriptionOccurrence.State.PAID
        occurrence.save(update_fields=["transaction", "state"])

        if subscription.next_due_date <= occurrence.due_date:
            subscription.next_due_date = _compute_next_due_date(subscription, occurrence.due_date)
            subscription.save(update_fields=["next_due_date"])

    if _is_htmx(request):
        response = render(request, "subscriptions/partials/dashboard_board.html", _dashboard_context(user))
        response["HX-Trigger"] = json.dumps({"subs:paid": {"message": "Pagamento registrato."}})
        return response
    return redirect("/subs/")
