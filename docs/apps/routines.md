---
title: routines
tags: [app, routines]
aliases: [habits, recurring tasks, weekly]
---

# Routines App

Weekly routines and habit tracking with check-off system.

## Models

| Model | Description | Key Fields |
|-------|-------------|------------|
| `RoutineCategory` | Routine categories | name, is_active |
| `Routine` | Routine groups | name, description, category, is_active |
| `RoutineItem` | Individual routine items | routine, project, title, weekday, time_start, time_end, note, is_active, schema |
| `RoutineCheck` | Weekly completion checks | item, week_start, status, data |

### Weekday Values

0=Monday, 1=Tuesday, 2=Wednesday, 3=Thursday, 4=Friday, 5=Saturday, 6=Sunday

### RoutineCheck Status

- `PLANNED` - Planned
- `DONE` - Done
- `SKIPPED` - Skipped

## URLs

| Route | Name | Description |
|-------|------|-------------|
| `/` | todos-dashboard | Routines dashboard |
| `/stats` | todos-stats | Routines statistics |
| `/check` | todos-check | Check routine item |
| `/api/add` | todos-add | Add routine |
| `/api/update` | todos-update | Update routine |
| `/api/remove` | todos-remove | Remove routine |
| `/items/add` | todos-items-add | Add routine item |
| `/items/update` | todos-items-update | Update routine item |
| `/items/remove` | todos-items-remove | Remove routine item |

## Related Apps

- [[projects]] - Project linking for RoutineItem
- [[core]] - Mobile API integration (core app)