from urllib.parse import urlencode

from django.contrib.auth.decorators import login_required
from django.db.models import Count, Q, Sum
from django.http import HttpResponse
from django.shortcuts import get_object_or_404, redirect, render
from django.urls import reverse

from projects.models import Project

from .forms import TransactionEntryForm, TransactionFilterForm
from .models import Transaction


def _is_htmx(request):
    return request.headers.get("HX-Request") == "true"


def _normalized_filter_data(request):
    data = request.GET.copy()
    if not data.get("tx_type") and data.get("type"):
        data["tx_type"] = data.get("type")
    return data


def _resolve_filters(request):
    bound_data = _normalized_filter_data(request)
    filter_form = TransactionFilterForm(bound_data or None)
    allowed_types = {choice[0] for choice in Transaction.Type.choices}

    if filter_form.is_valid():
        cleaned = filter_form.cleaned_data
        return filter_form, {
            "tx_type": cleaned.get("tx_type") or "",
            "date_from": cleaned.get("date_from"),
            "date_to": cleaned.get("date_to"),
            "query": (cleaned.get("query") or "").strip(),
        }

    tx_type = (bound_data.get("tx_type") or "").strip()
    if tx_type not in allowed_types:
        tx_type = ""

    return filter_form, {
        "tx_type": tx_type,
        "date_from": None,
        "date_to": None,
        "query": (bound_data.get("query") or "").strip(),
    }


def _base_queryset(user):
    return Transaction.objects.filter(owner=user).select_related(
        "payee",
        "income_source",
        "currency",
        "account",
        "project",
        "category",
    )


def _apply_filters(queryset, filters):
    tx_type = filters.get("tx_type") or ""
    if tx_type:
        queryset = queryset.filter(tx_type=tx_type)

    date_from = filters.get("date_from")
    if date_from:
        queryset = queryset.filter(date__gte=date_from)

    date_to = filters.get("date_to")
    if date_to:
        queryset = queryset.filter(date__lte=date_to)

    query = (filters.get("query") or "").strip()
    if query:
        queryset = queryset.filter(
            Q(note__icontains=query)
            | Q(account__name__icontains=query)
            | Q(project__name__icontains=query)
            | Q(category__name__icontains=query)
            | Q(payee__name__icontains=query)
            | Q(income_source__name__icontains=query)
        )

    return queryset


def _counterparty(tx):
    if tx.tx_type == Transaction.Type.INCOME:
        if tx.income_source:
            return tx.income_source.name
        if tx.payee:
            return tx.payee.name
        return "Entrata"

    if tx.tx_type == Transaction.Type.EXPENSE:
        if tx.payee:
            return tx.payee.name
        return "Uscita"

    return "Trasferimento"


def _filters_to_querystring(filters):
    params = {}

    if filters.get("tx_type"):
        params["tx_type"] = filters["tx_type"]
    if filters.get("date_from"):
        params["date_from"] = filters["date_from"].isoformat()
    if filters.get("date_to"):
        params["date_to"] = filters["date_to"].isoformat()
    if filters.get("query"):
        params["query"] = filters["query"]

    return urlencode(params)


def _board_context(user, filters):
    all_queryset = _base_queryset(user)
    filtered_queryset = _apply_filters(all_queryset, filters)

    rows = filtered_queryset.order_by("-date", "-created_at")[:120]
    transactions = []
    for tx in rows:
        transactions.append(
            {
                "object": tx,
                "counterparty": _counterparty(tx),
            }
        )

    total_rows = (
        filtered_queryset.values("tx_type")
        .annotate(total=Sum("amount"))
    )
    totals = {row["tx_type"]: row["total"] for row in total_rows}

    count_rows = (
        filtered_queryset.values("tx_type")
        .annotate(total=Count("id"))
    )
    filtered_counts = {row["tx_type"]: row["total"] for row in count_rows}

    all_counts = (
        all_queryset.values("tx_type")
        .annotate(total=Count("id"))
    )
    global_counts = {row["tx_type"]: row["total"] for row in all_counts}

    income_total = totals.get(Transaction.Type.INCOME) or 0
    expense_total = totals.get(Transaction.Type.EXPENSE) or 0
    transfer_total = totals.get(Transaction.Type.TRANSFER) or 0

    return {
        "transactions": transactions,
        "summary": {
            "income_total": income_total,
            "expense_total": expense_total,
            "transfer_total": transfer_total,
            "net_total": income_total - expense_total,
            "filtered_total": filtered_queryset.count(),
            "global_total": all_queryset.count(),
        },
        "filtered_counts": {
            "income": filtered_counts.get(Transaction.Type.INCOME, 0),
            "expense": filtered_counts.get(Transaction.Type.EXPENSE, 0),
            "transfer": filtered_counts.get(Transaction.Type.TRANSFER, 0),
        },
        "global_counts": {
            "income": global_counts.get(Transaction.Type.INCOME, 0),
            "expense": global_counts.get(Transaction.Type.EXPENSE, 0),
            "transfer": global_counts.get(Transaction.Type.TRANSFER, 0),
        },
        "filters_querystring": _filters_to_querystring(filters),
    }


def _modal_open_url(request):
    open_mode = (request.GET.get("open") or "").strip().lower()
    tx_id = (request.GET.get("id") or "").strip()
    tx_type = (request.GET.get("tx_type") or request.GET.get("type") or "").strip()
    project = (request.GET.get("project") or "").strip()

    if open_mode == "new":
        params = {}
        if tx_type in {choice[0] for choice in Transaction.Type.choices}:
            params["tx_type"] = tx_type
        if project:
            params["project"] = project
        url = reverse("transactions-form")
        return f"{url}?{urlencode(params)}" if params else url

    if open_mode == "edit" and tx_id:
        return f"{reverse('transactions-form')}?{urlencode({'id': tx_id})}"

    if open_mode == "delete" and tx_id:
        return f"{reverse('transactions-delete')}?{urlencode({'id': tx_id})}"

    return ""


def _transaction_from_request(request):
    tx_id = (request.GET.get("id") or request.POST.get("id") or "").strip()
    if not tx_id:
        return None
    try:
        tx_id = int(tx_id)
    except (TypeError, ValueError):
        return None
    return get_object_or_404(Transaction, id=tx_id, owner=request.user)


def _dashboard_redirect_url(tx_type=""):
    base_url = reverse("transactions-dashboard")
    if tx_type in {choice[0] for choice in Transaction.Type.choices}:
        return f"{base_url}?{urlencode({'tx_type': tx_type})}"
    return base_url


@login_required
def dashboard(request):
    filter_form, filters = _resolve_filters(request)
    context = {
        "filter_form": filter_form,
        "modal_open_url": _modal_open_url(request),
    }
    context.update(_board_context(request.user, filters))
    return render(request, "transactions/dashboard.html", context)


@login_required
def board_partial(request):
    _filter_form, filters = _resolve_filters(request)
    context = _board_context(request.user, filters)
    return render(request, "transactions/partials/board.html", context)


@login_required
def form_partial(request):
    tx = _transaction_from_request(request)

    requested_type = (
        request.GET.get("tx_type")
        or request.POST.get("tx_type")
        or (tx.tx_type if tx else "")
        or Transaction.Type.EXPENSE
    )

    if requested_type not in {choice[0] for choice in Transaction.Type.choices}:
        requested_type = Transaction.Type.EXPENSE

    initial = {}
    project_id = (request.GET.get("project") or request.POST.get("project") or "").strip()
    if project_id and tx is None:
        project = Project.objects.filter(id=project_id, owner=request.user).first()
        if project:
            initial["project"] = project

    if request.method == "POST":
        form = TransactionEntryForm(
            request.POST,
            request.FILES,
            owner=request.user,
            tx_type=requested_type,
            instance=tx,
        )
        if form.is_valid():
            saved = form.save()

            if _is_htmx(request):
                response = HttpResponse(status=204)
                response["HX-Trigger"] = "transactions:refresh"
                return response

            return redirect(_dashboard_redirect_url(saved.tx_type))

        status_code = 422 if _is_htmx(request) else 200
    else:
        form = TransactionEntryForm(
            owner=request.user,
            tx_type=requested_type,
            instance=tx,
            initial=initial,
        )
        status_code = 200

    post_url = reverse("transactions-form")
    if tx is not None:
        post_url = f"{post_url}?{urlencode({'id': tx.id})}"

    return render(
        request,
        "transactions/partials/form.html",
        {
            "form": form,
            "tx": tx,
            "post_url": post_url,
        },
        status=status_code,
    )


@login_required
def delete_partial(request):
    tx = _transaction_from_request(request)
    if tx is None:
        return redirect(reverse("transactions-dashboard"))

    if request.method == "POST":
        tx_type = tx.tx_type
        tx.delete()

        if _is_htmx(request):
            response = HttpResponse(status=204)
            response["HX-Trigger"] = "transactions:refresh"
            return response

        return redirect(_dashboard_redirect_url(tx_type))

    post_url = f"{reverse('transactions-delete')}?{urlencode({'id': tx.id})}"
    return render(
        request,
        "transactions/partials/delete.html",
        {
            "tx": tx,
            "post_url": post_url,
        },
    )
