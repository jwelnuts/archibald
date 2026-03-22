# transactions

## Scopo
L'app `transactions` e il ledger unificato finanziario del progetto.
Gestisce entrate, uscite e trasferimenti con board filtrabile e form modale.

## Funzionalita principali
- Dashboard con board transazioni, riepiloghi e filtri avanzati.
- Supporto `tx_type`: IN, OUT, XFER.
- Partial HTMX per board/form/delete.
- Form entry con account, progetto, categoria, payee/income source, tag, allegati.
- KPI per tipo e totale netto filtrato.

## Modelli chiave
- `Transaction`: record finanziario centrale collegato a account/currency/project/category/payee/source/tag.

## View / Endpoint principali
- `GET /transactions/`: dashboard principale.
- `GET/POST /transactions/partials/board`
- `GET/POST /transactions/partials/form`
- `GET/POST /transactions/partials/delete`

## Template/UI principali
- `transactions/dashboard.html`
- `transactions/partials/board.html`
- `transactions/partials/form.html`
- `transactions/partials/delete.html`

## Integrazioni con altre app
- `subscriptions`: relazione `source_subscription` e pagamento occurrences.
- `projects`: progetto/categoria collegati.
- `core` (`Payee`), `income` (`IncomeSource`), `subscriptions` (`Account`,`Currency`,`Tag`).

## Casi d'uso reali
- Registrare movimenti finanza personale/progetto da un unico modulo.
- Filtrare rapidamente per tipo, periodo e query testo.
- Usare modali HTMX senza navigazione completa pagina.

## Note operative
- Context board calcola totali e counts sia filtered che globali.
- `_modal_open_url` permette deep-link da altri moduli (`open=new|edit|delete`).

## Copertura test esistente
- `TransactionsUnifiedFlowTests`

## Debito tecnico / TODO
- Aggiungere export CSV/PDF filtri correnti.
- Migliorare gestione trasferimenti con doppia scrittura controllata.

## Ultimo aggiornamento doc
- Data: 2026-03-22
- Autore: Codex
