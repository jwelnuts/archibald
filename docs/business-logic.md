---
title: Business Logic
tags: [business, workflow, process]
aliases: [processes, workflows]
---

# Business Logic

This document describes key business workflows and processes in MIO Master.

---

## Quote to Invoice Workflow

### Overview
```
Quote (Draft) → Quote (Sent) → Customer Approval → Invoice → Payment
                         → Quote (Rejected)
```

### Step-by-Step

1. **Create Quote**
   - Add quote with lines (QuoteLine)
   - Select customer, project, currency
   - Add VAT code, payment/shipping methods
   - Set status: DRAFT

2. **Send Quote**
   - Change status to SENT
   - Optionally set valid_until date

3. **Share Quote (Optional)**
   - Generate public access token
   - Share link via email to customer
   - Customer can view and confirm/reject online

4. **Customer Confirmation**
   - Customer visits public link
   - Fills confirmation form (signer name, decision)
   - Status changes to APPROVED or REJECTED

5. **Create Invoice**
   - Link from approved quote
   - Invoice inherits customer, amounts, currency
   - Set due_date for payment

6. **Payment Tracking**
   - Mark invoice as PAID
   - Track paid_date

---

## Subscription Payment Workflow

### Overview
```
Subscription (Active) → Occurrence Created → Payment → Transaction Created
                                     → Next Due Date Updated
```

### Step-by-Step

1. **Create Subscription**
   - Name, amount, currency
   - Interval (day/week/month/year)
   - Link to account, category, project, payee

2. **Automatic Occurrence Generation**
   - SubscriptionOccurrence records created
   - Due dates calculated based on interval

3. **Payment**
   - Select account to pay from
   - Creates Transaction (type: OUT)
   - Links to subscription via source_subscription

4. **Next Due Date**
   - Automatically calculated from interval
   - Updates subscription.next_due_date

---

## Transaction Recording

### Types

- **IN (Income)**: Money received
  - Links: Account, IncomeSource, Payee
- **OUT (Expense)**: Money spent
  - Links: Account, Payee
- **XFER (Transfer)**: Between accounts
  - Links: two Accounts (implied)

### Recording Flow
1. Select type (IN/OUT/XFER)
2. Enter amount, date
3. Select account
4. Optionally link: project, category, payee, income_source
5. Add note (optional)
6. Attach file (optional)

---

## Projects Storyboard

### Features
- Unified timeline of all project activities
- Quick note creation with attachments
- Quick task creation
- Quick planner item creation
- Filter by kind (note/task/planner/transaction)
- Date range filtering

### Quick Actions from Storyboard
- Add note with attachment
- Create task (goes to todo)
- Create planner item (goes to planner)
- View transaction history

---

## Routine Weekly Check

### Flow
1. View week (current or selected)
2. See items by weekday
3. Mark as: DONE / SKIPPED / Planned
4. Auto-skip past days

### Statistics
- Total items this week
- Completion rate
- Skip rate

---

## Task to Planner Transfer

### Task → Planner
- Can transfer task to planner
- Creates PlannerItem with due date
- Task remains in todo (can close)

### Planner → Task
- Can transfer planner item to todo
- Creates Task with due date
- Item marked as DONE

---

## Vault Security

### Setup Flow
1. Generate/enter TOTP secret
2. Scan QR code with authenticator app
3. Confirm with initial PIN
4. Vault unlocked for session

### Session Flow
1. Enter TOTP code
2. Session timeout (default 10 min)
3. Lock after inactivity

### Item Management
- Add password/note
- Fields encrypted with Fernet
- Retrieve decrypted values

---

## AI Assistant (Archibald)

### Chat Flow
1. Create or select thread
2. Send message
3. Build context (relations, cognitive)
4. Send to OpenAI
5. Save response
6. Display

### Context Building
- Relational context: projects, contacts, recent activity
- Cognitive context: emotional state, priorities
- Optional: Socratic questions, bias detection

### Message Features
- Favorite toggle
- Insight cards generation
- Temporary threads for quick questions

---

## Email AI Processing

### Inbound Processing
1. Poll inbox (IMAP)
2. Parse subject for flags
3. Route to handler
4. Process action

### Flags

| Flag | Action |
|------|--------|
| `[MEMORY]` / `#MEMORY` | Save to memory_stock |
| `[TODO]` / `#TODO` | Create todo task |
| `[TRANSACTION]` / `#TX` | Create transaction |
| `[REMINDER]` / `#REMINDER` | Create agenda item |
| `[ARCHI]` | AI reply |
| `[WORKLOG_AM]` | Log morning hours |
| `[WORKLOG_PM]` | Log afternoon hours |

### Notification Flow
1. Daily check (configurable time)
2. Gather pending items
3. Format summary
4. Send email

---

## Contact-Project Sync

### Features
- Auto-create Customer when adding to Project
- Auto-create Contact from Customer (bidirectional)
- Sync delivery addresses
- Price lists per contact

### Sync Trigger
- Adding customer to quote/invoice
- Adding customer to work order
- Contact toolbox updates

---

## CalDAV Integration

### Features
- Calendar sync (subscriptions, agenda)
- Task sync (todo) via VTODO
- Contact sync (contacts)
- External sharing via DavCalendarGrant

### Flow
1. User enables CalDAV
2. Create DavAccount
3. Manage calendars
4. Grant external access

---

## Related Documentation

- [[apps|Apps Overview]]
- [[models|Database Models]]
- [[views|Views & URLs]]
- [[deployment|Deployment]]