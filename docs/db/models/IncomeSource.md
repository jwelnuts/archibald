---
title: IncomeSource
tags: [db, model, finance, finance_hub]
---

# IncomeSource
**App:** `finance_hub` · **Tabella:** `finance_hub_incomesource`
**Base:** `OwnedModel`, `TimeStampedModel`

Fonte di entrate: cliente, rimborso, borsa, ecc.

## Campi principali
| Campo | Tipo | Note |
|---|---|---|
| name | CharField(160) | unique per owner |
| website | URLField | opzionale |

## Relazioni inverse
- `transactions` ← [[Transaction]]
