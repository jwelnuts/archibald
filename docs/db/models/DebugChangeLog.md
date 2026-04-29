---
title: DebugChangeLog
tags: [db, model, workbench]
---

# DebugChangeLog
**App:** `workbench` · **Tabella:** `workbench_debugchangelog`
**Base:** `models.Model`

Storico cambiamenti registrati dal middleware debug (attivo solo in modalità debug).

## Campi principali
| Campo | Tipo | Note |
|---|---|---|
| created_at | DateTimeField | auto_now_add |
| source | CharField(120) | |
| action | CharField(10) | CREATE / UPDATE / DELETE / CUSTOM |
| app_label | CharField(80) | |
| model_name | CharField(80) | |
| object_id | CharField(64) | |
| before | JSONField | snapshot pre-modifica |
| after | JSONField | snapshot post-modifica |
| note | TextField | |

## Relazioni FK
| Campo | → Modello | on_delete |
|---|---|---|
| user | User (auth) | SET_NULL |
