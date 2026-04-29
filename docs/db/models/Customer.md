---
title: Customer
tags: [db, model, projects]
---

# Customer
**App:** `projects` · **Tabella:** `projects_customer`
**Base:** `OwnedModel`, `TimeStampedModel`

Cliente associabile a progetti, preventivi, fatture e ordini di lavoro.

## Campi principali
| Campo | Tipo | Note |
|---|---|---|
| name | CharField(160) | unique per owner |
| email | EmailField | |
| phone | CharField(40) | |
| notes | TextField | |

## Relazioni inverse
- `projects` ← [[Project]]
- `finance_quotes` ← [[Quote]]
- `finance_invoices` ← [[Invoice]]
- `finance_work_orders` ← [[WorkOrder]]
