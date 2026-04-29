---
title: MobileApiSession
tags: [db, model, core]
---

# MobileApiSession
**App:** `core` · **Tabella:** `core_mobileapisession`
**Base:** `TimeStampedModel`

Sessione API mobile per autenticazione token-based (access + refresh token).

## Campi principali
| Campo | Tipo | Note |
|---|---|---|
| access_token_hash | CharField(64) | unique |
| refresh_token_hash | CharField(64) | unique |
| access_expires_at | DateTimeField | |
| refresh_expires_at | DateTimeField | |
| revoked_at | DateTimeField | null se attiva |
| last_used_at | DateTimeField | |
| device_label | CharField(120) | |
| user_agent | CharField(255) | |
| ip_address | GenericIPAddressField | |

## Relazioni FK
| Campo | → Modello | on_delete |
|---|---|---|
| user | User (auth) | CASCADE |
