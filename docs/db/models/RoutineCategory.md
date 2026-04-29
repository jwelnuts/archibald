---
title: RoutineCategory
tags: [db, model, planning, routines]
---

# RoutineCategory
**App:** `routines` · **Tabella:** `routines_routinecategory`
**Base:** `OwnedModel`, `TimeStampedModel`

Categoria per raggruppare [[Routine]] e [[RoutineItem]].

## Campi principali
| Campo | Tipo | Note |
|---|---|---|
| name | CharField(120) | unique per owner |
| is_active | BooleanField | |

## Relazioni inverse
- `routines` ← [[Routine]]
- `routine_items` ← [[RoutineItem]]
