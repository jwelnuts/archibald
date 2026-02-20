from __future__ import annotations

from typing import Iterable

from .models import Contact


def _strip_or_empty(value):
    return (value or "").strip()


def upsert_contact(
    owner,
    display_name: str,
    *,
    entity_type: str | None = None,
    person_name: str = "",
    business_name: str = "",
    email: str = "",
    phone: str = "",
    website: str = "",
    city: str = "",
    notes: str = "",
    roles: Iterable[str] | None = None,
):
    label = _strip_or_empty(display_name)
    if owner is None or not label:
        return None

    defaults = {
        "entity_type": entity_type or Contact.EntityType.PERSON,
        "person_name": _strip_or_empty(person_name),
        "business_name": _strip_or_empty(business_name),
        "email": _strip_or_empty(email),
        "phone": _strip_or_empty(phone),
        "website": _strip_or_empty(website),
        "city": _strip_or_empty(city),
        "notes": _strip_or_empty(notes),
        "is_active": True,
    }
    contact, _ = Contact.objects.get_or_create(owner=owner, display_name=label, defaults=defaults)

    update_fields = []
    if entity_type and contact.entity_type != entity_type:
        contact.entity_type = entity_type
        update_fields.append("entity_type")
    for field_name, value in (
        ("person_name", person_name),
        ("business_name", business_name),
        ("email", email),
        ("phone", phone),
        ("website", website),
        ("city", city),
        ("notes", notes),
    ):
        raw = _strip_or_empty(value)
        if raw and not getattr(contact, field_name):
            setattr(contact, field_name, raw)
            update_fields.append(field_name)

    for role_name in roles or ():
        if hasattr(contact, role_name) and not getattr(contact, role_name):
            setattr(contact, role_name, True)
            update_fields.append(role_name)

    if not contact.is_active:
        contact.is_active = True
        update_fields.append("is_active")

    if update_fields:
        unique_fields = sorted(set(update_fields + ["updated_at"]))
        contact.save(update_fields=unique_fields)
    return contact


def ensure_legacy_records_for_contact(contact: Contact):
    if not contact:
        return

    from core.models import Payee
    from income.models import IncomeSource
    from projects.models import Customer

    if contact.role_customer:
        customer, created = Customer.objects.get_or_create(
            owner=contact.owner,
            name=contact.display_name,
            defaults={
                "email": contact.email,
                "phone": contact.phone,
                "notes": contact.notes,
            },
        )
        if not created:
            changed = []
            if contact.email and not customer.email:
                customer.email = contact.email
                changed.append("email")
            if contact.phone and not customer.phone:
                customer.phone = contact.phone
                changed.append("phone")
            if contact.notes and not customer.notes:
                customer.notes = contact.notes
                changed.append("notes")
            if changed:
                customer.save(update_fields=changed)

    if contact.role_payee or contact.role_supplier:
        payee, created = Payee.objects.get_or_create(
            owner=contact.owner,
            name=contact.display_name,
            defaults={"website": contact.website},
        )
        if not created and contact.website and not payee.website:
            payee.website = contact.website
            payee.save(update_fields=["website"])

    if contact.role_income_source:
        source, created = IncomeSource.objects.get_or_create(
            owner=contact.owner,
            name=contact.display_name,
            defaults={"website": contact.website},
        )
        if not created and contact.website and not source.website:
            source.website = contact.website
            source.save(update_fields=["website"])


def sync_contacts_from_legacy(owner):
    if owner is None:
        return

    from core.models import Payee
    from income.models import IncomeSource
    from projects.models import Customer

    customers = Customer.objects.filter(owner=owner).values("name", "email", "phone", "notes")
    for row in customers:
        upsert_contact(
            owner,
            row["name"],
            entity_type=Contact.EntityType.HYBRID,
            email=row.get("email") or "",
            phone=row.get("phone") or "",
            notes=row.get("notes") or "",
            roles={"role_customer"},
        )

    payees = Payee.objects.filter(owner=owner).values("name", "website")
    for row in payees:
        upsert_contact(
            owner,
            row["name"],
            entity_type=Contact.EntityType.HYBRID,
            website=row.get("website") or "",
            roles={"role_payee", "role_supplier"},
        )

    income_sources = IncomeSource.objects.filter(owner=owner).values("name", "website")
    for row in income_sources:
        upsert_contact(
            owner,
            row["name"],
            entity_type=Contact.EntityType.HYBRID,
            website=row.get("website") or "",
            roles={"role_income_source", "role_customer"},
        )
