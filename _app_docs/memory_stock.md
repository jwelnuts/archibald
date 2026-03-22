# memory_stock

## Scopo
L'app `memory_stock` archivia memorie testuali e metadati, anche originate da pipeline email/automation.

## Funzionalita principali
- CRUD memorie.
- Archiviazione/de-archiviazione item.
- Conservazione metadati sorgente (sender, subject, message id, action).

## Modelli chiave
- `MemoryStockItem`: titolo, nota, URL sorgente, metadati e flag archivio.

## View / Endpoint principali
- `GET /memory-stock/`
- `GET/POST /memory-stock/api/add`
- `GET/POST /memory-stock/api/update?id=<id>`
- `GET/POST /memory-stock/api/remove?id=<id>`
- `POST /memory-stock/api/archive?id=<id>`

## Template/UI principali
- `memory_stock/dashboard.html`
- `memory_stock/add_item.html`
- `memory_stock/update_item.html`
- `memory_stock/remove_item.html`

## Integrazioni con altre app
- `archibald_mail`: principale sink di alcune azioni email.

## Casi d'uso reali
- Salvare idee/brief estratti da email o input manuale.
- Archiviare memorie concluse mantenendo storico ricercabile.

## Note operative
- Campo `metadata` JSON libero per estensioni future.
- Indice su `source_message_id` per dedup/tracciamento inbound.

## Copertura test esistente
- `MemoryStockServiceTests`
- `MemoryStockViewTests`

## Debito tecnico / TODO
- Implementare filtri avanzati su metadati sorgente.
- Aggiungere tagging dedicato memoria.

## Ultimo aggiornamento doc
- Data: 2026-03-22
- Autore: Codex
