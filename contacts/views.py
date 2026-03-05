from urllib.parse import quote_plus

from django.contrib.auth.decorators import login_required
from django.db import transaction
from django.db.models import Q
from django.shortcuts import get_object_or_404, redirect, render
from django.utils.http import url_has_allowed_host_and_scheme

from .forms import ContactForm, ContactPriceListForm, ContactPriceListItemFormSet, ContactToolboxForm
from .models import Contact, ContactPriceList, ContactToolbox
from .services import ensure_legacy_records_for_contact, sync_contacts_from_legacy


def _ensure_toolbox(contact):
    toolbox, _ = ContactToolbox.objects.get_or_create(owner=contact.owner, contact=contact)
    return toolbox


def _safe_next_url(request):
    next_url = (request.POST.get("next") or request.GET.get("next") or "").strip()
    if not next_url:
        return ""
    if url_has_allowed_host_and_scheme(
        url=next_url,
        allowed_hosts={request.get_host()},
        require_https=request.is_secure(),
    ):
        return next_url
    return ""


@login_required
def dashboard(request):
    user = request.user
    sync_contacts_from_legacy(user)

    qs = Contact.objects.filter(owner=user).order_by("display_name")
    role = (request.GET.get("role") or "").strip().lower()
    if role == "customer":
        qs = qs.filter(role_customer=True)
    elif role == "supplier":
        qs = qs.filter(role_supplier=True)
    elif role == "payee":
        qs = qs.filter(role_payee=True)
    elif role == "income":
        qs = qs.filter(role_income_source=True)
    elif role == "active":
        qs = qs.filter(is_active=True)

    q = (request.GET.get("q") or "").strip()
    if q:
        qs = qs.filter(
            Q(display_name__icontains=q)
            | Q(person_name__icontains=q)
            | Q(business_name__icontains=q)
            | Q(email__icontains=q)
            | Q(phone__icontains=q)
        )

    rows = list(qs[:200])
    grid_rows = []
    for item in rows:
        role_labels = []
        if item.role_customer:
            role_labels.append("Cliente")
        if item.role_supplier:
            role_labels.append("Fornitore")
        if item.role_payee:
            role_labels.append("Beneficiario")
        if item.role_income_source:
            role_labels.append("Fonte entrata")

        grid_rows.append(
            {
                "id": item.id,
                "display_name": item.display_name,
                "entity_type": item.get_entity_type_display(),
                "entity_code": item.entity_type,
                "person_name": item.person_name or "",
                "business_name": item.business_name or "",
                "email": item.email or "",
                "phone": item.phone or "",
                "city": item.city or "",
                "roles_text": ", ".join(role_labels) if role_labels else "Nessun ruolo",
                "role_customer": item.role_customer,
                "role_supplier": item.role_supplier,
                "role_payee": item.role_payee,
                "role_income_source": item.role_income_source,
                "is_active": item.is_active,
                "update_url": f"/contacts/update?id={item.id}",
                "remove_url": f"/contacts/remove?id={item.id}",
                "search_url": f"/contacts/?q={quote_plus(item.display_name)}",
                "toolbox_url": f"/contacts/toolbox?id={item.id}",
            }
        )

    counts = {
        "total": Contact.objects.filter(owner=user).count(),
        "active": Contact.objects.filter(owner=user, is_active=True).count(),
        "customers": Contact.objects.filter(owner=user, role_customer=True).count(),
        "suppliers": Contact.objects.filter(owner=user, role_supplier=True).count(),
        "payees": Contact.objects.filter(owner=user, role_payee=True).count(),
        "income_sources": Contact.objects.filter(owner=user, role_income_source=True).count(),
    }

    return render(
        request,
        "contacts/dashboard.html",
        {
            "rows": rows,
            "grid_rows": grid_rows,
            "counts": counts,
            "filters": {"role": role, "q": q},
        },
    )


@login_required
def add_contact(request):
    sync_contacts_from_legacy(request.user)
    next_url = _safe_next_url(request)
    if request.method == "POST":
        form = ContactForm(request.POST)
        if form.is_valid():
            item = form.save(commit=False)
            item.owner = request.user
            item.save()
            _ensure_toolbox(item)
            ensure_legacy_records_for_contact(item)
            return redirect(next_url or "/contacts/")
    else:
        form = ContactForm()
    return render(request, "contacts/add_contact.html", {"form": form, "next_url": next_url})


@login_required
def update_contact(request):
    sync_contacts_from_legacy(request.user)
    item_id = request.GET.get("id")
    item = None
    if item_id:
        item = get_object_or_404(Contact, id=item_id, owner=request.user)
        if request.method == "POST":
            form = ContactForm(request.POST, instance=item)
            if form.is_valid():
                saved = form.save()
                _ensure_toolbox(saved)
                ensure_legacy_records_for_contact(saved)
                return redirect("/contacts/")
        else:
            form = ContactForm(instance=item)
        return render(request, "contacts/update_contact.html", {"form": form, "item": item})
    rows = Contact.objects.filter(owner=request.user).order_by("display_name")[:30]
    return render(request, "contacts/update_contact.html", {"rows": rows})


@login_required
def remove_contact(request):
    sync_contacts_from_legacy(request.user)
    item_id = request.GET.get("id")
    item = None
    if item_id:
        item = get_object_or_404(Contact, id=item_id, owner=request.user)
        if request.method == "POST":
            item.delete()
            return redirect("/contacts/")
    rows = Contact.objects.filter(owner=request.user).order_by("display_name")[:30]
    return render(request, "contacts/remove_contact.html", {"item": item, "rows": rows})


@login_required
def toolbox(request):
    sync_contacts_from_legacy(request.user)
    contact_id = request.GET.get("id")
    if contact_id:
        contact = get_object_or_404(Contact, id=contact_id, owner=request.user)
        toolbox_item = _ensure_toolbox(contact)

        if request.method == "POST":
            form = ContactToolboxForm(request.POST, instance=toolbox_item)
            if form.is_valid():
                saved = form.save(commit=False)
                saved.owner = request.user
                saved.contact = contact
                saved.save()
                return redirect(f"/contacts/toolbox?id={contact.id}")
        else:
            form = ContactToolboxForm(instance=toolbox_item)

        price_lists = (
            ContactPriceList.objects.filter(owner=request.user, toolbox=toolbox_item)
            .prefetch_related("items")
            .order_by("-updated_at", "-id")
        )
        return render(
            request,
            "contacts/toolbox.html",
            {
                "contact": contact,
                "toolbox": toolbox_item,
                "form": form,
                "price_lists": price_lists,
            },
        )

    rows = Contact.objects.filter(owner=request.user).order_by("display_name")[:50]
    return render(request, "contacts/toolbox.html", {"rows": rows})


@login_required
def add_price_list(request):
    sync_contacts_from_legacy(request.user)
    contact_id = request.GET.get("contact_id")
    contact = get_object_or_404(Contact, id=contact_id, owner=request.user)
    toolbox_item = _ensure_toolbox(contact)

    if request.method == "POST":
        form = ContactPriceListForm(request.POST)
        temp_item = ContactPriceList(owner=request.user, toolbox=toolbox_item)
        item_formset = ContactPriceListItemFormSet(request.POST, instance=temp_item, prefix="items")
        if form.is_valid() and item_formset.is_valid():
            with transaction.atomic():
                price_list = form.save(commit=False)
                price_list.owner = request.user
                price_list.toolbox = toolbox_item
                price_list.save()

                item_formset.instance = price_list
                line_items = item_formset.save(commit=False)
                for deleted in item_formset.deleted_objects:
                    deleted.delete()
                for idx, line in enumerate(line_items, start=1):
                    line.owner = request.user
                    line.price_list = price_list
                    if not line.row_order:
                        line.row_order = idx
                    line.save()
            return redirect(f"/contacts/toolbox?id={contact.id}")
    else:
        form = ContactPriceListForm()
        item_formset = ContactPriceListItemFormSet(
            instance=ContactPriceList(owner=request.user, toolbox=toolbox_item),
            prefix="items",
        )

    return render(
        request,
        "contacts/price_list_form.html",
        {
            "mode": "add",
            "contact": contact,
            "toolbox": toolbox_item,
            "form": form,
            "item_formset": item_formset,
        },
    )


@login_required
def update_price_list(request):
    sync_contacts_from_legacy(request.user)
    item_id = request.GET.get("id")
    if item_id:
        price_list = get_object_or_404(
            ContactPriceList.objects.select_related("toolbox", "toolbox__contact"),
            id=item_id,
            owner=request.user,
        )
        contact = price_list.contact
        if request.method == "POST":
            form = ContactPriceListForm(request.POST, instance=price_list)
            item_formset = ContactPriceListItemFormSet(request.POST, instance=price_list, prefix="items")
            if form.is_valid() and item_formset.is_valid():
                with transaction.atomic():
                    saved_price_list = form.save(commit=False)
                    saved_price_list.owner = request.user
                    saved_price_list.toolbox = price_list.toolbox
                    saved_price_list.save()

                    line_items = item_formset.save(commit=False)
                    for deleted in item_formset.deleted_objects:
                        deleted.delete()
                    for idx, line in enumerate(line_items, start=1):
                        line.owner = request.user
                        line.price_list = saved_price_list
                        if not line.row_order:
                            line.row_order = idx
                        line.save()
                return redirect(f"/contacts/toolbox?id={contact.id}")
        else:
            form = ContactPriceListForm(instance=price_list)
            item_formset = ContactPriceListItemFormSet(instance=price_list, prefix="items")
        return render(
            request,
            "contacts/price_list_form.html",
            {
                "mode": "update",
                "contact": contact,
                "toolbox": price_list.toolbox,
                "item": price_list,
                "form": form,
                "item_formset": item_formset,
            },
        )

    rows = ContactPriceList.objects.filter(owner=request.user).select_related("toolbox__contact").order_by("-updated_at", "-id")[
        :40
    ]
    return render(request, "contacts/price_list_form.html", {"mode": "select", "rows": rows})


@login_required
def remove_price_list(request):
    sync_contacts_from_legacy(request.user)
    item_id = request.GET.get("id")
    if item_id:
        price_list = get_object_or_404(
            ContactPriceList.objects.select_related("toolbox", "toolbox__contact"),
            id=item_id,
            owner=request.user,
        )
        if request.method == "POST":
            contact_id = price_list.contact.id
            price_list.delete()
            return redirect(f"/contacts/toolbox?id={contact_id}")
        return render(request, "contacts/price_list_remove.html", {"item": price_list, "contact": price_list.contact})

    rows = ContactPriceList.objects.filter(owner=request.user).select_related("toolbox__contact").order_by("-updated_at", "-id")[
        :40
    ]
    return render(request, "contacts/price_list_remove.html", {"rows": rows})
