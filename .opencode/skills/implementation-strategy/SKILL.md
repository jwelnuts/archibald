---
name: implementation-strategy
description: Implementation strategy, architecture rules, development workflow, and feature checklist for the MIO Django monolith using Django + HTMX + Stimulus + UIKit.
---

# Implementation Strategy — MIO Project

Use this skill when implementing, reviewing, refactoring, or planning features for the MIO monolith.

The project is a Django monolith using:

- Django
- HTMX
- Stimulus
- UIKit
- Vite
- LESS
- user-owned data isolation through `owner`

The goal of this skill is to enforce architecture boundaries, safe ownership filtering, predictable UI patterns, and a consistent implementation workflow.

---

## Non-Negotiable Rules

These rules always apply.

1. Every user-owned query must be filtered by `owner=request.user`.
2. Every object lookup for user-owned models must include `owner=request.user`.
3. Every view must use `@login_required`, unless it is intentionally public.
4. Every POST form must include `{% csrf_token %}`.
5. New records owned by a user must set `item.owner = request.user` before saving.
6. Never import from a higher layer into a lower layer.
7. Use Post/Redirect/Get for traditional POST flows.
8. Use HTMX partials only when replacing a specific page fragment.
9. Use Stimulus only for client-side interaction or as a wrapper around JS libraries.
10. No debug `print()` statements in final code.
11. Do not leave migrations, Vite entries, templates, or styles half-wired.
12. Do not introduce cross-app dependencies without checking the layer map.

---

## Architecture Layers

```text
L0 common
   ↓
L1 core
   ↓
L2 hubs
   ↓
L3 ops
   ↓
L4 archibald / archibald_mail

Isolated apps:
vault, memory_stock, link_storage, workbench, ai_lab