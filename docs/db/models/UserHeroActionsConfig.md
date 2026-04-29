---
title: UserHeroActionsConfig
tags: [db, model, core]
---

# UserHeroActionsConfig
**App:** `core` · **Tabella:** `core_userheroactionsconfig`
**Base:** `models.Model`

Configurazione azioni rapide globali dell'utente (hero actions per modulo).

## Campi principali
| Campo | Tipo | Note |
|---|---|---|
| config | JSONField | mappa modulo → lista azioni visibili |

## Relazioni FK
| Campo | → Modello | on_delete |
|---|---|---|
| user | User (auth) | CASCADE (1:1) |
