---
title: workbench
tags: [app, workbench]
aliases: [debug, admin, development]
---

# Workbench App

Developer/debug tool for superusers only. Provides system utilities and database inspection.

## Models

| Model | Description | Key Fields |
|-------|-------------|------------|
| `WorkbenchItem` | Work items | title, kind, status, note |
| `DebugChangeLog` | Change history | user, source, action, app_label, model_name, object_id, before, after |

### WorkbenchItem Kind

- `IMPORT` - Import
- `REPORT` - Report
- `DEBUG` - Debug

### WorkbenchItem Status

- `OPEN` - Open
- `IN_PROGRESS` - In progress
- `DONE` - Done

### DebugChangeLog Action

- `CREATE` - Create
- `UPDATE` - Update
- `DELETE` - Delete
- `CUSTOM` - Custom

## Security

- **Superuser only** - All views protected with `superuser_only` decorator
- Redirects non-authenticated users to login
- Returns 403 Forbidden for non-superusers

## URLs

| Route | Name | Description |
|-------|------|-------------|
| `/` | workbench-dashboard | Workbench dashboard |
| `/api/add` | workbench-add | Add work item |
| `/api/remove` | workbench-remove | Remove work item |
| `/api/update` | workbench-update | Update work item |
| `/debug/logs` | workbench-debug-logs | Debug logs view |
| `/debug/radicale` | workbench-debug-radicale | Radicale debug |
| `/debug/api-endpoints` | workbench-api-endpoints | API endpoints list |
| `/debug/schema` | workbench-db-schema | Database schema view |

## Related Apps

- [[core]] - Uses core user model for change logs