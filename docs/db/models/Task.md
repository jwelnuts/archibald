---
title: Task
tags: [db, model, planning, todo]
---

# Task
**App:** `todo` · **Tabella:** `todo_task`
**Base:** `OwnedModel`, `TimeStampedModel`

Task, reminder o appuntamento con priorità, scadenza e stato.

## Campi principali
| Campo | Tipo | Note |
|---|---|---|
| title | CharField(160) | |
| item_type | CharField | TASK / REMINDER / APPOINTMENT |
| status | CharField | OPEN / IN_PROGRESS / DONE |
| priority | CharField | LOW / MEDIUM / HIGH |
| due_date | DateField | opzionale |
| due_time | TimeField | opzionale |
| note | TextField | |

## Relazioni FK
| Campo | → Modello | on_delete |
|---|---|---|
| project | [[Project]] | SET_NULL |
| category | [[Category]] | SET_NULL |
