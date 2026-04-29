---
title: PlannerItem
tags: [db, model, planning, planner]
---

# PlannerItem
**App:** `planner` · **Tabella:** `planner_planneritem`
**Base:** `OwnedModel`, `TimeStampedModel`

Voce pianificata con importo opzionale, categoria e progetto.

## Campi principali
| Campo | Tipo | Note |
|---|---|---|
| title | CharField(200) | |
| due_date | DateField | opzionale |
| amount | DecimalField(12,2) | opzionale |
| status | CharField | PLANNED / DONE / SKIPPED |
| note | TextField | |

## Relazioni FK
| Campo | → Modello | on_delete |
|---|---|---|
| category | [[Category]] | SET_NULL |
| project | [[Project]] | SET_NULL |
