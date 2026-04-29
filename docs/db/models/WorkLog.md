---
title: WorkLog
tags: [db, model, planning, agenda]
---

# WorkLog
**App:** `agenda` · **Tabella:** `agenda_worklog`
**Base:** `OwnedModel`, `TimeStampedModel`

Registro ore lavorate: uno per giorno per utente.

## Campi principali
| Campo | Tipo | Note |
|---|---|---|
| work_date | DateField | unique per owner |
| time_start | TimeField | opzionale |
| time_end | TimeField | opzionale |
| lunch_break_minutes | PositiveSmallIntegerField | |
| hours | DecimalField(5,2) | |
| note | TextField | |
