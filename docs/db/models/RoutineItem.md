---
title: RoutineItem
tags: [db, model, planning, routines]
---

# RoutineItem
**App:** `routines` · **Tabella:** `routines_routineitem`
**Base:** `OwnedModel`, `TimeStampedModel`

Singola voce settimanale di una [[Routine]] (giorno, ora, progetto).

## Campi principali
| Campo | Tipo | Note |
|---|---|---|
| title | CharField(200) | |
| weekday | PositiveSmallIntegerField | 0=Lun … 6=Dom |
| time_start | TimeField | opzionale |
| time_end | TimeField | opzionale |
| is_active | BooleanField | |
| schema | JSONField | struttura dati custom |

## Relazioni FK
| Campo | → Modello | on_delete |
|---|---|---|
| routine | [[Routine]] | CASCADE |
| category | [[RoutineCategory]] | SET_NULL |
| project | [[Project]] | SET_NULL |

## Relazioni inverse
- `checks` ← [[RoutineCheck]]
