---
title: PaymentMethod
tags: [db, model, finance, finance_hub]
---

# PaymentMethod
**App:** `finance_hub` · **Tabella:** `finance_hub_paymentmethod`
**Base:** `OwnedModel`, `TimeStampedModel`

Metodo di pagamento selezionabile nei preventivi (es. Bonifico, PayPal).

## Campi principali
| Campo | Tipo | Note |
|---|---|---|
| name | CharField(120) | unique per owner |
| description | CharField(255) | |
| is_active | BooleanField | |

## Relazioni inverse
- `quotes` ← [[Quote]]
