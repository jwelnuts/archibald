# archibald

## Scopo
L'app `archibald` implementa l'assistente AI contestuale del sistema.
Gestisce chat persistenti, thread temporanei, preferiti e insight sui dati utente.

## Funzionalita principali
- Dashboard chat con thread diario e thread temporanei.
- Invio/ricezione messaggi con integrazione OpenAI Responses API.
- Supporto conversation state (`openai_conversation_id`, `last_response_id`).
- Toggle messaggi preferiti.
- Insight cards contestuali generate dai dati di dominio.
- Quick chat endpoint dedicato.

## Modelli chiave
- `ArchibaldThread`: contenitore conversazione (`DIARY` o `TEMPORARY`).
- `ArchibaldMessage`: messaggio chat con ruolo, contenuto, favorite flag.

## View / Endpoint principali
- `GET /archibald/`: dashboard chat.
- `POST /archibald/messages`: invio messaggi.
- `POST /archibald/favorite`: toggle favorite.
- `GET /archibald/insights`: insight cards.
- `POST /archibald/temp/new`: crea thread temporaneo.
- `POST /archibald/temp/remove`: rimuove thread temporaneo.
- `POST /archibald/quick`: quick chat.

## Template/UI principali
- `archibald/dashboard.html`
- `archibald/partials/insight_cards.html`

## Integrazioni con altre app
- `core`, `projects`, `todo`, `planner`, `routines`, `subscriptions`, `transactions`, `income`:
  i servizi di contesto leggono dati cross-app per produrre insight e risposte piu utili.

## Casi d'uso reali
- Chiedere sintesi operative del proprio stato (task, routine, finanza, progetti).
- Lavorare in thread temporanei per ragionamenti spot.
- Salvare messaggi critici nei preferiti.

## Note operative
- Modalita API selezionata anche via env (`ARCHIBALD_USE_CONVERSATIONS`).
- Sistema prompt composto da blocchi (base + cognitive context + dati utente).

## Copertura test esistente
- `ArchibaldModesTests`

## Debito tecnico / TODO
- Migliorare osservabilita su fallback errori OpenAI per thread lunghi.
- Aggiungere strumenti di pruning cronologia per thread molto estesi.

## Ultimo aggiornamento doc
- Data: 2026-03-22
- Autore: Codex
