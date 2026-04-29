---
title: Tag
tags: [db, model, finance, finance_hub]
---

# Tag
**App:** `finance_hub` · **Tabella:** `finance_hub_tag`
**Base:** `OwnedModel`, `TimeStampedModel`

Etichetta libera riusabile su transazioni e abbonamenti.

## Campi principali
| Campo | Tipo | Note |
|---|---|---|
| name | CharField(50) | unique per owner |

## Relazioni M2M inverse
- `transactions` ← [[Transaction]]
- `subscriptions` ← [[Subscription]]
