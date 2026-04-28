---
title: transactions
tags: [app, transactions]
aliases: [finances, ledger, payments]
---

# Transactions App

Manages all financial transactions including income, expenses, and transfers.

## Models

| Model | Description | Key Fields |
|-------|-------------|------------|
| `Transaction` | Financial transaction | tx_type, date, amount, currency, account, project, category, payee, note, attachment, tags |

### Transaction Types

- `IN` - Income
- `OUT` - Expense
- `XFER` - Transfer

## Relationships

- Links to `finance_hub.Currency`
- Links to `subscriptions.Account`
- Links to `projects.Project` (optional)
- Links to `projects.Category` (optional)
- Links to `core.Payee` (optional)
- Links to `finance_hub.IncomeSource` (optional)
- Links to `subscriptions.Subscription` (for auto-generated from subscriptions)
- ManyToMany to `subscriptions.Tag`

## URLs

| Route | Name | Description |
|-------|------|-------------|
| `/` | transactions-dashboard | Transaction dashboard |
| `/partials/board` | transactions-board | Board partial view |
| `/partials/form` | transactions-form | Transaction form partial |
| `/partials/delete` | transactions-delete | Delete confirmation partial |

## Related Apps

- [[finance_hub]] - Account, Currency, IncomeSource, Tag models
- [[projects]] - Project, Category linking
- [[core]] - Payee model
- [[subscriptions]] - Subscription linking for auto-generated transactions