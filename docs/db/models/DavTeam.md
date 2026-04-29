---
title: DavTeam
tags: [db, model, core, dav]
---

# DavTeam
**App:** `core` · **Tabella:** `core_davteam`
**Base:** `OwnedModel`, `TimeStampedModel`

Gruppo/team per organizzare calendari DAV condivisi.

## Campi principali
| Campo | Tipo | Note |
|---|---|---|
| name | CharField(120) | |
| slug | CharField(120) | unique per owner |
| is_active | BooleanField | |
