---
title: income
tags: [app, income]
aliases: [revenue, earnings, sources]
---

# Income App

Wrapper app for income source management from finance_hub.

## Models (from finance_hub)

| Model | Description |
|-------|-------------|
| `IncomeSource` | Money sources (clients, refunds, scholarships) |

## URLs

| Route | Name | Description |
|-------|------|-------------|
| `/` | income-dashboard | Income dashboard |
| `/api/add` | income-add | Add income source |
| `/api/remove` | income-remove | Remove income source |
| `/api/update` | income-update | Update income source |

## Related Apps

- [[finance_hub]] - IncomeSource model