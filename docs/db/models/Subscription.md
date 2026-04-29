---
title: Subscription
tags: [db, model, finance, finance_hub]
---

# Subscription
**App:** `finance_hub` · **Tabella:** `finance_hub_subscription`
**Base:** `OwnedModel`, `TimeStampedModel`

Abbonamento ricorrente (Netflix, AWS, affitto...). Genera [[SubscriptionOccurrence]] pianificate.

## Campi principali
| Campo | Tipo | Note |
|---|---|---|
| name | CharField(160) | unique per owner |
| status | CharField | ACTIVE / PAUSED / CANCELED |
| amount | DecimalField(12,2) | |
| start_date | DateField | |
| next_due_date | DateField | |
| end_date | DateField | opzionale |
| interval | PositiveSmallIntegerField | default 1 |
| interval_unit | CharField | DAY / WEEK / MONTH / YEAR |
| autopay | BooleanField | |

## Relazioni FK
| Campo | → Modello | on_delete |
|---|---|---|
| account | [[Account]] | PROTECT |
| currency | [[Currency]] | PROTECT |
| payee | [[Payee]] | SET_NULL |
| category | [[Category]] | SET_NULL |
| project | [[Project]] | SET_NULL |

## Relazioni M2M
| Campo | → Modello |
|---|---|
| tags | [[Tag]] |

## Relazioni inverse
- `occurrences` ← [[SubscriptionOccurrence]]
- `generated_transactions` ← [[Transaction]]
