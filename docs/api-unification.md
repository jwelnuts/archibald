# API Unification (Web + Mobile)

## Goal
Use the same backend endpoints for web and mobile clients, with a single business logic path.

## Rules
- Prefer `/api/<domain>/...` as canonical endpoints.
- Keep old `/api/mobile/...` endpoints only as compatibility aliases.
- Business logic must live in app services (example: `routines/services.py`).
- Endpoint handlers should be thin: parse payload, auth, call service, return JSON.

## Auth
- Canonical API endpoints (`/api/...`) support:
  - Bearer token (mobile/native clients)
  - Django session auth (web clients)
- Mobile alias endpoints can remain bearer-only if needed.

## Response contract
- Success: `{ "ok": true, ... }`
- Error: `{ "ok": false, "error": "error_code" }`
- Use stable `error` codes (not translated strings) for frontend handling.

## Migration strategy
1. Add canonical `/api/...` endpoint.
2. Point mobile client to canonical endpoint.
3. Gradually migrate web async calls to canonical endpoint.
4. Keep legacy routes during migration window.
5. Remove legacy routes only after clients are fully migrated.

## Implemented example
- `routines` domain now has canonical endpoints under `/api/routines/...` and compatibility under `/api/mobile/routines/...`.
