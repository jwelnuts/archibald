---
title: Dipendenze tra app
tags: [architecture, dependencies, graph, moc]
aliases: [deps, app-dependencies, architecture-layers]
---

# 🔗 Dipendenze tra app

Mappa autoritativa delle dipendenze del progetto, derivata dai modelli (`ForeignKey`/`ManyToMany`) e dagli import Python cross-app. Aggiornata: 2026-04-27.

## TL;DR — architettura a 6 livelli

```mermaid
graph TD
  subgraph L0["🧱 L0 · Foundation"]
    COMMON[common<br/><i>OwnedModel, TimeStampedModel</i>]
  end

  subgraph L1["🔐 L1 · Identity & Auth"]
    CORE[core<br/><i>auth, Payee, DAV, calendar agg.</i>]
  end

  subgraph L2["🎯 L2 · Domain Hubs"]
    FH[finance_hub<br/><i>Account, Currency, Quote</i>]
    PR[projects<br/><i>Project, Customer, Category</i>]
    CT[contacts<br/><i>Contact, Toolbox</i>]
  end

  subgraph L3["⚙️ L3 · Operational"]
    TX[transactions]
    SUBS[subscriptions]
    PL[planner]
    TD[todo]
    RT[routines]
    AG[agenda]
  end

  subgraph L4["🤖 L4 · Orchestrators"]
    AM[archibald_mail]
  end

  subgraph LISO["🏝️ Isolated leaves"]
    VL[vault]
    MS[memory_stock]
    LS[link_storage]
  end

  subgraph LDEV["🛠️ Dev tools"]
    WB[workbench]
  end

  COMMON --> CORE
  COMMON --> FH
  COMMON --> PR
  COMMON --> CT
  COMMON --> TX
  COMMON --> PL
  COMMON --> TD
  COMMON --> RT
  COMMON --> AG
  COMMON --> AM
  COMMON --> VL
  COMMON --> MS
  COMMON --> LS

  CORE --> WB

  CT --> FH
  CT --> PR
  CORE --> CT
  CORE --> FH
  CORE --> PR

  FH --> TX
  FH --> SUBS
  PR --> TX
  PR --> SUBS
  PR --> PL
  PR --> TD
  PR --> RT
  CORE --> TX
  CORE --> SUBS

  PR -.optional.-> AG
  PL -.import.-> AG
  TD -.import.-> AG
  RT -.import.-> AG

  TX --> AM
  TD --> AM
  PL --> AM
  RT --> AM
  AG --> AM
  MS --> AM
  FH --> AM

  classDef foundation fill:#ddd,stroke:#666
  classDef hub fill:#fde,stroke:#c39
  classDef ops fill:#def,stroke:#39c
  classDef orch fill:#efd,stroke:#3c9
  classDef iso fill:#ffd,stroke:#cc6
  classDef dev fill:#fed,stroke:#c63
  class COMMON foundation
  class CORE,FH,PR,CT hub
  class TX,SUBS,PL,TD,RT,AG ops
  class AM orch
  class VL,MS,LS iso
  class WB dev
```

> **Regola**: ogni livello può dipendere solo dai livelli inferiori (no upward imports). Eccezione documentata: `core` aggrega eventi calendario da L3 via lazy import.

## Dipendenze dati (ForeignKey/M2M)

Solo riferimenti **dichiarati nei modelli** (DB-level).

```mermaid
graph LR
  COMMON[common]:::base
  CORE[core.Payee]:::hub
  CTC[contacts.Contact]:::hub
  FHA[finance_hub.Account]:::hub
  FHC[finance_hub.Currency]:::hub
  FHT[finance_hub.Tag]:::hub
  FHQ[finance_hub.Quote]:::hub
  FHS[finance_hub.Subscription]:::hub
  PRP[projects.Project]:::hub
  PRC[projects.Category]:::hub
  TX[transactions.Transaction]:::ops

  TX -->|account| FHA
  TX -->|currency| FHC
  TX -->|project| PRP
  TX -->|category| PRC
  TX -->|payee| CORE
  TX -->|tags M2M| FHT
  TX -->|source_subscription| FHS
  TX -->|income_source| FHQ

  FHQ -->|customer| CTC
  FHQ -->|project| PRP
  FHQ -->|currency| FHC
  FHS -->|account| FHA
  FHS -->|payee| CORE
  FHS -->|category| PRC
  FHS -->|project| PRP
  FHS -->|tags M2M| FHT

  PRP -->|customer| CTC
  PRP -->|category| PRC

  COMMON -.-> MS
  MS -.optional FK.-> LS
  
  classDef base fill:#eee
  classDef hub fill:#fde
  classDef ops fill:#def
  classDef memory fill:#e6ffe6,stroke:#2d5a2d
```

### Riepilogo FK per app

| App | Dipende da (FK) | Note |
|-----|-----------------|------|
| **common** | — | foundation |
| **core** | django.User | OneToOne con user; nessuna FK app-level |
| **contacts** | self only | grafo interno (Contact ↔ Toolbox ↔ PriceList) |
| **finance_hub** | core.Payee, projects.{Project,Category}, contacts.Contact | hub centrale |
| **projects** | contacts.Contact, finance_hub | tramite import; FK a self (subproject) |
| **transactions** | finance_hub.{Account,Currency,Tag,Subscription,Quote}, projects.{Project,Category}, core.Payee | ledger collega tutto |
| **subscriptions** | (alias di finance_hub.Subscription) | stub legacy |
| **planner** | projects.{Project,Category} | + auto-crea ProjectNote |
| **todo** | projects.{Project,Category} | trasferimento ↔ planner |
| **routines** | projects.{Project,Category} | self-FK (Routine→Item→Check) |
| **agenda** | projects.Project | aggregatore eventi |
| **archibald_mail** | self only | FK interne (Config, Message, Category) |
| **memory_stock** | — | hub memoria (base per Link, Note, ecc.) |
| **vault** | — | isolato |
| **link_storage** | memory_stock.MemoryStockItem | specializzazione Link (opzionale FK OneToOne) |
| **workbench** | django.User | log debug per user |

## Dipendenze codice (import cross-app)

Le dipendenze a runtime spesso superano gli FK (services, signals, viste aggregate):

| App | Importa da |
|-----|------------|
| **common** | — |
| **vault** | common |
| **memory_stock** | common |
| **link_storage** | common |
| **workbench** | common, core |
| **planner** | common, projects |
| **todo** | common, core, projects |
| **routines** | common, projects |
| **contacts** | common, core, finance_hub, projects |
| **finance_hub** | common, contacts, core, projects |
| **transactions** | common, contacts, core, finance_hub, projects |
| **agenda** | common, core, planner, projects, routines, todo |
| **subscriptions** | core, finance_hub, projects, transactions |
| **income** | contacts, finance_hub, projects, transactions *(stub)* |
| **outcome** | finance_hub *(stub)* |
| **projects** | common, contacts, core, finance_hub, planner, routines, todo, transactions |
| **core** | + agenda, archibald, contacts, finance_hub, planner, projects, routines, todo, transactions |
| **archibald_mail** | agenda, archibald, common, finance_hub, memory_stock, planner, routines, todo |

> ⚠️ **Cicli osservati**:
> - `projects ↔ contacts` (FK customer ↔ import services)
> - `projects ↔ finance_hub` (FK + import bidirezionale)
> - `core` importa da L3 per il calendario aggregato → mitigato con **lazy imports** dentro view/services
> 
> Questi cicli sono accettati come *trade-off* perché rappresentano hub operativi. Vanno tenuti d'occhio: nuove FK upward sono da evitare.

## Mappa per dominio funzionale

```mermaid
graph TB
  subgraph Finance["💰 Finance"]
    FHfin[finance_hub]
    TXfin[transactions]
    SUBSfin[subscriptions]
  end

  subgraph Work["🛠️ Work"]
    PRwork[projects]
    CTwork[contacts]
  end

  subgraph Plan["📅 Personal Planning"]
    AGplan[agenda]
    PLplan[planner]
    RTplan[routines]
    TDplan[todo]
  end

  subgraph Know["🧠 Knowledge"]
    MSknow[memory_stock]
    LSknow[link_storage]
    AMknow[archibald_mail]
  end

  subgraph Sec["🔐 Security"]
    VLsec[vault]
  end

  subgraph Sys["⚙️ System"]
    COREsys[core]
    WBsys[workbench]
  end

  Finance ==> Work
  Work ==> Plan
  Plan -.events.-> Sys
  Know -.read.-> Finance
  Know -.read.-> Plan
  Sys --> Finance
  Sys --> Work
```

## Cosa significa, operativamente

- **Per modificare `common`** → impatto totale (tutti gli OwnedModel). Test full suite.
- **Per modificare `core.Payee`** → tocchi finance_hub.Subscription, transactions.Transaction.
- **Per modificare `finance_hub.Account/Currency`** → tocchi transactions e subscriptions.
- **Per modificare `projects.Project`** → tocchi transactions, finance_hub, planner, todo, routines, agenda.
- **Per aggiungere nuova app L3** → dipende da L2 (hub) o L1 (core), mai upward.
- **Le isolate** (vault) → modifiche locali, zero blast radius.
- **Memory hub** (memory_stock) → hub per la conoscenza, link_storage è una specializzazione (FK opzionale).
- **Aggiungere nuovo tipo a memory_stock** → creare modello con FK a MemoryStockItem, come Link.

## Vedi anche

- [[project-identity]] - Visione e principi
- [[moc-apps]] - Map of Content delle app
- [[models]] - ERD completo dei modelli
- [[business-logic]] - Workflow di business
