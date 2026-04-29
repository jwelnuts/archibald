---
title: DavExternalAccount
tags: [db, model, core, dav]
---

# DavExternalAccount
**App:** `core` · **Tabella:** `core_davexternalaccount`
**Base:** `TimeStampedModel`

Account DAV esterno (es. client di terze parti) con accesso limitato tramite grant.

## Campi principali
| Campo | Tipo | Note |
|---|---|---|
| label | CharField(120) | |
| dav_username | CharField(150) | unique |
| password_hash | CharField(255) | |
| is_active | BooleanField | |
| password_rotated_at | DateTimeField | |

## Relazioni FK
| Campo | → Modello | on_delete |
|---|---|---|
| owner | User (auth) | CASCADE |

## Relazioni inverse
- `grants` ← [[DavCalendarGrant]]
