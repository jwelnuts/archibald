---
title: Category
tags: [db, model, projects]
---

# Category
**App:** `projects` · **Tabella:** `common_category`
**Base:** `OwnedModel`, `TimeStampedModel`

Categoria generica gerarchica (es. Streaming, Casa, Trasporti). Usata da transazioni, abbonamenti, task e planner.

## Campi principali
| Campo | Tipo | Note |
|---|---|---|
| name | CharField(80) | unique per owner |

## Relazioni FK
| Campo | → Modello | on_delete |
|---|---|---|
| parent | [[Category]] (self) | SET_NULL |

## Relazioni inverse
- `children` ← [[Category]]
- `transactions` ← [[Transaction]]
- `subscriptions` ← [[Subscription]]
- `todo_tasks` ← [[Task]]
- `planner_items` ← [[PlannerItem]]
- `projects` ← [[Project]]
