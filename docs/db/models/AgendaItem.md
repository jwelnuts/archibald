---
title: AgendaItem
tags: [db, model, planning, agenda]
---

# AgendaItem
**App:** `agenda` · **Tabella:** `agenda_agendaitem`
**Base:** `OwnedModel`, `TimeStampedModel`

Attività o reminder in agenda con data e ora.

## Campi principali
| Campo | Tipo | Note |
|---|---|---|
| title | CharField(200) | |
| item_type | CharField | ACTIVITY / REMINDER |
| due_date | DateField | |
| due_time | TimeField | opzionale |
| status | CharField | PLANNED / DONE |
| note | TextField | |

## Relazioni FK
| Campo | → Modello | on_delete |
|---|---|---|
| project | [[Project]] | SET_NULL |
