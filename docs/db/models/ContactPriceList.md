---
title: ContactPriceList
tags: [db, model, contacts]
---

# ContactPriceList
**App:** `contacts` · **Tabella:** `contacts_contactpricelist`
**Base:** `OwnedModel`, `TimeStampedModel`

Listino prezzi associato a un [[ContactToolbox]] (quindi a un [[Contact]]).

## Campi principali
| Campo | Tipo | Note |
|---|---|---|
| title | CharField(180) | |
| currency_code | CharField(3) | es. EUR |
| pricing_notes | TextField | |
| is_active | BooleanField | |

## Relazioni FK
| Campo | → Modello | on_delete |
|---|---|---|
| toolbox | [[ContactToolbox]] | CASCADE |

## Relazioni inverse
- `items` ← [[ContactPriceListItem]]
