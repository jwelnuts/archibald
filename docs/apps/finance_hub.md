---
title: finance_hub
tags: [app, finance_hub]
aliases: [finances, accounting, invoicing, quotes, invoices]
---

# Finance Hub

Central hub for all financial operations including quotes, invoices, work orders, subscriptions, and account management.

## Models

| Model | Description | Key Fields |
|-------|-------------|------------|
| `IncomeSource` | Money sources (clients, refunds, scholarships) | name, website |
| `VatCode` | VAT codes with rates | code, description, rate, is_active |
| `PaymentMethod` | Payment methods (bank transfer, card, etc.) | name, description, is_active |
| `ShippingMethod` | Shipping methods | name, description, is_active |
| `Currency` | Currency codes (global, not owned) | code, name, symbol |
| `Tag` | Tags for subscriptions | name |
| `Account` | Financial accounts | name, kind (BANK/CARD/CASH/INVEST), currency, opening_balance, is_active |
| `Subscription` | Recurring subscriptions | name, payee, category, project, account, currency, amount, interval, status |
| `SubscriptionOccurrence` | Individual subscription payments | subscription, due_date, amount, state, transaction |
| `Quote` | Customer quotes | code, title, customer, project, dates, amounts, status, public_access_token |
| `QuoteLine` | Quote line items | quote, row_order, code, description, net_amount, gross_amount, quantity, discount |
| `Invoice` | Customer invoices | code, title, quote, customer, project, dates, amounts, status |
| `WorkOrder` | Work orders | code, title, customer, project, dates, estimated_amount, final_amount, status |

### Status Enums

**Quote Status**: DRAFT, SENT, APPROVED, REJECTED, EXPIRED
**Invoice Status**: DRAFT, ISSUED, PAID, OVERDUE, CANCELED
**WorkOrder Status**: OPEN, IN_PROGRESS, WAITING, DONE, CANCELED
**Subscription Status**: ACTIVE, PAUSED, CANCELED
**SubscriptionOccurrence State**: PLANNED, PAID, SKIPPED, FAILED

## URLs

| Route | Name | Description |
|-------|------|-------------|
| `/` | finance-hub-dashboard | Main dashboard |
| `/vat-codes/` | finance-hub-vat-codes | VAT code management |
| `/subscriptions/` | subs-dashboard | Subscriptions dashboard |
| `/subscriptions/board` | subs-board | Subscription board view |
| `/subscriptions/add` | subs-add | Add subscription |
| `/subscriptions/pay` | subs-pay | Pay subscription |
| `/quotes/` | finance-hub-quotes | Quotes list |
| `/quotes/add` | finance-hub-quotes-add | Create quote |
| `/quotes/share` | finance-hub-quotes-share | Share quote (public access) |
| `/quotes/confirm/<token>` | finance-hub-quotes-public | Public quote confirmation |
| `/invoices/` | finance-hub-invoices | Invoices list |
| `/work-orders/` | finance-hub-work-orders | Work orders list |

## Related Apps

- [[transactions]] - Transaction records use Account, Currency
- [[projects]] - Projects linked to Quotes, Invoices, WorkOrders
- [[contacts]] - Customers linked to Quotes, Invoices
- [[core]] - Payee (from core app)