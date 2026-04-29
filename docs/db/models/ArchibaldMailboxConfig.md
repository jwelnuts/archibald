---
title: ArchibaldMailboxConfig
tags: [db, model, knowledge, archibald_mail]
---

# ArchibaldMailboxConfig
**App:** `archibald_mail` · **Tabella:** `archibald_mail_archibaldmailboxconfig`
**Base:** `OwnedModel`, `TimeStampedModel`

Configurazione IMAP/SMTP e notifiche per la casella email di cattura. Uno per utente.

## Campi principali
| Campo | Tipo | Note |
|---|---|---|
| inbox_address | EmailField | indirizzo monitorato |
| is_enabled | BooleanField | attiva il polling |
| imap_host / port / ssl | vari | config IMAP |
| smtp_host / port / tls | vari | config SMTP per risposte |
| notifications_enabled | BooleanField | digest giornaliero |
| notification_hour / minute | Integer | orario invio |
| latest_poll_at | DateTimeField | ultimo polling |
| latest_poll_status | CharField(32) | ok / error |

## Relazioni inverse
- `messages` ← [[ArchibaldEmailMessage]]
