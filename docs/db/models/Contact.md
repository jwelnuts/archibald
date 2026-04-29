---
title: Contact
tags: [db, model, contacts]
---

# Contact
**App:** `contacts` · **Tabella:** `contacts_contact`
**Base:** `OwnedModel`, `TimeStampedModel`

Rubrica contatti: persona, azienda, ente o ibrido. Può avere ruoli multipli (cliente, fornitore, payee, income source).

## Campi principali
| Campo | Tipo | Note |
|---|---|---|
| display_name | CharField(160) | unique per owner |
| entity_type | CharField | PERSON / HYBRID / ENTITY / COMPANY |
| person_name | CharField(160) | |
| business_name | CharField(160) | |
| email | EmailField | |
| phone | CharField(40) | |
| role_customer | BooleanField | |
| role_supplier | BooleanField | |
| role_payee | BooleanField | |
| role_income_source | BooleanField | |
| is_active | BooleanField | |

## Relazioni inverse
- `toolbox` ← [[ContactToolbox]] (1:1)
- `delivery_addresses` ← [[ContactDeliveryAddress]]
