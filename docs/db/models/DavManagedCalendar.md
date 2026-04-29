---
title: DavManagedCalendar
tags: [db, model, core, dav]
---

# DavManagedCalendar
**App:** `core` · **Tabella:** `core_davmanagedcalendar`
**Base:** `TimeStampedModel`

Calendario DAV gestito dall'applicazione (CalDAV collection).

## Campi principali
| Campo | Tipo | Note |
|---|---|---|
| principal | CharField(150) | default "team" |
| calendar_slug | CharField(120) | |
| display_name | CharField(120) | |
| is_active | BooleanField | |

`collection_path` → `{principal}/{calendar_slug}`

## Relazioni FK
| Campo | → Modello | on_delete |
|---|---|---|
| owner | User (auth) | CASCADE |

## Relazioni inverse
- `grants` ← [[DavCalendarGrant]]
