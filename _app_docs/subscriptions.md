# subscriptions

## Scopo
L'app `subscriptions` gestisce abbonamenti ricorrenti, scadenze (`occurrences`), conti e pagamento con generazione transazione.

## Funzionalita principali
- Dashboard abbonamenti con upcoming/overdue.
- CRUD abbonamenti.
- Payment flow su occorrenza con creazione `Transaction` spesa.
- Calcolo next due date in base a intervallo/unita.
- Board parziale HTMX per aggiornamento rapido.

## Modelli chiave
- `Currency`: valuta condivisa (`common_currency`).
- `Tag`: tag owner-scoped.
- `Account`: conto finanziario owner-scoped.
- `Subscription`: definizione ricorrenza.
- `SubscriptionOccurrence`: singola scadenza (planned/paid/skipped/failed).

## View / Endpoint principali
- `GET /subs/`: dashboard.
- `GET /subs/api/board`: partial board.
- `GET/POST /subs/api/add`
- `GET/POST /subs/api/update?id=<id>`
- `GET/POST /subs/api/remove?id=<id>`
- `POST /subs/api/pay`: registra pagamento.

## Template/UI principali
- `subscriptions/dashboard.html`
- `subscriptions/partials/dashboard_board.html`
- `subscriptions/add_sub.html`
- `subscriptions/update_sub.html`
- `subscriptions/remove_sub.html`

## Integrazioni con altre app
- `transactions`: pagamento occurrence crea transazione `OUT`.
- `projects`: collega subscription a progetto/categoria.
- `core`: usa `Payee`.

## Casi d'uso reali
- Monitorare scadenze ricorrenti imminenti.
- Registrare pagamento con un click e avanzare prossima scadenza.

## Note operative
- `pay_subscription` gestisce sia occurrence esplicita che creazione on-demand da subscription.
- Se chiamata HTMX, risponde con partial board e trigger evento UI.

## Copertura test esistente
- `SubscriptionPaymentsTests`

## Debito tecnico / TODO
- Implementare generazione batch occurrences programmata.
- Aggiungere alert automatici multi-canale oltre dashboard.

## Ultimo aggiornamento doc
- Data: 2026-03-22
- Autore: Codex
