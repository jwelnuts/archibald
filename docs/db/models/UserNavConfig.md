---
title: UserNavConfig
tags: [db, model, core]
---

# UserNavConfig
**App:** `core` · **Tabella:** `core_usernavconfig`
**Base:** `models.Model`

Ordine e visibilità moduli nella navigazione dell'utente.

## Campi principali
| Campo | Tipo | Note |
|---|---|---|
| config | JSONField | ordine moduli e scorciatoie |

## Relazioni FK
| Campo | → Modello | on_delete |
|---|---|---|
| user | User (auth) | CASCADE (1:1) |
