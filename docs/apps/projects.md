---
title: projects
tags: [app, projects]
aliases: [crm, customers, management]
---

# Projects App

Project and customer relationship management with sub-projects, activities, and categories.

## Models

| Model                      | Description                    | Key Fields                                                                     |
| -------------------------- | ------------------------------ | ------------------------------------------------------------------------------ |
| `Customer`                 | Customer/client records        | name, email, phone, notes                                                      |
| `Project`                  | Projects linked to customers   | name, customer, description, category, is_archived                             |
| `SubProject`               | Sub-projects within projects   | title, description, status, priority, start_date, due_date, completion_percent |
| `SubProjectActivity`       | Activities within sub-projects | title, description, status, due_date, ordering                                 |
| `ProjectNote`              | Notes with attachments         | project, content, attachment                                                   |
| `Category`                 | Generic categories (global)    | name, parent                                                                   |
| `ProjectHeroActionsConfig` | Hero actions per project       | user, project, config                                                          |

### SubProject Status

PLANNED, IN_PROGRESS, BLOCKED, DONE

### SubProject Priority

LOW, MEDIUM, HIGH, CRITICAL

### SubProjectActivity Status

TODO, IN_PROGRESS, BLOCKED, DONE

## URLs

| Route | Name | Description |
|-------|------|-------------|
| `/` | projects-dashboard | Projects dashboard |
| `/view` | projects-detail | Project detail view |
| `/subprojects/add` | projects-subproject-add | Add subproject |
| `/subprojects/view` | projects-subproject-detail | Subproject detail |
| `/subprojects/update` | projects-subproject-update | Update subproject |
| `/storyboard` | projects-storyboard | Project storyboard |
| `/hero-actions` | projects-hero-actions | Hero actions config |
| `/api/add` | projects-add | Add project API |
| `/api/update` | projects-update | Update project API |
| `/categories/` | projects-categories | Categories management |

## Related Apps

- [[finance_hub]] - Quote, Invoice, WorkOrder linking
- [[contacts]] - Customer model
- [[transactions]] - Transaction linking
- [[agenda]] - AgendaItem linking
- [[planner]] - PlannerItem linking
- [[routines]] - RoutineItem linking
- [[todo]] - Task linking