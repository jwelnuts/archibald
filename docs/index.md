---
title: Index
tags: [root, index, documentation]
aliases: [main, home, README]
---

# MIO Master Documentation

Welcome to the MIO Master application documentation. This is an Obsidian-ready knowledge base for the Django application.

> 💡 Per una vista completa delle app e relazioni, vedere **Graph View** (Ctrl+G) e il [[moc-apps|MOC Apps]].

## Navigation

### Main Docs
- [[project-identity|🎯 Project Identity]] - Visione, principi, architettura a 6 livelli
- [[dependencies|🔗 Dipendenze tra app]] - FK + import + cicli noti
- [[models|Database Models]] - Models and relationships (ERD)
- [[views|Views & URLs]] - Views and URL patterns by app
- [[api|API Endpoints]] - All API endpoints
- [[business-logic|Business Logic]] - Business workflows and processes
- [[deployment|Deployment]] - Docker and VPS deployment
- [[moc-apps|MOC Apps]] - Map of Content con graph

### Apps (18 totali)

| Status | Apps |
|--------|------|
| **✅ Attive** | finance_hub, transactions, projects, core, contacts, agenda, planner, routines, todo, memory_stock, vault, workbench |
| **⚠️ Stub** | subscriptions (→FH), income (→FH), outcome, link_storage |
| **📧 Email** | archibald_mail |
| **❌ Rimosso** | archibald (27 Apr 2026) |

### Apps Links
- [[apps/finance_hub]] - Finance Hub
- [[apps/subscriptions]] - Subscriptions
- [[apps/transactions]] - Transactions
- [[apps/projects]] - Projects
- [[apps/core]] - Core (auth, users, DAV)
- [[apps/contacts]] - Contacts
- [[apps/agenda]] - Agenda
- [[apps/planner]] - Planner
- [[apps/routines]] - Routines
- [[apps/todo]] - Todo
- [[apps/income]] - Income
- [[apps/outcome]] - Outcome
- [[apps/link_storage]] - Link Storage
- [[apps/memory_stock]] - Memory Stock
- [[apps/vault]] - Vault
- [[apps/archibald_mail]] - Archibald Mail
- [[apps/workbench]] - Workbench
- ~~[[apps/archibald]]~~ - Archibald (**rimosso**)

## Quick Links

- [GitHub Repository](https://github.com/anomalyco/mio_master)
- [README](../README.md) - Full application README

## Related Documentation

- [[caldav-unification|CalDAV Integration]] - Calendar/CardDAV unification docs
- [[archibald-removal-analysis|Archibald Removal]] - Analisi e reason per rimozione AI assistant
- [[moc-apps|MOC Apps]] - Map of Content con visualizzazione relazioni

## Application Overview

**MIO Master** is a personal organization Django application comprising:
- Finance management (quotes, invoices, subscriptions, transactions)
- Project management with storyboard
- Personal planning (todo, planner, routines, agenda)
- ~~AI assistant (Archibald)~~ - *rimosso 27 Apr 2026*
- Encrypted vault for credentials
- Email AI processing (Archibald Mail)
- Technical workbench (superuser tools)

## Graph View Relationships

```
                    ┌──────────────────┐
                    │   finance_hub    │
                    │   (Core Finance) │
                    └───────┬──────────┘
                            │
          ┌─────────┬────────┼────────┼────────┬────────┐
          │         │        │        │        │        │
    ┌─────▼───┐ ┌────▼────┐ ┌───▼────┐ ┌────▼────┐ ┌───▼────┐
    │transactions│ │projects│ │contacts│ │agenda  │ │planner │
    └─────────┘ └────────┘ └────────┘ └────────┘ └────────┘
                         │
                ┌────────┼────────┐
                │        │        │
           ┌────▼───┐ ┌──▼────┐ ┌─▼──���─┐
           │todo    │ │routines│ │workbench│
           └────────┘ └───────┘ └──────┘

    ┌────────────────┐
    │ archibald_mail  │ ──→ memory_stock ──→ todo
    │  (Email AI)     │
    └────────────────┘
```

---
*Last updated: April 2026*