---
title: agenda
tags: [app, agenda]
aliases: [calendar, planner, worklog, hours]
---

# Agenda App

Daily agenda and work log management with activities, reminders, and time tracking.

## Models

| Model | Description | Key Fields |
|-------|-------------|------------|
| `AgendaItem` | Agenda items (activities/reminders) | title, item_type, due_date, due_time, project, status, note |
| `WorkLog` | Daily work logs | work_date, time_start, time_end, lunch_break_minutes, hours, note |

### AgendaItem Types

- `ACTIVITY` - Attivita
- `REMINDER` - Reminder

### AgendaItem Status

- `PLANNED` - Pianificata
- `DONE` - Completata

## Constraints

- One `WorkLog` per day per user

## URLs

| Route | Name | Description |
|-------|------|-------------|
| `/` | agenda-dashboard | Agenda dashboard |
| `/panel` | agenda-panel | Agenda panel view |
| `/snapshot` | agenda-snapshot | Agenda snapshot |
| `/item-action` | agenda-item-action | Item action (complete, etc.) |
| `/preferences` | agenda-preferences | Agenda preferences |

## Related Apps

- [[projects]] - Project linking
- [[core]] - CalDAV/DavCalendarGrant integration