---
title: DavCalendarGrant
tags: [db, model, core, dav]
---

# DavCalendarGrant
**App:** `core` · **Tabella:** `core_davcalendargrant`
**Base:** `TimeStampedModel`

Permesso di accesso (ro/rw) di un account esterno su un calendario gestito.

## Campi principali
| Campo | Tipo | Note |
|---|---|---|
| access_level | CharField(2) | `ro` / `rw` |
| is_active | BooleanField | |

## Relazioni FK
| Campo | → Modello | on_delete |
|---|---|---|
| owner | User (auth) | CASCADE |
| external_account | [[DavExternalAccount]] | CASCADE |
| calendar | [[DavManagedCalendar]] | CASCADE |
