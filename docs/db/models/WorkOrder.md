---
title: WorkOrder
tags: [db, model, finance, finance_hub]
---

# WorkOrder
**App:** `finance_hub` · **Tabella:** `finance_hub_workorder`
**Base:** `OwnedModel`, `TimeStampedModel`

Ordine di lavoro: ore/attività fatturabili associate a un progetto/cliente.

## Campi principali
| Campo | Tipo | Note |
|---|---|---|
| code | CharField(40) | unique non-vuoto per owner |
| title | CharField(180) | |
| status | CharField | OPEN / IN_PROGRESS / WAITING / DONE / CANCELED |
| start_date | DateField | |
| end_date | DateField | opzionale |
| estimated_amount | DecimalField(12,2) | |
| final_amount | DecimalField(12,2) | |
| is_billable | BooleanField | |

## Relazioni FK
| Campo | → Modello | on_delete |
|---|---|---|
| customer | [[Customer]] | SET_NULL |
| project | [[Project]] | SET_NULL |
| account | [[Account]] | SET_NULL |
| currency | [[Currency]] | PROTECT |
