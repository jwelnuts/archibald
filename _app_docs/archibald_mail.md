# archibald_mail

## Scopo
L'app `archibald_mail` gestisce inbox email di Archibald, regole flag e automazioni in ingresso/uscita.
Include anche classificazione manuale coda inbound e notifiche periodiche.

## Funzionalita principali
- Configurazione mailbox IMAP/SMTP per utente.
- Regole flag (`ArchibaldEmailFlagRule`) per mappare token ad azioni applicative.
- Coda inbound con review/apply/ignore/reopen.
- Categorie inbound personalizzabili.
- Log messaggi email inbound/outbound/notification/test.

## Modelli chiave
- `ArchibaldMailboxConfig`: parametri connessione e policy notifiche.
- `ArchibaldEmailFlagRule`: token -> action key applicativa.
- `ArchibaldInboundCategory`: categoria classificazione inbound.
- `ArchibaldEmailMessage`: storico messaggi e stato review/processamento.

## View / Endpoint principali
- `GET /archibald-mail/`: dashboard mailbox.
- `GET /archibald-mail/flags/`: lista regole.
- `GET/POST /archibald-mail/flags/add`
- `GET/POST /archibald-mail/flags/<rule_id>/edit`
- `GET/POST /archibald-mail/flags/<rule_id>/remove`
- `GET /archibald-mail/inbox/`: coda inbound.
- `POST /archibald-mail/inbox/<message_id>/apply`
- `POST /archibald-mail/inbox/<message_id>/ignore`
- `POST /archibald-mail/inbox/<message_id>/reopen`

## Template/UI principali
- `archibald_mail/dashboard.html`
- `archibald_mail/flag_rules.html`
- `archibald_mail/flag_rule_form.html`
- `archibald_mail/flag_rule_delete.html`
- `archibald_mail/inbound_queue.html`

## Integrazioni con altre app
- `memory_stock`, `todo`, `transactions`, `agenda`: azioni automatiche pilotate da flag.
- `archibald`: integrazione risposte AI per email abilitate.

## Casi d'uso reali
- Convertire email strutturate in memorie/task/transazioni.
- Smistare manualmente email inbound non coperte da flag.
- Inviare notifiche periodiche aggregate su attivita e scadenze.

## Note operative
- Config supporta fallback credenziali via variabili ambiente.
- `flag_token` viene normalizzato in uppercase e validato.
- Review workflow usa stato `PENDING/APPLIED/IGNORED`.

## Copertura test esistente
- `ArchibaldMailFormTests`
- `ArchibaldMailServicesTests`
- `ArchibaldMailActionsTests`
- `ArchibaldMailPromptingTests`
- `ArchibaldMailFlagCrudViewsTests`
- `ArchibaldMailInboundQueueViewsTests`
- `ArchibaldMailDigestTests`

## Debito tecnico / TODO
- Aggiungere metrics tecniche su throughput worker e retry.
- Migliorare UX bulk action sulla coda inbound.

## Ultimo aggiornamento doc
- Data: 2026-03-22
- Autore: Codex
