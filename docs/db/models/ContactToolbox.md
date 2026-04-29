---
title: ContactToolbox
tags: [db, model, contacts]
---

# ContactToolbox
**App:** `contacts` · **Tabella:** `contacts_contacttoolbox`
**Base:** `OwnedModel`, `TimeStampedModel`

Estensione 1:1 di [[Contact]] con note interne e listini prezzi.

## Campi principali
| Campo | Tipo | Note |
|---|---|---|
| internal_notes | TextField | |
| extra_data | JSONField | |

## Relazioni FK
| Campo | → Modello | on_delete |
|---|---|---|
| contact | [[Contact]] | CASCADE (1:1) |

## Relazioni inverse
- `price_lists` ← [[ContactPriceList]]
