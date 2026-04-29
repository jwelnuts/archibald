---
title: SubProject
tags: [db, model, projects]
---

# SubProject
**App:** `projects` · **Tabella:** `projects_subproject`
**Base:** `OwnedModel`, `TimeStampedModel`

Sotto-progetto con stato, priorità e percentuale avanzamento.

## Campi principali
| Campo | Tipo | Note |
|---|---|---|
| title | CharField(140) | unique per (owner, project) |
| status | CharField | planned / in_progress / blocked / done |
| priority | CharField | low / medium / high / critical |
| start_date | DateField | opzionale |
| due_date | DateField | opzionale |
| completion_percent | PositiveSmallIntegerField | 0-100 |
| is_archived | BooleanField | |

## Relazioni FK
| Campo | → Modello | on_delete |
|---|---|---|
| project | [[Project]] | CASCADE |

## Relazioni inverse
- `activities` ← [[SubProjectActivity]]
