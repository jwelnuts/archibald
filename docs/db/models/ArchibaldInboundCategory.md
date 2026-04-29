---
title: ArchibaldInboundCategory
tags: [db, model, knowledge, archibald_mail]
---

# ArchibaldInboundCategory
**App:** `archibald_mail` · **Tabella:** `archibald_mail_archivaldinboundcategory`
**Base:** `OwnedModel`, `TimeStampedModel`

Categoria custom per classificare i messaggi email in entrata.

## Campi principali
| Campo | Tipo | Note |
|---|---|---|
| label | CharField(80) | unique per owner |
| is_active | BooleanField | |
| notes | TextField | |

## Relazioni inverse
- `messages` ← [[ArchibaldEmailMessage]]
