from urllib.parse import quote_plus

from django.contrib.auth.decorators import login_required
from django.db.models import Q
from django.shortcuts import get_object_or_404, redirect, render

from .forms import ContactForm
from .models import Contact
from .services import ensure_legacy_records_for_contact, sync_contacts_from_legacy


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
    if request.method == "POST":
        form = ContactForm(request.POST)
        if form.is_valid():
            item = form.save(commit=False)
            item.owner = request.user
            item.save()
            ensure_legacy_records_for_contact(item)
            return redirect("/contacts/")
    else:
        form = ContactForm()
    return render(request, "contacts/add_contact.html", {"form": form})


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
