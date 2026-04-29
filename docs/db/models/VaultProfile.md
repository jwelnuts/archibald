---
title: VaultProfile
tags: [db, model, security, vault]
---

# VaultProfile
**App:** `vault` · **Tabella:** `vault_vaultprofile`
**Base:** `OwnedModel`, `TimeStampedModel`

Profilo TOTP del vault: uno per utente. Gestisce setup, lock e tentativi falliti.

## Campi principali
| Campo | Tipo | Note |
|---|---|---|
| totp_secret_encrypted | TextField | segreto TOTP cifrato con Fernet |
| totp_enabled_at | DateTimeField | null finché non attivato |
| failed_attempts | PositiveSmallIntegerField | reset dopo lock |
| locked_until | DateTimeField | lock temporaneo dopo 5 fail |

## Note
- unique su `owner` (un solo profilo per utente)
- Il segreto TOTP è sempre cifrato a riposo
