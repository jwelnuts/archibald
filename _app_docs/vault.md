# vault

## Scopo
L'app `vault` protegge segreti/password/note private con cifratura e sblocco TOTP.

## Funzionalita principali
- Setup TOTP iniziale con QR provisioning.
- Unlock/lock sessione vault con verifica codice 2FA.
- Protezione brute force con lock temporaneo dopo tentativi falliti.
- CRUD item vault cifrati.
- Reset completo TOTP + wipe contenuti vault.

## Modelli chiave
- `VaultProfile`: stato TOTP utente, lockout e tentativi.
- `VaultItem`: credenziali/note con campi cifrati (`secret_encrypted`, `notes_encrypted`).

## View / Endpoint principali
- `GET /vault/`: dashboard vault (richiede gate TOTP verificato).
- `GET/POST /vault/setup`
- `GET/POST /vault/unlock`
- `GET /vault/lock`
- `GET/POST /vault/reset`
- `GET/POST /vault/api/add`
- `GET/POST /vault/api/update?id=<id>`
- `GET/POST /vault/api/remove?id=<id>`

## Template/UI principali
- `vault/dashboard.html`
- `vault/setup_totp.html`
- `vault/unlock.html`
- `vault/reset_totp.html`
- `vault/add_item.html`
- `vault/update_item.html`
- `vault/remove_item.html`

## Integrazioni con altre app
- Modulo indipendente (nessuna dipendenza dominio forte).

## Casi d'uso reali
- Conservare password e note sensibili fuori dai moduli operativi.
- Bloccare temporaneamente il vault a fine sessione.

## Note operative
- Gate accesso: setup TOTP obbligatorio + sessione verificata.
- Dopo setup iniziale, il segreto non viene riesposto in chiaro via UI.
- Reset elimina item e configura nuovamente profilo TOTP.

## Copertura test esistente
- `VaultCryptoTests`
- `VaultFlowTests`

## Debito tecnico / TODO
- Aggiungere rotazione chiave cifratura assistita.
- Implementare storico accessi vault.

## Ultimo aggiornamento doc
- Data: 2026-03-22
- Autore: Codex
