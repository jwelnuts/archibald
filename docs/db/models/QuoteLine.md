---
title: QuoteLine
tags: [db, model, finance, finance_hub]
---

# QuoteLine
**App:** `finance_hub` · **Tabella:** `finance_hub_quoteline`
**Base:** `OwnedModel`, `TimeStampedModel`

Riga di un preventivo (codice, descrizione, quantità, prezzo, sconto).

## Campi principali
| Campo | Tipo | Note |
|---|---|---|
| row_order | PositiveSmallIntegerField | ordinamento |
| code | CharField(60) | |
| description | CharField(255) | |
| net_amount | DecimalField(12,2) | prezzo unitario netto |
| quantity | DecimalField(10,2) | default 1 |
| discount | DecimalField(5,2) | % sconto |
| vat_code | CharField(20) | stringa, non FK |

## Relazioni FK
| Campo | → Modello | on_delete |
|---|---|---|
| quote | [[Quote]] | CASCADE |
