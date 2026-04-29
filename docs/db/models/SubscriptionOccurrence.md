---
title: SubscriptionOccurrence
tags: [db, model, finance, finance_hub]
---

# SubscriptionOccurrence
**App:** `finance_hub` · **Tabella:** `finance_hub_subscriptionoccurrence`
**Base:** `OwnedModel`, `TimeStampedModel`

Singola scadenza pianificata di un [[Subscription]]. Quando pagata, viene collegata a una [[Transaction]].

## Campi principali
| Campo | Tipo | Note |
|---|---|---|
| due_date | DateField | unique con subscription |
| amount | DecimalField(12,2) | |
| state | CharField | PLANNED / PAID / SKIPPED / FAILED |

## Relazioni FK
| Campo | → Modello | on_delete |
|---|---|---|
| subscription | [[Subscription]] | CASCADE |
| currency | [[Currency]] | PROTECT |
| transaction | [[Transaction]] | SET_NULL (1:1) |
