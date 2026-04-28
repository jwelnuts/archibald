---
title: contacts
tags: [app, contacts]
aliases: [crm, address book, people]
---

# Contacts App

Comprehensive contact management with entity types, delivery addresses, and pricing.

## Models

| Model | Description | Key Fields |
|-------|-------------|------------|
| `Contact` | Contact records | display_name, entity_type, person_name, business_name, email, phone, website, roles, notes |
| `ContactDeliveryAddress` | Delivery addresses | contact, label, recipient_name, line1, line2, postal_code, city, province, country, is_default |
| `ContactToolbox` | Internal notes/data | contact, internal_notes, extra_data |
| `ContactPriceList` | Price lists | toolbox, title, currency_code, pricing_notes, note |
| `ContactPriceListItem` | Price list items | price_list, code, title, min_quantity, max_quantity, unit_price |

### Contact Entity Types

- `PERSON` - Persona
- `HYBRID` - Persona + Attivita
- `ENTITY` - Ente
- `COMPANY` - Azienda

### Contact Roles

- role_customer
- role_supplier
- role_payee
- role_income_source

## URLs

| Route | Name | Description |
|-------|------|-------------|
| `/` | contacts-dashboard | Contacts dashboard |
| `/add` | contacts-add | Add contact |
| `/update` | contacts-update | Update contact |
| `/remove` | contacts-remove | Remove contact |
| `/toolbox` | contacts-toolbox | Contact toolbox |
| `/price-lists/add` | contacts-price-list-add | Add price list |
| `/price-lists/update` | contacts-price-list-update | Update price list |
| `/price-lists/remove` | contacts-price-list-remove | Remove price list |
| `/api/payees/search` | contacts-api-payee-search | Search payees |
| `/api/payees/quick-create` | contacts-api-payee-quick-create | Quick create payee |

## Related Apps

- [[finance_hub]] - Customer for Quote, Invoice
- [[core]] - Payee linking
- [[projects]] - Customer model