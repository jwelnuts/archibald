---
title: RoutineCheck
tags: [db, model, planning, routines]
---

# RoutineCheck
**App:** `routines` · **Tabella:** `routines_routinecheck`
**Base:** `OwnedModel`, `TimeStampedModel`

Traccia lo stato di un [[RoutineItem]] per una settimana specifica.

## Campi principali
| Campo | Tipo | Note |
|---|---|---|
| week_start | DateField | lunedì della settimana |
| status | CharField | PLANNED / DONE / SKIPPED |
| data | JSONField | dati extra custom |

## Relazioni FK
| Campo | → Modello | on_delete |
|---|---|---|
| item | [[RoutineItem]] | CASCADE |

## Note
- unique su (owner, item, week_start)
