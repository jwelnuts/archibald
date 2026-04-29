---
title: ContactPriceListItem
tags: [db, model, contacts]
---

# ContactPriceListItem
**App:** `contacts` · **Tabella:** `contacts_contactpricelistitem`
**Base:** `OwnedModel`, `TimeStampedModel`

Voce di un [[ContactPriceList]] con fasce di quantità e prezzo unitario.

## Campi principali
| Campo | Tipo | Note |
|---|---|---|
| code | CharField(60) | |
| title | CharField(180) | |
| min_quantity | DecimalField(10,2) | |
| max_quantity | DecimalField(10,2) | opzionale |
| unit_price | DecimalField(12,2) | |
| is_active | BooleanField | |

## Relazioni FK
| Campo | → Modello | on_delete |
|---|---|---|
| price_list | [[ContactPriceList]] | CASCADE |
