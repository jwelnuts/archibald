---
title: ContactDeliveryAddress
tags: [db, model, contacts]
---

# ContactDeliveryAddress
**App:** `contacts` · **Tabella:** `contacts_contactdeliveryaddress`
**Base:** `OwnedModel`, `TimeStampedModel`

Indirizzo di consegna associato a un [[Contact]], usato nei [[Quote]].

## Campi principali
| Campo | Tipo | Note |
|---|---|---|
| label | CharField(120) | |
| line1 | CharField(180) | |
| city | CharField(120) | |
| postal_code | CharField(20) | |
| country | CharField(120) | default Italia |
| is_default | BooleanField | uno solo per contatto |
| is_active | BooleanField | |

## Relazioni FK
| Campo | → Modello | on_delete |
|---|---|---|
| contact | [[Contact]] | CASCADE |

## Relazioni inverse
- `finance_quotes` ← [[Quote]]
