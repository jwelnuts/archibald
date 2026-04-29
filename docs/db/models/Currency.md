---
title: Currency
tags: [db, model, finance, finance_hub]
---

# Currency
**App:** `finance_hub` · **Tabella:** `common_currency`
**Base:** `models.Model` (no owner, no timestamp)

Valuta globale condivisa (non per-utente).

## Campi principali
| Campo | Tipo | Note |
|---|---|---|
| code | CharField(3) | unique, es. EUR |
| name | CharField(64) | |
| symbol | CharField(8) | |

## Relazioni inverse
- `account_set` ← [[Account]]
- `transaction_set` ← [[Transaction]]
- `subscription_set` ← [[Subscription]]
- `subscriptionoccurrence_set` ← [[SubscriptionOccurrence]]
- `quote_set` ← [[Quote]]
- `invoice_set` ← [[Invoice]]
- `workorder_set` ← [[WorkOrder]]
