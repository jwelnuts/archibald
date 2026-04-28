---
title: planner
tags: [app, planner]
aliases: [planning, tasks, budget]
---

# Planner App

Financial and task planning with amounts, categories, and due dates.

## Models

| Model | Description | Key Fields |
|-------|-------------|------------|
| `PlannerItem` | Planning items | title, due_date, amount, category, project, note, status |

### PlannerItem Status

- `PLANNED` - Planned
- `DONE` - Done
- `SKIPPED` - Skipped

## URLs

| Route | Name | Description |
|-------|------|-------------|
| `/` | planner-dashboard | Planner dashboard |
| `/add` | planner-add | Add planner item |
| `/update` | planner-update | Update planner item |
| `/remove` | planner-remove | Remove planner item |

## Related Apps

- [[projects]] - Project linking