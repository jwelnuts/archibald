---
title: VaultItem
tags: [db, model, security, vault]
---

# VaultItem
**App:** `vault` · **Tabella:** `vault_vaultitem`
**Base:** `OwnedModel`, `TimeStampedModel`

Password o nota privata cifrata con Fernet.

## Campi principali
| Campo | Tipo | Note |
|---|---|---|
| title | CharField(160) | |
| kind | CharField | PASSWORD / NOTE |
| login | CharField(120) | username/email opzionale |
| website_url | URLField | opzionale |
| secret_encrypted | TextField | valore cifrato |
| notes_encrypted | TextField | note cifrate |

## Note
- `secret_encrypted` e `notes_encrypted` sono cifrati con la stessa chiave Fernet del progetto
- Accesso protetto da TOTP via [[VaultProfile]]
