# core

## Scopo
L'app `core` e il backbone trasversale del progetto.
Gestisce auth/profile, dashboard principale, configurazioni UI, account finanziari legacy e API mobile.

## Funzionalita principali
- Dashboard globale con widget configurabili.
- Preferenze dashboard e navigazione personalizzabile per utente.
- Gestione hero actions globali.
- Signup/login/logout/profile/password change.
- Gestione account finanziari (`core/accounts/*`).
- Endpoint calendario eventi aggregati.
- API mobile: auth token, dashboard, routines, projects, agenda.
- Provisioning DAV account utente.

## Modelli chiave
- `Payee`: anagrafica beneficiario legacy.
- `UserHeroActionsConfig`: config visibilita azioni per utente.
- `UserNavConfig`: configurazione nav/widgets/preferences utente.
- `MobileApiSession`: sessione mobile con token hashati e scadenze.
- `DavAccount`: credenziali DAV per sync calendar.

## View / Endpoint principali
- UI:
  - `GET /`: dashboard core.
  - `GET /profile/`, `GET/POST /profile/nav/`, `GET/POST /profile/hero-actions/`.
  - `GET/POST /accounts/signup/`, login/logout/password change.
  - `GET/POST /core/accounts/*`.
- API mobile:
  - `POST /api/mobile/auth/login|refresh|logout`
  - `GET /api/mobile/dashboard`
  - `GET/POST /api/mobile/routines*`
  - `GET /api/mobile/projects`
  - `GET /api/mobile/agenda`
- API web tecniche:
  - `GET/POST /api/routines*`
  - `GET /api/projects`
  - `GET /api/agenda`

## Template/UI principali
- `core/dashboard.html`
- `core/profile.html`
- `core/nav_settings.html`
- `core/hero_actions.html`
- `core/accounts.html`
- `registration/login.html`
- `registration/signup.html`

## Integrazioni con altre app
- Usa dati da: `agenda`, `planner`, `projects`, `routines`, `subscriptions`, `todo`, `transactions`.
- Usa servizi DAV (`core.dav`) e routines services per API mobile.

## Casi d'uso reali
- Configurare home dashboard e nav secondo priorita utente.
- Usare app mobile con token refresh senza sessione browser.
- Gestire account e impostazioni trasversali senza entrare nei moduli verticali.

## Note operative
- API mobile usa token access+refresh con hashing persistito.
- Molti endpoint API supportano solo JSON e validano payload strict.
- Config widget/preferenze vengono normalizzate con whitelist.

## Copertura test esistente
- `ProfileArchibaldInstructionsTests`
- `DavProvisioningTests`
- `NavSettingsTests`
- `DashboardWidgetsTests`
- `DashboardPreferencesTests`
- `MobileApiAuthTests`

## Debito tecnico / TODO
- Separare viste UI e API in moduli dedicati per ridurre dimensione `views.py`.
- Rafforzare test end-to-end su token rotation mobile.

## Ultimo aggiornamento doc
- Data: 2026-03-22
- Autore: Codex
