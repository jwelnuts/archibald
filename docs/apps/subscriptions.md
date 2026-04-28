---
title: subscriptions
tags: [app, subscriptions]
aliases: [recurring, payments, billing]
---

# Subscriptions App

Wrapper app for subscription-related models from finance_hub. Provides subscription tracking and payment management.

## Models (from finance_hub)

| Model | Description |
|-------|-------------|
| `Currency` | Currency codes |
| `Tag` | Subscription tags |
| `Account` | Financial accounts |
| `Subscription` | Recurring subscriptions |
| `SubscriptionOccurrence` | Individual subscription payment instances |

## URLs

| Route | Name | Description |
|-------|------|-------------|
| `/` | subs-dashboard | Subscriptions dashboard |
| `/api/board` | subs-board | Board API endpoint |
| `/api/add` | subs-add | Add subscription |
| `/api/remove` | subs-remove | Remove subscription |
| `/api/update` | subs-update | Update subscription |
| `/api/pay` | subs-pay | Pay/mark occurrence as paid |

## Related Apps

- [[finance_hub]] - Source of models (Account, Subscription, etc.)
- [[transactions]] - Transaction generation for paid occurrences