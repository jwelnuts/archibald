---
title: DavAccount
tags: [db, model, core, dav]
---

# DavAccount
**App:** `core` · **Tabella:** `core_davaccount`
**Base:** `TimeStampedModel`

Account DAV (CalDAV/CardDAV) interno dell'utente. Uno per utente (1:1).

## Campi principali
| Campo | Tipo | Note |
|---|---|---|
| dav_username | CharField(150) | unique |
| password_hash | CharField(255) | |
| is_active | BooleanField | |
| password_rotated_at | DateTimeField | |

## Relazioni FK
| Campo | → Modello | on_delete |
|---|---|---|
| user | User (auth) | CASCADE (1:1) |
