---
title: Quote
tags: [db, model, finance, finance_hub]
---

# Quote
**App:** `finance_hub` · **Tabella:** `finance_hub_quote`
**Base:** `OwnedModel`, `TimeStampedModel`

Preventivo emesso verso un cliente. Può avere accesso pubblico temporaneo per firma digitale.

## Campi principali
| Campo | Tipo | Note |
|---|---|---|
| code | CharField(40) | unique non-vuoto per owner |
| title | CharField(180) | |
| status | CharField | DRAFT / SENT / APPROVED / REJECTED / EXPIRED |
| issue_date | DateField | |
| valid_until | DateField | opzionale |
| amount_net | DecimalField(12,2) | calcolato da righe |
| tax_amount | DecimalField(12,2) | calcolato |
| total_amount | DecimalField(12,2) | calcolato |
| public_access_token | CharField(96) | per link firma pubblica |
| customer_signed_at | DateTimeField | opzionale |

## Relazioni FK
| Campo | → Modello | on_delete |
|---|---|---|
| customer | [[Customer]] | SET_NULL |
| project | [[Project]] | SET_NULL |
| delivery_address | [[ContactDeliveryAddress]] | SET_NULL |
| currency | [[Currency]] | PROTECT |
| vat_code | [[VatCode]] | SET_NULL |
| payment_method | [[PaymentMethod]] | SET_NULL |
| shipping_method | [[ShippingMethod]] | SET_NULL |

## Relazioni inverse
- `lines` ← [[QuoteLine]]
- `invoices` ← [[Invoice]]
