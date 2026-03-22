# outcome

## Scopo
L'app `outcome` e il layer guidato per inserire uscite/spese (`Transaction` tipo `OUT`).

## Funzionalita principali
- Form spesa con payee, progetto, categoria, conto, allegato e tag.
- Creazione rapida progetto/categoria dal form.
- CRUD uscite filtrato su transazioni di tipo `EXPENSE`.
- Dashboard che redirige alla board transazioni filtrata uscite.

## Modelli chiave
- Nessun modello dominio dedicato.
- Dato persistito in `transactions.Transaction`.

## View / Endpoint principali
- `GET /outcome/`: redirect a `/transactions/?tx_type=OUT`.
- `GET/POST /outcome/api/add`
- `GET/POST /outcome/api/update?id=<tx_id>`
- `GET/POST /outcome/api/remove?id=<tx_id>`

## Template/UI principali
- `outcome/add_outcome.html`
- `outcome/update_outcome.html`
- `outcome/remove_outcome.html`

## Integrazioni con altre app
- `transactions`: persistenza spese.
- `core` (`Payee`) + `contacts`: sync beneficiario/fornitore.
- `projects`: progetto/categoria e quick create.
- `subscriptions`: valuta.

## Casi d'uso reali
- Registrare rapidamente una spesa con ricevuta allegata.
- Allineare payee in rubrica contatti durante l'inserimento.

## Note operative
- Validazione allegato: immagini/PDF max 10MB.
- `tx_type` forzato a `EXPENSE` lato view.

## Copertura test esistente
- `OutcomeAttachmentTests`
- `OutcomeDashboardFlowTests`

## Debito tecnico / TODO
- Uniformare UX con transazioni modali mantenendo preset outcome.
- Migliorare gestione duplicate payee.

## Ultimo aggiornamento doc
- Data: 2026-03-22
- Autore: Codex
