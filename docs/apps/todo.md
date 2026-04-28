---
title: todo
tags: [app, todo]
aliases: [tasks, checklist, items]
---

# Todo App

Task and reminder management with status tracking and CalDAV sync.

## Models

| Model | Description | Key Fields |
|-------|-------------|------------|
| `Task` | Todo tasks | title, project, category, item_type, due_date, due_time, status, priority, note |

### Task Item Types

- `TASK` - Task da completare
- `REMINDER` - Reminder
- `APPOINTMENT` - Appuntamento

### Task Status

- `OPEN` - Open
- `IN_PROGRESS` - In progress
- `DONE` - Done

### Task Priority

- `LOW` - Low
- `MEDIUM` - Medium
- `HIGH` - High

## URLs

| Route | Name | Description |
|-------|------|-------------|
| `/` | todo-dashboard | Todo dashboard |
| `/api/add` | todo-add | Add task |
| `/api/remove` | todo-remove | Remove task |
| `/api/update` | todo-update | Update task |
| `/api/status` | todo-set-status | Set task status |
| `/api/sync-vtodo` | todo-sync-vtodo | Sync with vTodo format |

## Related Apps

- [[projects]] - Project linking
- [[core]] - CalDAV sync (DavAccount)