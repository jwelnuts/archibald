---
title: memory_stock
tags: [app, memory_stock]
aliases: [knowledge, notes, captured info]
---

# Memory Stock App

Knowledge capture and storage system for links, emails, and other information.

## Models

| Model | Description | Key Fields |
|-------|-------------|------------|
| `MemoryStockItem` | Captured items | title, source_url, note, source_sender, source_subject, source_message_id, source_action, metadata, is_archived |

## Relationships

- Tracks source message_id for email integration
- Optional source URL for web captures
- JSON metadata for flexible data storage

## URLs

| Route | Name | Description |
|-------|------|-------------|
| `/` | memory-stock-dashboard | Memory stock dashboard |
| `/api/add` | memory-stock-add | Add item |
| `/api/update` | memory-stock-update | Update item |
| `/api/remove` | memory-stock-remove | Remove item |
| `/api/archive` | memory-stock-archive | Toggle archive status |

## Related Apps

- [[archibald_mail]] - Email integration
- [[link_storage]] - Similar bookmark-style app