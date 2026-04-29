---
title: Transaction
tags: [db, model, finance, transactions]
---

# Transaction
**App:** `transactions` · **Tabella:** `transactions_transaction`
**Base:** `OwnedModel`, `TimeStampedModel`

Movimento finanziario: entrata (IN), uscita (OUT) o trasferimento (XFER).

## Campi principali
| Campo | Tipo | Note |
|---|---|---|
| tx_type | CharField | IN / OUT / XFER |
| date | DateField | default oggi |
| amount | DecimalField(12,2) | |
| note | TextField | |
| attachment | FileField | opzionale |

## Relazioni FK
| Campo | → Modello | on_delete |
|---|---|---|
| currency | [[Currency]] | PROTECT |
| account | [[Account]] | PROTECT |
| project | [[Project]] | SET_NULL |
| category | [[Category]] | SET_NULL |
| payee | [[Payee]] | SET_NULL |
| income_source | [[IncomeSource]] | SET_NULL |
| source_subscription | [[Subscription]] | SET_NULL |

## Relazioni M2M
| Campo | → Modello |
|---|---|
| tags | [[Tag]] |

## Relazioni inverse
- `subscription_occurrence` ← [[SubscriptionOccurrence]] (1:1)

## Note
- `source_subscription` è popolato quando la transazione viene generata da una [[SubscriptionOccurrence]]
- `income_source` usato solo per tx_type=IN
