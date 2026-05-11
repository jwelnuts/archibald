---
title: Archibald - Analisi per Rimozione
tags: [analysis, archibald, removal, migration]
aliases: [archibald-analysis, remove-archibald]
---

# Archibald - Analisi Completa per Rimozione

> **Stato**: ✅ COMPLETATO - 27 Aprile 2026

## Sommario

Questo documento analizza l'app **archibald** per la rimozione dal progetto MIO Master. L'utente vuole mantenere solo la funzionalità di salvataggio degli appunti via email (già presente in **archibald_mail**).

---

## Componenti di Archibald

### 1. App `archibald` (da rimuovere)

**File principali:**
```
archibald/
├── models.py          # 188 linee - DB models
├── views.py          # 476 linee - Views HTTP
├── urls.py           # 13 linee - URL patterns
├── forms.py          # 14 linee - Forms
├── prompting.py      # 334 linee - System prompts & persona
├── services.py       # 475 linee - Data context builders
├── openai_client.py  # 250 linee - OpenAI API client
└── templates/
    ├── dashboard.html
    ├── base.html
    └── partials/insight_cards.html
```

### 2. App `archibald_mail` (da MANTENERE)

**Contiene la funzionalità email:**
- IMAP/SMTP polling
- Flag rules per azioni automatiche
- Inclusa `$MEMORY` flag per salvataggio in memory_stock

---

## Modelli Database

### ArchibaldThread
```
- title: Char(120)
- is_active: Boolean
- kind: DIARY | TEMPORARY
- openai_conversation_id: Char(128)
- openai_last_response_id: Char(128)
- openai_model: Char(64)
```

### ArchibaldMessage
```
- thread: FK -> ArchibaldThread
- role: SYSTEM | USER | ASSISTANT
- content: Text
- is_favorite: Boolean
- openai_response_id: Char(128)
```

### ArchibaldPersonaConfig (complessa)
- 20+ campi per configurazione psicologica
- Preset: OPERATIVE, BALANCED, CLASSIC, ELITE
- Feature: bias detection, cognitive reframe, socratic questions, ecc.

### ArchibaldInstructionState
```
- name: Char(120)
- instructions_text: Text
```

---

## Dipendenze Esterne

### OpenAI API
- **Provider**: OpenAI Responses API
- **Model**: GPT-5mini (configurabile via `OPENAI_MODEL_ARCHIBALD`)
- **Features**: reasoning effort, conversation history
- **Env vars**:
  - `OPENAI_API_KEY`
  - `OPENAI_MODEL`
  - `OPENAI_MODEL_ARCHIBALD`
  - `ARCHIBALD_REASONING_EFFORT`
  - `ARCHIBALD_USE_CONVERSATIONS`

### Integrazioni interne (usate in services.py)
```python
from core.models import Payee
from finance_hub.models import IncomeSource, Account, Subscription, SubscriptionOccurrence, Tag
from planner.models import PlannerItem
from projects.models import Category, Customer, Project, ProjectNote
from todos.models import Routine, RoutineCheck, RoutineItem
from todo.models import Task
from transactions.models import Transaction
```

---

## URL Patterns

| Route | View | Descrizione |
|-------|------|-------------|
| `/` | dashboard | Chat interface |
| `messages` | messages_api | Fetch messages |
| `favorite` | toggle_favorite | Toggle star |
| `insights` | insights | Insight cards |
| `temp/new` | create_temp_thread | New temp thread |
| `temp/remove` | remove_temp_thread | Delete thread |
| `quick` | quick_chat | Quick chat API |

---

## Funzionalità Core

### 1. Chat Modes
- **DIARY**: Thread singolo持久ente per diario
- **TEMPORARY**: Thread temporanei per domande one-off

### 2. Context Building
- `build_context_messages()`: aggrega dati da tutte le app
- `build_cognitive_context_for_prompt()`: bias detection
- `build_relational_context_for_prompt()`: distress signals

### 3. Persona System
- 4 preset (OPERATIVE, BALANCED, CLASSIC, ELITE)
- Configurazione psicologica avanzata
- Bias detection con 6 categorie

### 4. OpenAI Integration
- Conversations API (thread history)
- Responses API (single shot)
- Fallback automatico

---

## Cosa Mantenere (archibald_mail)

### Flag Rules per Email

L'app **archibald_mail** contiene flag rules che salvano automaticamente in **memory_stock**:

| Flag Token | Azione | Destinazione |
|-----------|-------|--------------|
| `$MEMORY` | memory_stock.save | memory_stock |
| `$IDEA` | memory_stock.save | memory_stock |
| `$TODO` | todo.capture | todo (fallback: memory_stock) |
| `$TRANSACTION` | transaction.capture | transactions |

### Codice di salvataggio email

```python
# archibald_mail/actions.py
from memory_stock.services import save_memory_from_inbound_email

def _execute_action_to_memory_stock(*, owner, sender, subject, body_text, message_id):
    save_memory_from_inbound_email(
        owner=owner,
        title=subject,
        note=body_text,
        source_sender=sender,
        source_subject=subject,
        source_message_id=message_id,
    )
```

---

## Operazioni per Rimozione

### 1. Rimuovere app archibald
```bash
# settings.py
INSTALLED_APPS = [
    ...
    # 'archibald',  # Remove this
    'archibald_mail',  # Keep
    ...
]
```

### 2. Rimuovere URLs
```python
# mio_master/urls.py
path('archibald/', include('archibald.urls')),  # Remove this line
```

### 3. Database migrations
```bash
# Generare migration per rimozione modelli
python manage.py makemigrations archibald --delete
python manage.py migrate
```

### 4. Cleanup env vars (opzionale)
```bash
# Da rimuovere da .env:
OPENAI_MODEL_ARCHIBALD
ARCHIBALD_REASONING_EFFORT
ARCHIBALD_USE_CONVERSATIONS
```

### 5. Rimuovere file
```bash
rm -rf archibald/
```

---

## Cosa Mantenere

### archibald_mail (funzionante)
- `archibald_mail/models.py` - MailboxConfig, FlagRule, InboundCategory, EmailMessage
- `archibald_mail/views.py` - Dashboard, flag management
- `archibald_mail/actions.py` - Email processing
- `archibald_mail/services.py` - IMAP/SMTP services
- `archibald_mail/templates/`

### memory_stock (già presente)
- Funzionalità di salvataggio note via email già attiva
- Flag `$MEMORY` e `$IDEA` in archibald_mail

---

## Dipendenze Inverse da Rimuovere

### Se altre app usano archibald:
```bash
rg "from archibald" --type py
rg "import archibald" --type py
```

### Potenziali riferimenti in:
- Documentazione
- Templates
- JavaScript
- Workbench

---

## Nuovo Progetto Specifiche Proposte

Se l'utente vuole creare un progetto separato per Archibald:

### Opzioni:

1. **Standalone Python app**
   - FastAPI/Flask + OpenAI SDK
   - Solo chat functionality
   - Deploy separato

2. **Servizio API**
   - REST API per chat
   - Integrabile via webhooks
   - Meno dipendente da MIO

3. **Tool CLI**
   - Command-line tool
   - Integrato in workflow esistenti

### Dati da esportare per nuovo progetto:
- `archibald_personaconfig` - Persona settings
- `archibald_thread` - Conversation history
- `archibald_message` - Messages

---

## Rischi e Considerazioni

### Basso impatto:
- Nessuna perdita di dati (se esportati)
- archibald_mail indipendente
- memory_stock già funzionante

### Pre-rimozione:
- [ ] Esportare PersonaConfig se necessario
- [ ] Verificare che nessun altro uso archibald
- [ ] Backup database
- [ ] Testare che email save funziona senza archibald

---

## Comandi Utili

```bash
# Trovare riferimenti
rg "archibald\." --type py
rg "from archibald" --type py

# Verificare flag rules attive
python manage.py shell
from archibald_mail.models import ArchibaldEmailFlagRule
print(list(ArchibaldEmailFlagRule.objects.filter(action_key='memory_stock.save')) 

# Testare email capture
python manage.py shell
from archibald_mail.services import process_inbound_emails
process_inbound_emails()
```