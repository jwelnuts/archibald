---
title: MemoryStockItem
tags: [db, model, knowledge, memory_stock]
---

# MemoryStockItem
**App:** `memory_stock` · **Tabella:** `memory_stock_memorystockitem`
**Base:** `OwnedModel`, `TimeStampedModel`

Appunto/cattura salvato manualmente o via email flag (senza dimenticazione).

## Campi principali
| Campo | Tipo | Note |
|---|---|---|
| title | CharField(220) | |
| source_url | URLField | opzionale |
| note | TextField | |
| source_sender | EmailField | mittente email originale |
| source_subject | CharField(255) | oggetto email originale |
| source_message_id | CharField(255) | ID messaggio email |
| source_action | CharField(64) | flag usato (es. memory_stock.save) |
| metadata | JSONField | dati extra |
| is_archived | BooleanField | |

## Note
- Quando `source_action` è valorizzato, l'item è stato creato da [[ArchibaldEmailMessage]] via flag email
