---
title: link_storage
tags: [app, link_storage]
aliases: [bookmarks, urls, saved links]
---

# Link Storage App

Bookmark and link management with categorization.

## Models

| Model | Description | Key Fields |
|-------|-------------|------------|
| `Link` | Saved links | url, category, importance, note |

### Categories

- `TECNOLOGIA` - Technology
- `SALUTE` - Health
- `SPORT` - Sports
- `INTRATTENIMENTO` - Entertainment

## URLs

| Route | Name | Description |
|-------|------|-------------|
| `/` | link_storage-dashboard | Links dashboard |
| `/api/add` | link_storage-add | Add link |
| `/api/update` | link_storage-update | Update link |
| `/api/remove` | link_storage-remove | Remove link |

## Related Apps

- [[memory_stock]] - Similar bookmark-style app