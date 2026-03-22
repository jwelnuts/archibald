# finance_hub

## Scopo
L'app `finance_hub` gestisce ciclo commerciale e operativo: preventivi, fatture, ordini lavoro e codici IVA.

## Funzionalita principali
- Dashboard finanza con KPI e alert (quote in scadenza, invoice overdue, work order aperti).
- CRUD preventivi (`Quote`) con righe dettaglio (`QuoteLine`).
- CRUD fatture (`Invoice`).
- CRUD ordini lavoro (`WorkOrder`).
- Gestione tabella codici IVA (`VatCode`).
- Calcolo automatico imponibile/imposta/totale e sincronizzazione IVA su righe quote.

## Modelli chiave
- `VatCode`: anagrafica aliquote IVA.
- `Quote`: preventivo con cliente/progetto e totali.
- `QuoteLine`: righe articolo del preventivo.
- `Invoice`: fattura legata opzionalmente a quote.
- `WorkOrder`: ordine lavoro con importi stimati/finali.

## View / Endpoint principali
- `GET /finance/`: dashboard.
- `GET /finance/vat-codes/`
- `GET /finance/quotes/`, `add`, `update`, `remove`
- `GET /finance/invoices/`, `add`, `update`, `remove`
- `GET /finance/work-orders/`, `add`, `update`, `remove`

## Template/UI principali
- `finance_hub/dashboard.html`
- `finance_hub/quote_form.html`
- `finance_hub/quotes.html`
- `finance_hub/invoice_form.html`
- `finance_hub/work_order_form.html`
- `finance_hub/vat_codes.html`

## Integrazioni con altre app
- `projects`: usa `Project` e `Customer` in documenti commerciali.
- `projects`: dal dettaglio progetto (`/projects/view`) mostra gli ultimi preventivi collegati con link rapido a `/finance/quotes/update`.
- `subscriptions`: usa `Currency` e `Account`.
- `contacts`: sync contatto cliente via servizi dedicati.

## Casi d'uso reali
- Preparare preventivi multi-riga con IVA coerente.
- Tracciare conversione quote->invoice e monitorare pipeline.
- Gestire ordini lavoro e stato avanzamento economico.

## Note operative
- I codici IVA default vengono auto-creati on-demand per utente.
- Se quote ha righe, i totali vengono ricalcolati dal dettaglio righe.
- Quote form supporta scelta progetto esistente o creazione rapida progetto.

## Copertura test esistente
- `FinanceHubViewsTests`

## Debito tecnico / TODO
- Estrarre logica condivisa quote in service layer riusabile anche da `projects`.
- Aggiungere test su casi edge fiscali multi-aliquota.

## Ultimo aggiornamento doc
- Data: 2026-03-22
- Autore: Codex
