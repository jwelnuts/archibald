---
title: ShippingMethod
tags: [db, model, finance, finance_hub]
---

# ShippingMethod
**App:** `finance_hub` · **Tabella:** `finance_hub_shippingmethod`
**Base:** `OwnedModel`, `TimeStampedModel`

Metodo di spedizione selezionabile nei preventivi.

## Campi principali
| Campo | Tipo | Note |
|---|---|---|
| name | CharField(120) | unique per owner |
| description | CharField(255) | |
| is_active | BooleanField | |

## Relazioni inverse
- `quotes` ← [[Quote]]
