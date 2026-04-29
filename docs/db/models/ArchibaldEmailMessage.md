---
title: ArchibaldEmailMessage
tags: [db, model, knowledge, archibald_mail]
---

# ArchibaldEmailMessage
**App:** `archibald_mail` · **Tabella:** `archibald_mail_archivaldemailmessage`
**Base:** `OwnedModel`, `TimeStampedModel`

Log di ogni email processata (inbound, outbound, notifica). Hub centrale del flusso di cattura.

## Campi principali
| Campo | Tipo | Note |
|---|---|---|
| direction | CharField | INBOUND / OUTBOUND / NOTIFICATION / TEST |
| status | CharField | RECEIVED / REPLIED / SENT / FAILED / SKIPPED |
| message_id | CharField(255) | ID IMAP |
| sender / recipient | EmailField | |
| subject | CharField(255) | |
| body_text | TextField | testo email |
| selected_action_key | CharField(64) | flag riconosciuto |
| review_status | CharField | PENDING / APPLIED / IGNORED |
| processed_at | DateTimeField | |

## Relazioni FK
| Campo | → Modello | on_delete |
|---|---|---|
| config | [[ArchibaldMailboxConfig]] | CASCADE |
| related_message | [[ArchibaldEmailMessage]] (self) | SET_NULL |
| classification_category | [[ArchibaldInboundCategory]] | SET_NULL |

## Flusso
Email ricevuta → flag riconosciuto via [[ArchibaldEmailFlagRule]] → azione eseguita → record salvato in [[MemoryStockItem]] / [[Task]] / [[WorkLog]]
