---
title: Django Apps Overview
tags: [architecture, apps, django]
aliases: [applications, modules]
---

# Django Apps Overview

This document describes all Django applications in the MIO Master project.

## Main Apps

### finance_hub

**Purpose:** Core finance module - quotes, invoices, work orders, accounts, subscriptions

**Key Models:**
- `Quote` - Commercial quotes with lines (QuoteLine)
- `Invoice` - Customer invoices
- `WorkOrder` - Work order tracking
- `Account` - Financial accounts (BANK, CARD, CASH, INVEST, OTHER)
- `Currency` - Currency codes (EUR, USD, etc.)
- `VatCode` - VAT rates (22%, 10%, 4%, 0%)
- `PaymentMethod` - Payment methods for quotes
- `ShippingMethod` - Shipping methods for quotes
- `Tag` - Tags for transactions
- `IncomeSource` - Income sources (clients, refunds, grants)
- `Subscription` - Recurring subscriptions
- `SubscriptionOccurrence` - Individual subscription payment instances

**Related:** [[models#finance_hub|Models Reference]]

---

### subscriptions

**Purpose:** Re-exports finance_hub models for backwards compatibility

**Models:** (imported from finance_hub)

---

### transactions

**Purpose:** Financial transactions hub - income, expenses, transfers

**Key Models:**
- `Transaction` - Single transaction record
  - `tx_type`: IN (income), OUT (expense), XFER (transfer)
  - Links to: Account, Currency, Project, Category, Payee, IncomeSource, Subscription

**Related:** [[models#transactions|Models Reference]]

---

### projects

**Purpose:** Project management with customers, categories, storyboard

**Key Models:**
- `Project` - Main project entity
- `Customer` - Client/customer records
- `Category` - Reusable categories for transactions/subscriptions
- `SubProject` - Sub-project with status tracking
- `SubProjectActivity` - Activities within subprojects
- `ProjectNote` - Notes with attachments
- `ProjectHeroActionsConfig` - Per-project hero action overrides

**Related:** [[models#projects|Models Reference]]

---

### core

**Purpose:** Main application - authentication, dashboard, DAV integration

**Key Models:**
- `Payee` - Payee/beneficiary records (Netflix, Enel, AWS, etc.)
- `MobileApiSession` - Mobile API token management
- `DavAccount` - CalDAV/CardDAV account credentials
- `DavExternalAccount` - External DAV accounts (for sharing)
- `DavTeam` - Team/Dav collection groups
- `DavManagedCalendar` - User-managed calendars
- `DavCalendarGrant` - Calendar access grants
- `UserHeroActionsConfig` - Hero actions configuration
- `UserNavConfig` - Navigation configuration

---

### contacts

**Purpose:** Contact management with delivery addresses, price lists

**Key Models:**
- `Contact` - Contact with roles (customer, supplier, payee, income_source)
- `ContactDeliveryAddress` - Delivery addresses
- `ContactToolbox` - Extra data storage per contact
- `ContactPriceList` - Custom pricing per contact
- `ContactPriceListItem` - Individual price list items

**Related:** [[models#contacts|Models Reference]]

---

### agenda

**Purpose:** Calendar and work logging

**Key Models:**
- `AgendaItem` - Calendar items (activities, reminders)
- `WorkLog` - Daily work hours logging

---

### planner

**Purpose:** Weekly planning

**Key Models:**
- `PlannerItem` - Items planned with due date, amount, category, project

---

### routines

**Purpose:** Daily/weekly routine tracking

**Key Models:**
- `RoutineCategory` - Categories for routines
- `Routine` - Named routine grouping
- `RoutineItem` - Individual routine item with weekday assignment
- `RoutineCheck` - Weekly check records (planned/done/skipped)

---

### todo

**Purpose:** Task management

**Key Models:**
- `Task` - Task with status (OPEN/IN_PROGRESS/DONE), priority, due date

---

### income

**Purpose:** Legacy stub - re-exports IncomeSource from finance_hub

---

### outcome

**Purpose:** Legacy stub - re-exports WorkOrder from finance_hub

---

### link_storage

**Purpose:** URL bookmarks/links with categories

**Key Models:**
- `Link` - URL with category, importance, note

---

### memory_stock

**Purpose:** Memory capture from emails and links

**Key Models:**
- `MemoryStockItem` - Captured item with source metadata

---

### vault

**Purpose:** Encrypted credential storage

**Key Models:**
- `VaultProfile` - User TOTP profile
- `VaultItem` - Encrypted password/note items

---

### archibald

**Purpose:** AI assistant with conversation threads

**Key Models:**
- `ArchibaldThread` - Conversation thread
- `ArchibaldMessage` - Individual messages with roles
- `ArchibaldPersonaConfig` - Persona settings (presets, psychology features)
- `ArchibaldInstructionState` - Custom instruction overrides

---

### archibald_mail

**Purpose:** Email AI processing, inbox triage

**Related to:** [[archibald|Chat AI]]

---

### workbench

**Purpose:** Technical tooling (superuser only)

**Key Models:**
- (Technical items and debug utilities)

---

## App Relationships Map

```
core (auth, DAV)
    |
    +-- finance_hub (quotes, invoices, subscriptions, accounts)
    |       |
    |       +-- transactions
    |       +-- projects (Project, Customer, Category)
    |       +-- subscriptions (re-export)
    |
    +-- contacts
    +-- agenda
    +-- planner
    +-- routines
    +-- todo
    +-- vault
    +-- archibald
    +-- archibald_mail
    +-- memory_stock
    +-- link_storage
    +-- workbench
```

---

## Related Documentation

- [[models|Database Models]] - Full ERD
- [[views|Views & URLs]] - By app
- [[api|API Endpoints]]
- [[business-logic|Business Logic]] - Workflows
- [[deployment|Deployment]] - Docker setup