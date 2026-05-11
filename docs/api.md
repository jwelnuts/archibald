---
title: API Endpoints
tags: [api, endpoints, json]
aliases: [rest, mobile-api]
---

# API Endpoints

This document describes all API endpoints in MIO Master.

---

## Mobile API

**Base URL:** `/api/mobile/`

Authentication required for all endpoints.

### POST /api/mobile/auth/login
```json
// Request
{
  "identity": "email_or_username",
  "password": "password",
  "device_label": "optional"  // optional
}

// Response
{
  "access_token": "...",
  "refresh_token": "...",
  "access_expires_at": "ISO8601",
  "refresh_expires_at": "ISO8601",
  "user": { ... }
}
```

### POST /api/mobile/auth/refresh
```json
// Request
{
  "refresh_token": "..."
}

// Response
{
  "access_token": "new_token",
  "refresh_token": "new_refresh",
  "access_expires_at": "...",
  "refresh_expires_at": "..."
}
```

### POST /api/mobile/auth/logout
```json
// Request (header: Authorization: Bearer <access_token>)
{
  "refresh_token": "optional"
}
```

### GET /api/mobile/dashboard
```
Header: Authorization: Bearer <access_token>

// Response - dashboard metrics + recent events
```

---

## Project API

**Base URL:** `/projects/api/`

| Method | Endpoint | Description |
|--------|----------|-------------|
| POST | `/projects/api/add` | Add project |
| POST | `/projects/api/remove` | Remove project |
| POST | `/projects/api/update` | Update project |

---

## Todo API

**Base URL:** `/todo/api/`

| Method | Endpoint | Description |
|--------|----------|-------------|
| POST | `/todo/api/add` | Add task |
| POST | `/todo/api/remove` | Remove task |
| POST | `/todo/api/update` | Update task |
| POST | `/todo/api/status` | Set task status |
| POST | `/todo/api/sync-vtodo` | Sync to CalDAV |

---

## Contacts API

**Base URL:** `/contacts/api/`

| Method | Endpoint | Description |
|--------|----------|-------------|
| GET | `/contacts/api/payees/search` | Search payees |
| POST | `/contacts/api/payees/quick-create` | Quick create payee |

---

## Calendar Events API

**Base URL:** `/calendar/`

| Method | Endpoint | Description |
|--------|----------|-------------|
| GET | `/calendar/events` | Aggregated events from all apps |

Returns events from:
- todo (Task)
- planner (PlannerItem)
- subscriptions (SubscriptionOccurrence)
- transactions (Transaction)
- routines (RoutineCheck)

---

## Hero Actions API

**Base URL:** `/core/hero-actions/`

| Method | Endpoint | Description |
|--------|----------|-------------|
| GET/POST | `/core/hero-actions/api` | Hero actions configuration |

---

## Archibald Messages API

**Base URL:** `/archibald/`

| Method | Endpoint | Description |
|--------|----------|-------------|
| GET/POST | `/archibald/messages` | Chat messages |
| POST | `/archibald/favorite` | Toggle favorite |

---

## HTMX Partials

Various apps expose HTMX partial endpoints for dynamic content:

### Transactions
- `/transactions/partials/board` - Board refresh
- `/transactions/partials/form` - Form modal
- `/transactions/partials/delete` - Delete modal

### Subscriptions
- `/finance/subscriptions/board` - Dashboard board

### Routines
- `/todos/check` - Check item

---

## Debug Endpoints (Superuser)

**Base URL:** `/workbench/debug/`

| Endpoint | Description |
|----------|-------------|
| `/workbench/debug/logs` | Debug logs viewer |
| `/workbench/debug/radicale` | Radicale status |
| `/workbench/debug/api-endpoints` | API endpoints list |
| `/workbench/debug/schema` | DB schema explorer |

---

## Public Endpoints

| Endpoint | Description |
|----------|-------------|
| `/finance/quotes/confirm/<token>` | Public quote confirmation |
| `/finance/quotes/confirm/<token>/pdf` | Public quote PDF |

---

## Related Documentation

- [[views|Views & URLs]]
- [[deployment|Deployment]] - Security notes