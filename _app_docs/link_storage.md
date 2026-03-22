# link_storage

## Scopo
L'app `link_storage` e un archivio leggero di link utili con priorita e note.

## Funzionalita principali
- CRUD link.
- Classificazione rapida per categoria predefinita.
- Ordinamento semplice via dashboard.

## Modelli chiave
- `Link`: URL, categoria, importanza, nota.

## View / Endpoint principali
- `GET /link_storage/`
- `GET/POST /link_storage/api/add`
- `GET/POST /link_storage/api/update?id=<id>`
- `GET/POST /link_storage/api/remove?id=<id>`

## Template/UI principali
- `link_storage/dashboard.html`
- `link_storage/add_item.html`
- `link_storage/update_item.html`
- `link_storage/remove_item.html`

## Integrazioni con altre app
- Nessuna integrazione forte: modulo indipendente.

## Casi d'uso reali
- Salvare reference tecniche o personali con priorita.
- Mantenere una mini knowledge base URL centrica.

## Note operative
- Modello minimale senza normalizzazione extra category.

## Copertura test esistente
- `SmokeTest`

## Debito tecnico / TODO
- Sostituire category fissa con tassonomia dinamica.
- Aggiungere ricerca full-text.

## Ultimo aggiornamento doc
- Data: 2026-03-22
- Autore: Codex
