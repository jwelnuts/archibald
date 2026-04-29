---
title: ProjectNote
tags: [db, model, projects]
---

# ProjectNote
**App:** `projects` · **Tabella:** `projects_projectnote`
**Base:** `OwnedModel`, `TimeStampedModel`

Nota testuale (con allegato opzionale) associata a un [[Project]].

## Campi principali
| Campo | Tipo | Note |
|---|---|---|
| content | TextField | |
| attachment | FileField | opzionale |

## Relazioni FK
| Campo | → Modello | on_delete |
|---|---|---|
| project | [[Project]] | CASCADE |
