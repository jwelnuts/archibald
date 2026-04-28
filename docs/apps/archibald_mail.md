---
title: archibald_mail
tags: [app, archibald_mail]
aliases: [email, mail, imap, smtp, inbox]
---

# Archibald Mail App

> **Stato**: ATTIVO - Indipendente da archibald (rimosso)

Email integration with IMAP/SMTP, auto-replies, and AI-powered message handling.

## Models

| Model | Description | Key Fields |
|-------|-------------|------------|
| `ArchibaldMailboxConfig` | Mailbox settings | inbox_address, timezone, IMAP/SMTP config, notifications, auto-reply |
| `ArchibaldEmailFlagRule` | Email flag rules | label, flag_token, action_key, is_active |
| `ArchibaldInboundCategory` | Message categories | label, is_active, notes |
| `ArchibaldEmailMessage` | Email messages | config, direction, status, sender, recipient, subject, body, classification |

### Flag Rule Action Keys

- `memory_stock.save` - Save to Memory Stock
- `todo.capture` - Create Todo
- `transaction.capture` - Record Transaction
- `reminder.capture` - Create Reminder
- `archi.reply` - Immediate AI reply
- `worklog.capture_am` - Worklog morning
- `worklog.capture_pm` - Worklog afternoon

### Message Direction

- `INBOUND` - Inbound
- `OUTBOUND` - Outbound
- `NOTIFICATION` - Notification
- `TEST` - Test

### Message Status

- `RECEIVED` - Received
- `REPLIED` - Replied
- `SENT` - Sent
- `FAILED` - Failed
- `SKIPPED` - Skipped

### Review Status

- `PENDING` - Pending
- `APPLIED` - Applied
- `IGNORED` - Ignored

## URLs

| Route | Name | Description |
|-------|------|-------------|
| `/` | archibald-mail-dashboard | Mail dashboard |
| `/flags/` | archibald-mail-flag-rules | Flag rules list |
| `/flags/add` | archibald-mail-flag-add | Add flag rule |
| `/flags/<id>/edit` | archibald-mail-flag-edit | Edit flag rule |
| `/flags/<id>/remove` | archibald-mail-flag-remove | Remove flag rule |
| `/inbox/` | archibald-mail-inbox | Inbound message queue |
| `/inbox/<id>/apply` | archibald-mail-inbox-apply | Apply message action |
| `/inbox/<id>/ignore` | archibald-mail-inbox-ignore | Ignore message |
| `/inbox/<id>/reopen` | archibald-mail-inbox-reopen | Reopen message |

## Related Apps

- [[memory_stock]] - $MEMORY flag action
- [[todo]] - $TODO flag action
- [[transactions]] - $TRANSACTION flag action
- [[agenda]] - Worklog capture (WORKLOG_AM, WORKLOG_PM)
- [[archibald]] - AI reply generation