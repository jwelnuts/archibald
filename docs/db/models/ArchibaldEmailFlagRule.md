---
title: ArchibaldEmailFlagRule
tags: [db, model, knowledge, archibald_mail]
---

# ArchibaldEmailFlagRule
**App:** `archibald_mail` · **Tabella:** `archibald_mail_archivaldemailflagrule`
**Base:** `OwnedModel`, `TimeStampedModel`

Regola che mappa un flag email (es. `MEMORY`) a un'azione (es. `memory_stock.save`).

## Campi principali
| Campo | Tipo | Note |
|---|---|---|
| label | CharField(60) | nome leggibile |
| flag_token | CharField(32) | es. MEMORY, TODO — unique per owner |
| action_key | CharField(64) | es. memory_stock.save |
| is_active | BooleanField | |
| notes | TextField | |

## Azioni disponibili
| action_key | Effetto |
|---|---|
| memory_stock.save | Salva in [[MemoryStockItem]] |
| todo.capture | Crea [[Task]] (fallback MemoryStock) |
| transaction.capture | Crea [[Transaction]] (fallback MemoryStock) |
| reminder.capture | Reminder (fallback MemoryStock) |
| archi.reply | Salva in [[MemoryStockItem]] |
| worklog.capture_am | Aggiorna [[WorkLog]] mattina |
| worklog.capture_pm | Aggiorna [[WorkLog]] pomeriggio |
