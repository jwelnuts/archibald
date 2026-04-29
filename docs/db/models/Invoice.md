---
title: Invoice
tags: [db, model, finance, finance_hub]
---

# Invoice
**App:** `finance_hub` · **Tabella:** `finance_hub_invoice`
**Base:** `OwnedModel`, `TimeStampedModel`

Fattura emessa, opzionalmente collegata a un [[Quote]].

## Campi principali
| Campo | Tipo | Note |
|---|---|---|
| code | CharField(40) | unique non-vuoto per owner |
| title | CharField(180) | |
| status | CharField | DRAFT / ISSUED / PAID / OVERDUE / CANCELED |
| issue_date | DateField | |
| due_date | DateField | opzionale |
| paid_date | DateField | opzionale |
| amount_net | DecimalField(12,2) | |
| tax_amount | DecimalField(12,2) | |
| total_amount | DecimalField(12,2) | calcolato |

## Relazioni FK
| Campo | → Modello | on_delete |
|---|---|---|
| quote | [[Quote]] | SET_NULL |
| customer | [[Customer]] | SET_NULL |
| project | [[Project]] | SET_NULL |
| account | [[Account]] | SET_NULL |
| currency | [[Currency]] | PROTECT |
