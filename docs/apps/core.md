---
title: core
tags: [app, core]
aliases: [auth, users, dav, calendar, payees]
---

# Core App

Core functionality including authentication, payees, DAV/CalDAV support, mobile API, and user configuration.

## Models

| Model | Description | Key Fields |
|-------|-------------|------------|
| `Payee` | Beneficiaries/payees | name, website |
| `UserHeroActionsConfig` | User hero actions settings | user, config |
| `UserNavConfig` | Navigation configuration | user, config |
| `MobileApiSession` | Mobile API sessions | user, access_token_hash, refresh_token_hash, expiry times, device info |
| `DavAccount` | DAV account credentials | user, dav_username, password_hash, is_active |
| `DavExternalAccount` | External DAV accounts | owner, label, dav_username, password_hash |
| `DavTeam` | DAV teams | owner, name, slug, is_active |
| `DavManagedCalendar` | Managed calendars | owner, principal, calendar_slug, display_name |
| `DavCalendarGrant` | Calendar access grants | owner, external_account, calendar, access_level |

### DAV Access Levels

- `ro` - Read-only
- `rw` - Read-write

## URLs

### Authentication
| Route | Name |
|-------|------|
| `/accounts/login/` | login |
| `/accounts/logout/` | logout |
| `/accounts/signup/` | signup |
| `/accounts/password_change/` | password_change |

### Mobile API
| Route | Name |
|-------|------|
| `/api/mobile/auth/login` | mobile-auth-login |
| `/api/mobile/auth/refresh` | mobile-auth-refresh |
| `/api/mobile/auth/logout` | mobile-auth-logout |
| `/api/mobile/dashboard` | mobile-dashboard |
| `/api/mobile/routines` | mobile-routines |
| `/api/mobile/todos/check` | mobile-todos-check |
| `/api/mobile/todos/items/create` | mobile-todos-item-create |
| `/api/mobile/todos/items/update` | mobile-todos-item-update |
| `/api/mobile/todos/items/delete` | mobile-todos-item-delete |

### Core Features
| Route | Name |
|-------|------|
| `/` | core-dashboard |
| `/dashboard/widgets` | core-dashboard-widgets |
| `/dashboard/preferences` | core-dashboard-preferences |
| `/profile/` | profile |
| `/profile/dav/` | dav-management |
| `/profile/hero-actions/` | hero-actions |
| `/profile/nav/` | nav-settings |
| `/calendar/events` | core-calendar-events |
| `/core/accounts/` | core-accounts |

## Related Apps

- [[transactions]] - Payee linking
- [[finance_hub]] - Payee for subscriptions
- [[routines]] - UserHeroActionsConfig usage
- [[agenda]] - DavCalendarGrant
- [[todo]] - DAV sync (CalDAV)