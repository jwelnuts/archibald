---
title: WorkbenchItem
tags: [db, model, workbench]
---

# WorkbenchItem
**App:** `workbench` · **Tabella:** `workbench_workbenchitem`
**Base:** `OwnedModel`, `TimeStampedModel`

Task/item del workbench interno (import, report, debug).

## Campi principali
| Campo | Tipo | Note |
|---|---|---|
| title | CharField(160) | |
| kind | CharField(10) | IMPORT / REPORT / DEBUG |
| status | CharField(12) | OPEN / IN_PROGRESS / DONE |
| note | TextField | |
