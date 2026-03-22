# contacts

## Scopo
L'app `contacts` centralizza rubrica persone/aziende e relativi ruoli operativi.
Include toolbox contatto con listini prezzo riusabili in altri moduli (es. preventivi).

## Funzionalita principali
- CRUD contatti con ruoli (`customer`, `supplier`, `payee`, `income_source`).
- Toolbox per contatto con note interne.
- CRUD listini (`ContactPriceList`) e righe listino (`ContactPriceListItem`).
- Sync bidirezionale con anagrafiche legacy (Customer/Payee/IncomeSource).

## Modelli chiave
- `Contact`: anagrafica unica persona/ente/azienda con ruoli multipli.
- `ContactToolbox`: contenitore extra dati e note interne contatto.
- `ContactPriceList`: listino associato al toolbox.
- `ContactPriceListItem`: righe prezzo con range quantita e prezzo unitario.

## View / Endpoint principali
- `GET /contacts/`: dashboard rubrica.
- `GET/POST /contacts/add`
- `GET/POST /contacts/update?id=<id>`
- `GET/POST /contacts/remove?id=<id>`
- `GET/POST /contacts/toolbox?id=<contact_id>`
- `GET/POST /contacts/price-lists/add?contact_id=<id>`
- `GET/POST /contacts/price-lists/update?id=<price_list_id>`
- `GET/POST /contacts/price-lists/remove?id=<price_list_id>`

## Template/UI principali
- `contacts/dashboard.html`
- `contacts/toolbox.html`
- `contacts/price_list_form.html`
- `contacts/price_list_remove.html`
- `contacts/add_contact.html`
- `contacts/update_contact.html`
- `contacts/remove_contact.html`

## Integrazioni con altre app
- `projects`/`finance_hub`/`income`/`outcome`/`transactions`:
  sync ruoli e anagrafiche tramite `contacts.services`.
- `projects` quote flow: usa listini toolbox per import righe preventivo.

## Casi d'uso reali
- Tenere un'unica rubrica con ruoli diversi per lo stesso soggetto.
- Gestire listini cliente e riusarli in preventivi.
- Allineare progressivamente dati legacy verso modello contatti unico.

## Note operative
- `_ensure_toolbox` crea toolbox on-demand per ogni contatto.
- `ContactPriceListItem` normalizza valori quantita/prezzo in save.
- `sync_contacts_from_legacy` viene invocata in piu entrypoint dashboard/form.

## Copertura test esistente
- `ContactsViewsTests`
- `ContactToolboxPriceListTests`

## Debito tecnico / TODO
- Esporre API dedicate per autocomplete contatti/listini.
- Aggiungere gestione versioning listini.

## Ultimo aggiornamento doc
- Data: 2026-03-22
- Autore: Codex
