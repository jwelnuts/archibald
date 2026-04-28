---
title: vault
tags: [app, vault]
aliases: [passwords, secrets, secure storage]
---

# Vault App

Encrypted password and secret storage with TOTP support.

## Models

| Model | Description | Key Fields |
|-------|-------------|------------|
| `VaultProfile` | User vault profile | totp_secret_encrypted, totp_enabled_at, failed_attempts, locked_until |
| `VaultItem` | Stored items | title, kind, login, website_url, secret_encrypted, notes_encrypted |

### VaultItem Kind

- `PASSWORD` - Password
- `NOTE` - Nota privata

## Security Features

- AES encryption for secrets and notes
- TOTP (Time-based One-Time Password) support
- Account lockout after failed attempts
- Masked secret display

## URLs

| Route | Name | Description |
|-------|------|-------------|
| `/` | vault-dashboard | Vault dashboard |
| `/setup` | vault-setup | TOTP setup |
| `/unlock` | vault-unlock | Unlock vault |
| `/lock` | vault-lock | Lock vault |
| `/reset` | vault-reset | Reset TOTP |
| `/api/add` | vault-add | Add item |
| `/api/update` | vault-update | Update item |
| `/api/remove` | vault-remove | Remove item |

## Related Apps

- [[core]] - User authentication