---
title: VatCode
tags: [db, model, finance, finance_hub]
---

# VatCode
**App:** `finance_hub` · **Tabella:** `finance_hub_vatcode`
**Base:** `OwnedModel`, `TimeStampedModel`

Codice IVA con aliquota (es. IVA22, ESENTE).

## Campi principali
| Campo | Tipo | Note |
|---|---|---|
| code | CharField(20) | unique per owner |
| description | CharField(120) | |
| rate | DecimalField(5,2) | default 22.00 |
| is_active | BooleanField | |

## Relazioni inverse
- `quotes` ← [[Quote]]
