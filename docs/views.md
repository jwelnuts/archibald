---
title: Views & URLs
tags: [views, urls, endpoints]
aliases: [routes, view-functions]
---

# Views & URL Patterns

This document lists all views and URL routes by Django app.

---

## finance_hub

**Base URL:** `/finance/` (also accessible via `/subs/`)

### Dashboard
| View | URL | Description |
|------|-----|-------------|
| `dashboard` | `/finance/` | Finance hub main dashboard |
| `subscriptions_dashboard` | `/finance/subscriptions/` | Subscriptions dashboard |
| `dashboard_board` | `/finance/subscriptions/board` | HTMX partial for subscriptions |

### Quotes
| View | URL | Description |
|------|-----|-------------|
| `quotes` | `/finance/quotes/` | Quote list |
| `add_quote` | `/finance/quotes/add` | Create new quote |
| `update_quote` | `/finance/quotes/update` | Edit quote (select via `?id=` ) |
| `remove_quote` | `/finance/quotes/remove` | Delete quote |
| `share_quote` | `/finance/quotes/share` | Generate public share link |
| `quote_pdf` | `/finance/quotes/pdf` | Download quote PDF |
| `public_quote_confirm` | `/finance/quotes/confirm/<token>` | Public quote confirmation |
| `public_quote_pdf` | `/finance/quotes/confirm/<token>/pdf` | Public quote PDF download |

### Invoices
| View | URL | Description |
|------|-----|-------------|
| `invoices` | `/finance/invoices/` | Invoice list |
| `add_invoice` | `/finance/invoices/add` | Create new invoice |
| `update_invoice` | `/finance/invoices/update` | Edit invoice |
| `remove_invoice` | `/finance/invoices/remove` | Delete invoice |

### Work Orders
| View | URL | Description |
|------|-----|-------------|
| `work_orders` | `/finance/work-orders/` | Work order list |
| `add_work_order` | `/finance/work-orders/add` | Create new work order |
| `update_work_order` | `/finance/work-orders/update` | Edit work order |
| `remove_work_order` | `/finance/work-orders/remove` | Delete work order |

### Subscriptions
| View | URL | Description |
|------|-----|-------------|
| `add_sub` | `/finance/subscriptions/add` | Add subscription |
| `remove_sub` | `/finance/subscriptions/remove` | Remove subscription |
| `update_sub` | `/finance/subscriptions/update` | Edit subscription |
| `pay_subscription` | `/finance/subscriptions/pay` | Pay subscription (POST) |

### Settings
| View | URL | Description |
|------|-----|-------------|
| `vat_codes` | `/finance/vat-codes/` | VAT code management |

---

## transactions

**Base URL:** `/transactions/`

### Views
| View | URL | Description |
|------|-----|-------------|
| `dashboard` | `/transactions/` | Transactions dashboard |
| `board_partial` | `/transactions/partials/board` | HTMX board |
| `form_partial` | `/transactions/partials/form` | HTMX form modal |
| `delete_partial` | `/transactions/partials/delete` | HTMX delete modal |

---

## projects

**Base URL:** `/projects/`

### Views
| View | URL | Description |
|------|-----|-------------|
| `dashboard` | `/projects/` | Projects dashboard |
| `project_detail` | `/projects/view` | Project detail (via `?id=`) |
| `add_project_quote` | `/projects/quotes/add` | Quick create quote |
| `add_subproject` | `/projects/subprojects/add` | Add subproject |
| `subproject_detail` | `/projects/subprojects/view` | Subproject detail |
| `update_subproject` | `/projects/subprojects/update` | Edit subproject |
| `project_storyboard` | `/projects/storyboard` | Project storyboard |
| `project_storyboard_log` | `/projects/storyboard/log` | Storyboard timeline |
| `project_storyboard_delete_note` | `/projects/storyboard/note/delete` | Delete note |
| `project_hero_actions` | `/projects/hero-actions` | Hero actions config |
| `add_project` | `/projects/api/add` | API add project |
| `remove_project` | `/projects/api/remove` | API remove project |
| `update_project` | `/projects/api/update` | API update project |
| `categories` | `/projects/categories/` | Category list |
| `add_category` | `/projects/categories/add` | Add category |
| `remove_category` | `/projects/categories/remove` | Remove category |
| `update_category` | `/projects/categories/update` | Update category |

---

## contacts

**Base URL:** `/contacts/`

### Views
| View | URL | Description |
|------|-----|-------------|
| `dashboard` | `/contacts/` | Contacts dashboard |
| `add_contact` | `/contacts/add` | Add contact |
| `update_contact` | `/contacts/update` | Edit contact |
| `remove_contact` | `/contacts/remove` | Delete contact |
| `toolbox` | `/contacts/toolbox` | Contact toolbox |
| `add_price_list` | `/contacts/price-lists/add` | Add price list |
| `update_price_list` | `/contacts/price-lists/update` | Edit price list |
| `remove_price_list` | `/contacts/price-lists/remove` | Delete price list |
| `api_payee_search` | `/contacts/api/payees/search` | Payee search API |
| `api_payee_quick_create` | `/contacts/api/payees/quick-create` | Quick create payee |

---

## core

**Base URL:** `/` (and `/accounts/` for auth)

### Views
| View | URL | Description |
|------|-----|-------------|
| `dashboard` | `/` | Main dashboard |
| `login` | `/accounts/login/` | Login |
| `logout` | `/accounts/logout/` | Logout |
| `signup` | `/accounts/signup/` | Signup |
| `profile` | `/accounts/profile/` | User profile |
| `password_change` | `/accounts/password/` | Password change |
| `protected_media` | `/media/<path>` | Protected media serve |
| `calendar_events` | `/calendar/events` | Aggregated calendar events |
| `account_list` | `/core/accounts/` | Account list |
| `account_add` | `/core/accounts/add` | Add account |
| `account_update` | `/core/accounts/update` | Update account |
| `account_remove` | `/core/accounts/remove` | Remove account |
| `hero_actions` | `/core/hero-actions/` | Hero actions config |
| `hero_actions_api` | `/core/hero-actions/api` | Hero actions API |

---

## agenda

**Base URL:** `/agenda/`

### Views
| View | URL | Description |
|------|-----|-------------|
| `dashboard` | `/agenda/` | Agenda dashboard |
| `panel` | `/agenda/panel` | Agenda panel |
| `snapshot` | `/agenda/snapshot` | Agenda snapshot |
| `item_action` | `/agenda/item-action` | Item action (POST) |
| `preferences` | `/agenda/preferences` | Agenda preferences |

---

## planner

**Base URL:** `/planner/`

### Views
| View | URL | Description |
|------|-----|-------------|
| `dashboard` | `/planner/` | Planner dashboard |
| `add_item` | `/planner/add` | Add item |
| `update_item` | `/planner/update` | Edit item |
| `remove_item` | `/planner/remove` | Delete item |

---

## routines

**Base URL:** `/routines/`

### Views
| View | URL | Description |
|------|-----|-------------|
| `dashboard` | `/routines/` | Routines dashboard |
| `stats` | `/routines/stats` | Statistics |
| `check_item` | `/routines/check` | Check item (POST) |
| `add_routine` | `/routines/api/add` | Add routine |
| `update_routine` | `/routines/api/update` | Update routine |
| `remove_routine` | `/routines/api/remove` | Remove routine |
| `add_item` | `/routines/items/add` | Add routine item |
| `update_item` | `/routines/items/update` | Edit item |
| `remove_item` | `/routines/items/remove` | Delete item |

---

## todo

**Base URL:** `/todo/`

### Views
| View | URL | Description |
|------|-----|-------------|
| `dashboard` | `/todo/` | Todo dashboard |
| `add_task` | `/todo/api/add` | Add task |
| `remove_task` | `/todo/api/remove` | Remove task |
| `update_task` | `/todo/api/update` | Update task |
| `set_status` | `/todo/api/status` | Set task status |
| `sync_vtodo` | `/todo/api/sync-vtodo` | Sync to CalDAV |

---

## vault

**Base URL:** `/vault/`

### Views
| View | URL | Description |
|------|-----|-------------|
| `dashboard` | `/vault/` | Vault dashboard |
| `setup_totp` | `/vault/setup` | Initial TOTP setup |
| `unlock` | `/vault/unlock` | Unlock vault |
| `lock` | `/vault/lock` | Lock vault |
| `reset_totp` | `/vault/reset` | Reset TOTP |
| `add_item` | `/vault/api/add` | Add item |
| `update_item` | `/vault/api/update` | Edit item |
| `remove_item` | `/vault/api/remove` | Delete item |

---

## archibald

**Base URL:** `/archibald/`

### Views
| View | URL | Description |
|------|-----|-------------|
| `dashboard` | `/archibald/` | Archibald dashboard |
| `messages_api` | `/archibald/messages` | Messages API |
| `toggle_favorite` | `/archibald/favorite` | Toggle favorite |
| `insights` | `/archibald/insights` | Insight cards |
| `create_temp_thread` | `/archibald/temp/new` | Create temp thread |
| `remove_temp_thread` | `/archibald/temp/remove` | Remove temp thread |
| `quick_chat` | `/archibald/quick` | Quick chat |

---

## archibald_mail

**Base URL:** `/archibald-mail/`

### Views
| View | URL | Description |
|------|-----|-------------|
| `dashboard` | `/archibald-mail/` | Mail dashboard |
| `flag_rules` | `/archibald-mail/flags/` | Flag rules |
| `add_flag_rule` | `/archibald-mail/flags/add` | Add flag rule |
| `edit_flag_rule` | `/archibald-mail/flags/<id>/edit` | Edit flag rule |
| `remove_flag_rule` | `/archibald-mail/flags/<id>/remove` | Remove flag rule |
| `inbound_queue` | `/archibald-mail/inbox/` | Inbound queue |
| `apply_inbound_message` | `/archibald-mail/inbox/<id>/apply` | Apply flag |
| `ignore_inbound_message` | `/archibald-mail/inbox/<id>/ignore` | Ignore message |
| `reopen_inbound_message` | `/archibald-mail/inbox/<id>/reopen` | Reopen message |

---

## memory_stock

**Base URL:** `/memory-stock/`

### Views
| View | URL | Description |
|------|-----|-------------|
| `dashboard` | `/memory-stock/` | Memory stock dashboard |
| `add_item` | `/memory-stock/api/add` | Add item |
| `update_item` | `/memory-stock/api/update` | Update item |
| `remove_item` | `/memory-stock/api/remove` | Remove item |
| `toggle_archive` | `/memory-stock/api/archive` | Toggle archive |

---

## link_storage

**Base URL:** `/link_storage/`

### Views
| View | URL | Description |
|------|-----|-------------|
| `dashboard` | `/link_storage/` | Links dashboard |
| `add_item` | `/link_storage/api/add` | Add link |
| `update_item` | `/link_storage/api/update` | Update link |
| `remove_item` | `/link_storage/api/remove` | Remove link |

---

## workbench

**Base URL:** `/workbench/` (superuser only)

### Views
| View | URL | Description |
|------|-----|-------------|
| `dashboard` | `/workbench/` | Workbench dashboard |
| `add_item` | `/workbench/api/add` | Add item |
| `remove_item` | `/workbench/api/remove` | Remove item |
| `update_item` | `/workbench/api/update` | Update item |
| `debug_logs` | `/workbench/debug/logs` | Debug logs |
| `radicale_debug` | `/workbench/debug/radicale` | Radicale debug |
| `api_endpoints` | `/workbench/debug/api-endpoints` | API endpoints |
| `db_schema` | `/workbench/debug/schema` | DB schema explorer |

---

## URL Summary by Prefix

| Prefix | App |
|--------|-----|
| `/` | core |
| `/accounts/` | core auth |
| `/finance/` | finance_hub |
| `/subs/` | finance_hub |
| `/transactions/` | transactions |
| `/projects/` | projects |
| `/contacts/` | contacts |
| `/todo/` | todo |
| `/agenda/` | agenda |
| `/workbench/` | workbench |
| `/planner/` | planner |
| `/routines/` | routines |
| `/archibald/` | archibald |
| `/archibald-mail/` | archibald_mail |
| `/memory-stock/` | memory_stock |
| `/vault/` | vault |
| `/link_storage/` | link_storage |

---

## Related Documentation

- [[apps|Apps Overview]]
- [[models|Database Models]]
- [[api|API Endpoints]]