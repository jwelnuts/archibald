---
title: Payee
tags: [db, model, core]
---

# Payee
**App:** `core` · **Tabella:** `core_payee`
**Base:** `OwnedModel`, `TimeStampedModel`

Beneficiario/controparte di transazioni e abbonamenti (es. Netflix, Enel, AWS).

## Campi principali
| Campo | Tipo | Note |
|---|---|---|
| name | CharField(160) | unique per owner |
| website | URLField | |

## Relazioni inverse
- `transactions` ← [[Transaction]]
- `subscriptions` ← [[Subscription]]
