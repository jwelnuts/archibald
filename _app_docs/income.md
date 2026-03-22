# income

## Scopo
L'app `income` e il layer guidato per inserire entrate (`Transaction` tipo `IN`) con UX semplificata.

## Funzionalita principali
- Form ingresso rapido entrata con source, progetto, categoria, conto, tag.
- Possibilita di creare al volo source/progetto/categoria.
- CRUD entrate filtrato su transazioni di tipo `INCOME`.
- Dashboard che redirige alla vista transazioni filtrata entrate.

## Modelli chiave
- `IncomeSource`: sorgente entrata (cliente, rimborso, ecc).
- Dato operativo persistito in `transactions.Transaction`.

## View / Endpoint principali
- `GET /income/`: redirect a `/transactions/?tx_type=IN`.
- `GET/POST /income/api/add`
- `GET/POST /income/api/update?id=<tx_id>`
- `GET/POST /income/api/remove?id=<tx_id>`

## Template/UI principali
- `income/add_income.html`
- `income/update_income.html`
- `income/remove_income.html`

## Integrazioni con altre app
- `transactions`: persistenza effettiva delle entrate.
- `contacts`: sync ruolo `income_source`/`customer` per source.
- `projects`: collegamento progetto/categoria e quick create.
- `subscriptions`: usa `Currency`.

## Casi d'uso reali
- Inserire un incasso con source e progetto in pochi passaggi.
- Aggiornare entrate storiche senza aprire la board transazioni completa.

## Note operative
- `tx_type` viene forzato a `INCOME` lato view.
- Form imposta valuta EUR di default.

## Copertura test esistente
- `IncomeDashboardFlowTests`

## Debito tecnico / TODO
- Consolidare UI con modal unica transazioni mantenendo preset income.
- Aggiungere validazioni avanzate anti-duplicato per source.

## Ultimo aggiornamento doc
- Data: 2026-03-22
- Autore: Codex
