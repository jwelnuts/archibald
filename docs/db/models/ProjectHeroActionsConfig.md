---
title: ProjectHeroActionsConfig
tags: [db, model, projects]
---

# ProjectHeroActionsConfig
**App:** `projects` · **Tabella:** `projects_projectheroactionsconfig`
**Base:** `models.Model`

Configurazione azioni rapide (hero actions) per (utente, progetto).

## Campi principali
| Campo | Tipo | Note |
|---|---|---|
| config | JSONField | lista azioni visibili |

## Relazioni FK
| Campo | → Modello | on_delete |
|---|---|---|
| user | User (auth) | CASCADE |
| project | [[Project]] | CASCADE |
