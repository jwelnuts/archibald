---
title: Routine
tags: [db, model, planning, routines]
---

# Routine
**App:** `routines` · **Tabella:** `routines_routine`
**Base:** `OwnedModel`, `TimeStampedModel`

Contenitore di [[RoutineItem]] settimanali.

## Campi principali
| Campo | Tipo | Note |
|---|---|---|
| name | CharField(160) | unique per owner |
| description | TextField | |
| is_active | BooleanField | |

## Relazioni FK
| Campo | → Modello | on_delete |
|---|---|---|
| category | [[RoutineCategory]] | SET_NULL |

## Relazioni inverse
- `items` ← [[RoutineItem]]
