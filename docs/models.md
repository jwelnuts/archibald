---
title: Database Models
tags: [database, models, erd]
aliases: [schema, models]
---

# Database Models

This document describes all Django models and their relationships in MIO Master.

## Base Models

### common.TimeStampedModel
```python
created_at: DateTime (auto_now_add)
updated_at: DateTime (auto_now)
```

### common.OwnedModel
```python
owner: ForeignKey(User)  # All records scoped per user
```

> **Note:** Most models inherit from both TimeStampedModel and OwnedModel for timestamp and ownership tracking.

---

## finance_hub

### Currency
```
Currency (global, no owner)
├── code: Char(3) [PK, unique: EUR, USD, GBP]
├── name: Char(64)
└── symbol: Char(8)
```

### IncomeSource
```
IncomeSource (OwnedModel, TimeStampedModel)
├── name: Char(160) [unique with owner]
├── website: URL
└── FK -> owner: User
```

### VatCode
```
VatCode (OwnedModel, TimeStampedModel)
├── code: Char(20)
├── description: Char(120)
├── rate: Decimal(5,2) [22.00 default]
├── is_active: Boolean
└── FK -> owner: User
```

### PaymentMethod
```
PaymentMethod (OwnedModel, TimeStampedModel)
├── name: Char(120)
├── description: Char(255)
├── is_active: Boolean
└── FK -> owner: User
```

### ShippingMethod
```
ShippingMethod (OwnedModel, TimeStampedModel)
├── name: Char(120)
├── description: Char(255)
├── is_active: Boolean
└── FK -> owner: User
```

### Tag
```
Tag (OwnedModel, TimeStampedModel)
├── name: Char(50) [unique with owner]
└── FK -> owner: User
```

### Account
```
Account (OwnedModel, TimeStampedModel)
├── name: Char(120) [unique with owner]
├── kind: Char(10) [BANK, CARD, CASH, INVEST, OTHER]
├── FK -> currency: Currency
├── opening_balance: Decimal(12,2)
├── is_active: Boolean
└── FK -> owner: User
```

### Quote
```
Quote (OwnedModel, TimeStampedModel)
├── code: Char(40)
├── title: Char(180)
├── FK -> customer: projects.Customer [NULL]
├── FK -> delivery_address: contacts.ContactDeliveryAddress [NULL]
├── FK -> project: projects.Project [NULL]
├── issue_date: Date
├── valid_until: Date [NULL]
├── FK -> currency: Currency
├── FK -> vat_code: VatCode [NULL]
├── FK -> payment_method: PaymentMethod [NULL]
├── FK -> shipping_method: ShippingMethod [NULL]
├── amount_net: Decimal(12,2)
├── tax_amount: Decimal(12,2)
├── total_amount: Decimal(12,2)
├── status: Char(10) [DRAFT, SENT, APPROVED, REJECTED, EXPIRED]
├── note: Text
├── public_access_token: Char(96) [unique]
├── public_access_expires_at: DateTime
├── customer_signed_name: Char(180)
├── customer_signed_at: DateTime
├── customer_decision_note: Text
└── FK -> owner: User
```

### QuoteLine
```
QuoteLine (OwnedModel, TimeStampedModel)
├── FK -> quote: Quote [CASCADE]
├── row_order: PositiveSmallInteger
├── code: Char(60)
├── description: Char(255)
├── net_amount: Decimal(12,2)
├── gross_amount: Decimal(12,2)
├── quantity: Decimal(10,2)
├── discount: Decimal(5,2)
├── vat_code: Char(20)
└── FK -> owner: User
```

### Invoice
```
Invoice (OwnedModel, TimeStampedModel)
├── code: Char(40)
├── title: Char(180)
├── FK -> quote: Quote [NULL]
├── FK -> customer: projects.Customer [NULL]
├── FK -> project: projects.Project [NULL]
├── FK -> account: subscriptions.Account [NULL]
├── issue_date: Date
├── due_date: Date [NULL]
├── paid_date: Date [NULL]
├── FK -> currency: Currency
├── amount_net: Decimal(12,2)
├── tax_amount: Decimal(12,2)
├── total_amount: Decimal(12,2)
├── status: Char(10) [DRAFT, ISSUED, PAID, OVERDUE, CANCELED]
├── note: Text
└── FK -> owner: User
```

### WorkOrder
```
WorkOrder (OwnedModel, TimeStampedModel)
├── code: Char(40)
├── title: Char(180)
├── FK -> customer: projects.Customer [NULL]
├── FK -> project: projects.Project [NULL]
├── FK -> account: subscriptions.Account [NULL]
├── start_date: Date
├── end_date: Date [NULL]
├── FK -> currency: Currency
├── estimated_amount: Decimal(12,2)
├── final_amount: Decimal(12,2)
├── is_billable: Boolean
├── status: Char(12) [OPEN, IN_PROGRESS, WAITING, DONE, CANCELED]
├── note: Text
└── FK -> owner: User
```

### Subscription
```
Subscription (OwnedModel, TimeStampedModel)
├── name: Char(160)
├── FK -> payee: core.Payee [NULL]
├── FK -> category: projects.Category [NULL]
├── FK -> project: projects.Project [NULL]
├── FK -> account: Account
├── FK -> currency: Currency
├── amount: Decimal(12,2)
├── start_date: Date
├── next_due_date: Date
├── end_date: Date [NULL]
├── interval: PositiveSmallInteger
├── interval_unit: Char(8) [DAY, WEEK, MONTH, YEAR]
├── status: Char(10) [ACTIVE, PAUSED, CANCELED]
├── autopay: Boolean
├── note: Text
├── M2M -> tags: Tag
└── FK -> owner: User
```

### SubscriptionOccurrence
```
SubscriptionOccurrence (OwnedModel, TimeStampedModel)
├── FK -> subscription: Subscription [CASCADE]
├── due_date: Date
├── amount: Decimal(12,2)
├── FK -> currency: Currency
├── state: Char(10) [PLANNED, PAID, SKIPPED, FAILED]
├── FK -> transaction: transactions.Transaction [NULL, OneToOne]
└── FK -> owner: User
```

---

## projects

### Customer
```
Customer (OwnedModel, TimeStampedModel)
├── name: Char(160) [unique with owner]
├── email: Email
├── phone: Char(40)
├── notes: Text
└── FK -> owner: User
```

### Project
```
Project (OwnedModel, TimeStampedModel)
├── name: Char(120) [unique with owner]
├── FK -> customer: Customer [NULL]
├── description: Text
├── FK -> category: Category [NULL]
├── is_archived: Boolean
└── FK -> owner: User
```

### Category
```
Category (OwnedModel, TimeStampedModel)
├── name: Char(80) [unique with owner]
├── FK -> parent: Category [NULL, self-reference]
└── FK -> owner: User
```

### SubProject
```
SubProject (OwnedModel, TimeStampedModel)
├── FK -> project: Project [CASCADE]
├── title: Char(140)
├── description: Text
├── status: Char(20) [planned, in_progress, blocked, done]
├── priority: Char(20) [low, medium, high, critical]
├── start_date: Date [NULL]
├── due_date: Date [NULL]
├── completion_percent: PositiveSmallInteger
├── is_archived: Boolean
└── FK -> owner: User
```

### SubProjectActivity
```
SubProjectActivity (OwnedModel, TimeStampedModel)
├── FK -> subproject: SubProject [CASCADE]
├── title: Char(160)
├── description: Text
├── status: Char(20) [todo, in_progress, blocked, done]
├── due_date: Date [NULL]
├── ordering: PositiveInteger
└── FK -> owner: User
```

### ProjectNote
```
ProjectNote (OwnedModel, TimeStampedModel)
├── FK -> project: Project [CASCADE]
├── content: Text
├── attachment: File [NULL]
└── FK -> owner: User
```

### ProjectHeroActionsConfig
```
ProjectHeroActionsConfig
├── FK -> user: User
├── FK -> project: Project
├── config: JSON
[unique: (user, project)]
```

---

## transactions

### Transaction
```
Transaction (OwnedModel, TimeStampedModel)
├── tx_type: Char(4) [IN, OUT, XFER]
├── date: Date
├── amount: Decimal(12,2)
├── FK -> currency: Currency
├── FK -> account: Account
├── FK -> project: Project [NULL]
├── FK -> category: Category [NULL]
├── FK -> payee: core.Payee [NULL]
├── FK -> income_source: finance_hub.IncomeSource [NULL]
├── note: Text
├── attachment: File [NULL]
├── M2M -> tags: Tag
├── FK -> source_subscription: Subscription [NULL]
└── FK -> owner: User
```

---

## contacts

### Contact
```
Contact (OwnedModel, TimeStampedModel)
├── display_name: Char(160) [unique with owner]
├── entity_type: Char(10) [PERSON, HYBRID, ENTITY, COMPANY]
├── person_name: Char(160)
├── business_name: Char(160)
├── profile_image: File [NULL]
├── email: Email
├── phone: Char(40)
├── website: URL
├── city: Char(120)
├── role_customer: Boolean
├── role_supplier: Boolean
├── role_payee: Boolean
├── role_income_source: Boolean
├── notes: Text
├── is_active: Boolean
└── FK -> owner: User
```

### ContactDeliveryAddress
```
ContactDeliveryAddress (OwnedModel, TimeStampedModel)
├── FK -> contact: Contact [CASCADE]
├── row_order: PositiveSmallInteger
├── label: Char(120)
├── recipient_name: Char(160)
├── line1: Char(180)
├── line2: Char(180)
├── postal_code: Char(20)
├── city: Char(120)
├── province: Char(120)
├── country: Char(120)
├── notes: Text
├── is_default: Boolean
├── is_active: Boolean
└── FK -> owner: User
```

### ContactToolbox
```
ContactToolbox (OwnedModel, TimeStampedModel)
├── FK -> contact: Contact [OneToOne, CASCADE]
├── internal_notes: Text
├── extra_data: JSON
└── FK -> owner: User
```

### ContactPriceList
```
ContactPriceList (OwnedModel, TimeStampedModel)
├── FK -> toolbox: ContactToolbox [CASCADE]
├── title: Char(180)
├── currency_code: Char(3)
├── pricing_notes: Text
├── note: Text
├── is_active: Boolean
└── FK -> owner: User
```

### ContactPriceListItem
```
ContactPriceListItem (OwnedModel, TimeStampedModel)
├── FK -> price_list: ContactPriceList [CASCADE]
├── row_order: PositiveSmallInteger
├── code: Char(60)
├── title: Char(180)
├── description: Char(255)
├── min_quantity: Decimal(10,2)
├── max_quantity: Decimal(10,2) [NULL]
├── unit_price: Decimal(12,2)
├── is_active: Boolean
└── FK -> owner: User
```

---

## core

### Payee
```
Payee (OwnedModel, TimeStampedModel)
├── name: Char(160) [unique with owner]
├── website: URL
└── FK -> owner: User
```

### MobileApiSession
```
MobileApiSession (TimeStampedModel)
├── FK -> user: User
├── access_token_hash: Char(64) [unique]
├── refresh_token_hash: Char(64) [unique]
├── access_expires_at: DateTime
├── refresh_expires_at: DateTime
├── revoked_at: DateTime [NULL]
├── last_used_at: DateTime [NULL]
├── device_label: Char(120)
├── user_agent: Char(255)
└── ip_address: GenericIPAddress
```

### DavAccount
```
DavAccount (TimeStampedModel)
├── FK -> user: User [OneToOne]
├── dav_username: Char(150) [unique]
├── password_hash: Char(255)
├── is_active: Boolean
└── password_rotated_at: DateTime
```

### DavExternalAccount
```
DavExternalAccount (TimeStampedModel)
├── FK -> owner: User
├── label: Char(120)
├── dav_username: Char(150) [unique]
├── password_hash: Char(255)
├── is_active: Boolean
└─��� password_rotated_at: DateTime
```

### DavTeam
```
DavTeam (OwnedModel, TimeStampedModel)
├── name: Char(120)
├── slug: Char(120)
├── is_active: Boolean
└── FK -> owner: User
```

### DavManagedCalendar
```
DavManagedCalendar (TimeStampedModel)
├── FK -> owner: User
├── principal: Char(150) [default: team]
├── calendar_slug: Char(120)
├── display_name: Char(120)
└── is_active: Boolean
```

### DavCalendarGrant
```
DavCalendarGrant (TimeStampedModel)
├── FK -> owner: User
├── FK -> external_account: DavExternalAccount
├── FK -> calendar: DavManagedCalendar
├── access_level: Char(2) [ro, rw]
└── is_active: Boolean
```

### UserHeroActionsConfig
```
UserHeroActionsConfig
├── FK -> user: User [OneToOne]
└── config: JSON
```

### UserNavConfig
```
UserNavConfig
├── FK -> user: User [OneToOne]
└── config: JSON
```

---

## agenda

### AgendaItem
```
AgendaItem (OwnedModel, TimeStampedModel)
├── title: Char(200)
├── item_type: Char(10) [ACTIVITY, REMINDER]
├── due_date: Date
├── due_time: Time [NULL]
├── FK -> project: Project [NULL]
├── status: Char(10) [PLANNED, DONE]
├── note: Text
└── FK -> owner: User
```

### WorkLog
```
WorkLog (OwnedModel, TimeStampedModel)
├── work_date: Date
├── time_start: Time [NULL]
├── time_end: Time [NULL]
├── lunch_break_minutes: PositiveSmallInteger
├── hours: Decimal(5,2)
├── note: Text
└── FK -> owner: User
[unique: (owner, work_date)]
```

---

## planner

### PlannerItem
```
PlannerItem (OwnedModel, TimeStampedModel)
├── title: Char(200)
├── due_date: Date [NULL]
├── amount: Decimal(12,2) [NULL]
├── FK -> category: Category [NULL]
├── FK -> project: Project [NULL]
├── note: Text
├── status: Char(10) [PLANNED, DONE, SKIPPED]
└── FK -> owner: User
```

---

## routines

### RoutineCategory
```
RoutineCategory (OwnedModel, TimeStampedModel)
├── name: Char(120)
├── is_active: Boolean
└── FK -> owner: User
```

### Routine
```
Routine (OwnedModel, TimeStampedModel)
├── FK -> category: RoutineCategory [NULL]
├── name: Char(160)
├── description: Text
├── is_active: Boolean
└── FK -> owner: User
```

### RoutineItem
```
RoutineItem (OwnedModel, TimeStampedModel)
├── FK -> routine: Routine [CASCADE]
├── FK -> category: RoutineCategory [NULL]
├── FK -> project: Project [NULL]
├── title: Char(200)
├── weekday: PositiveSmallInteger (0-6)
├── time_start: Time [NULL]
├── time_end: Time [NULL]
├── note: Text
├── is_active: Boolean
├── schema: JSON
└── FK -> owner: User
```

### RoutineCheck
```
RoutineCheck (OwnedModel, TimeStampedModel)
├── FK -> item: RoutineItem [CASCADE]
├── week_start: Date
├── status: Char(10) [PLANNED, DONE, SKIPPED]
├── data: JSON
└── FK -> owner: User
[unique: (owner, item, week_start)]
```

---

## todo

### Task
```
Task (OwnedModel, TimeStampedModel)
├── title: Char(160)
├── FK -> project: Project [NULL]
├── FK -> category: Category [NULL]
├── item_type: Char(12) [TASK, REMINDER, APPOINTMENT]
├── due_date: Date [NULL]
├── due_time: Time [NULL]
├── status: Char(12) [OPEN, IN_PROGRESS, DONE]
├── priority: Char(8) [LOW, MEDIUM, HIGH]
├── note: Text
└── FK -> owner: User
```

---

## vault

### VaultProfile
```
VaultProfile (OwnedModel, TimeStampedModel)
├── totp_secret_encrypted: Text
├── totp_enabled_at: DateTime [NULL]
├── failed_attempts: PositiveSmallInteger
├── locked_until: DateTime [NULL]
└── FK -> owner: User
[unique: owner]
```

### VaultItem
```
VaultItem (OwnedModel, TimeStampedModel)
├── title: Char(160)
├── kind: Char(10) [PASSWORD, NOTE]
├── login: Char(120)
├── website_url: URL
├── secret_encrypted: Text
├── notes_encrypted: Text
└── FK -> owner: User
```

---

## link_storage

### Link
```
Link (OwnedModel, TimeStampedModel)
├── url: Char(160)
├── category: Char(15) [TECNOLOGIA, SALUTE, SPORT, INTRATTENIMENTO]
├── importance: Integer
├── note: Text
└── FK -> owner: User
```

---

## memory_stock

### MemoryStockItem
```
MemoryStockItem (OwnedModel, TimeStampedModel)
├── title: Char(220)
├── source_url: URL
├── note: Text
├── source_sender: Email
├── source_subject: Char(255)
├── source_message_id: Char(255)
├── source_action: Char(64)
├── metadata: JSON
├── is_archived: Boolean
└── FK -> owner: User
```

---

## archibald

### ArchibaldThread
```
ArchibaldThread (OwnedModel, TimeStampedModel)
├── title: Char(120)
├── is_active: Boolean
├── kind: Char(12) [DIARY, TEMPORARY]
├── openai_conversation_id: Char(128)
├── openai_last_response_id: Char(128)
├── openai_model: Char(64)
└── FK -> owner: User
```

### ArchibaldMessage
```
ArchibaldMessage (OwnedModel, TimeStampedModel)
├── FK -> thread: ArchibaldThread [CASCADE]
├── role: Char(10) [SYSTEM, USER, ASSISTANT]
├── content: Text
├── is_favorite: Boolean
├── openai_response_id: Char(128)
└── FK -> owner: User
```

### ArchibaldPersonaConfig
```
ArchibaldPersonaConfig (OwnedModel, TimeStampedModel)
├── preset: Char(12) [OPERATIVE, BALANCED, CLASSIC, ELITE]
├── verbosity: Char(10) [SHORT, MEDIUM, LONG]
├── challenge_level: Char(10) [LOW, NORMAL, HIGH]
├── action_mode: Char(12) [WHEN_USEFUL, ALWAYS, NEVER]
├── avoid_pandering: Boolean
├── include_reasoning: Boolean
├── psych_validate_emotions: Boolean
├── psych_assertive_boundaries: Boolean
├── psych_socratic_questions: Boolean
├── psych_cognitive_reframe: Boolean
├── psych_bias_check: Boolean
├── psych_self_efficacy: Boolean
├── psych_micro_actions: Boolean
├── psych_accountability_nudge: Boolean
├── psych_decision_simplify: Boolean
├── psych_non_judgmental_tone: Boolean
├── bias_catastrophizing: Boolean
├── bias_all_or_nothing: Boolean
├── bias_overgeneralization: Boolean
├── bias_mind_reading: Boolean
├── bias_negative_filtering: Boolean
├── bias_confirmation_bias: Boolean
├── custom_instructions: Text
└── FK -> owner: User
[unique: owner]
```

### ArchibaldInstructionState
```
ArchibaldInstructionState (OwnedModel, TimeStampedModel)
├── name: Char(120)
├── instructions_text: Text
└── FK -> owner: User
[unique: (owner, name)]
```

---

## Key Relationships Diagram

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                         Transaction                                    │
│  (links Account, Currency, Project, Category, Payee, IncomeSource)   │
└────────────────────────────────────────────────────────────────────┬────────────────┘
                                                     │
     ┌──────────────┬──────────────┬──────────────┬──────┴──────────┐
     │             │             │             │                  │
  Account    Currency    Project    Category           Payee (core)
     │             │             │             │                  │
     │             │             │             │         IncomeSource
  Subscription     │             │             │                  │
     │             │             │             │                  │
  Subscription   Quote    Invoice   WorkOrder              Contact (contacts)
  Occurrence      │              │             │                  │
     │         Customer                        ContactDeliveryAddress
     │              │              │             │                  │
     │         ProjectNote                   ContactToolbox
     │              │              │             │
     │         SubProject ── SubProjectActivity
     │              │
     └────────── Todo ── PlannerItem ── RoutineItem
                      │              │
                 SubTask         RoutineCheck
```

---

## Related Documentation

- [[apps|Apps Overview]] - Full app descriptions
- [[views|Views & URLs]] - View implementations
- [[business-logic|Business Logic]] - Using these models