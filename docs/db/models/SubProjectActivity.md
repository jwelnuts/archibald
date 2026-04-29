---
title: SubProjectActivity
tags: [db, model, projects]
---

# SubProjectActivity
**App:** `projects` · **Tabella:** `projects_subprojectactivity`
**Base:** `OwnedModel`, `TimeStampedModel`

Attività atomica dentro un [[SubProject]].

## Campi principali
| Campo | Tipo | Note |
|---|---|---|
| title | CharField(160) | |
| status | CharField | todo / in_progress / blocked / done |
| due_date | DateField | opzionale |
| ordering | PositiveIntegerField | |

## Relazioni FK
| Campo | → Modello | on_delete |
|---|---|---|
| subproject | [[SubProject]] | CASCADE |
