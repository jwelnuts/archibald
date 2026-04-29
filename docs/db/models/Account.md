---
title: Account
tags: [db, model, finance, finance_hub]
---

# Account
**App:** `finance_hub` · **Tabella:** `core_accounts`
**Base:** `OwnedModel`, `TimeStampedModel`

Conto bancario, carta, contanti o investimento dell'utente.

## Campi principali
| Campo | Tipo | Note |
|---|---|---|
| name | CharField(120) | unique per owner |
| kind | CharField | BANK / CARD / CASH / INVEST / OTHER |
| opening_balance | DecimalField(12,2) | |
| is_active | BooleanField | |

## Relazioni FK
| Campo | → Modello | on_delete |
|---|---|---|
| currency | [[Currency]] | PROTECT |

## Relazioni inverse
- `transactions` ← [[Transaction]]
- `subscriptions` ← [[Subscription]]
- `finance_invoices` ← [[Invoice]]
- `finance_work_orders` ← [[WorkOrder]]
