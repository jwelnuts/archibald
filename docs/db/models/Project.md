---
title: Project
tags: [db, model, projects]
---

# Project
**App:** `projects` · **Tabella:** `projects_project`
**Base:** `OwnedModel`, `TimeStampedModel`

Progetto: contenitore per note, task, transazioni, planner item e routine.

## Campi principali
| Campo | Tipo | Note |
|---|---|---|
| name | CharField(120) | unique per owner |
| description | TextField | |
| is_archived | BooleanField | |

## Relazioni FK
| Campo | → Modello | on_delete |
|---|---|---|
| customer | [[Customer]] | SET_NULL |
| category | [[Category]] | SET_NULL |

## Relazioni inverse
- `subprojects` ← [[SubProject]]
- `notes` ← [[ProjectNote]]
- `todo_tasks` ← [[Task]]
- `planner_items` ← [[PlannerItem]]
- `agenda_items` ← [[AgendaItem]]
- `routine_items` ← [[RoutineItem]]
- `transactions` ← [[Transaction]]
- `subscriptions` ← [[Subscription]]
- `finance_quotes` ← [[Quote]]
- `finance_invoices` ← [[Invoice]]
- `finance_work_orders` ← [[WorkOrder]]
