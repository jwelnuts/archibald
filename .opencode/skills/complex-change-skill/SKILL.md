---
name: complex-change-workflow
description: Workflow operativo per pianificare, eseguire e verificare modifiche complesse nel progetto MIO Django + HTMX + Stimulus + UIKit.
---

# Complex Change Workflow — MIO Project

Use this skill when the user asks for a complex change, refactor, bug fix, feature implementation, or multi-file modification in the MIO Django monolith.

This skill is not a general architecture reference.  
Its purpose is to help the assistant modify the application safely, incrementally, and with verification.

The project uses:

- Django
- HTMX
- Stimulus
- UIKit
- Vite
- LESS
- user-owned data through `owner`
- layered architecture

---

## When To Use This Skill

Use this skill for:

- features touching more than one file
- changes involving models, migrations, forms, views, templates, static files, or URLs
- cross-app changes
- refactors
- bug fixes with unclear causes
- changes involving HTMX partials
- changes involving Stimulus/Vite
- changes involving ownership, permissions, or user-scoped data
- changes where regression risk is medium or high

Do not use this skill for:

- one-line copy changes
- simple CSS tweaks
- isolated typo fixes
- questions that only require explanation and no code change

---

## Core Objective

For every complex change:

1. understand the current behavior;
2. identify the minimal safe change;
3. avoid layer violations;
4. preserve ownership isolation;
5. make changes incrementally;
6. verify backend and frontend wiring;
7. explain what changed and how to test it.

---

## Non-Negotiable Safety Rules

Always enforce these rules.

1. Every protected view must use `@login_required`.
2. Every user-owned queryset must filter by `owner=request.user`.
3. Every user-owned object lookup must include `owner=request.user`.
4. Every new user-owned object must set `owner = request.user`.
5. Every POST form must include `{% csrf_token %}`.
6. Do not import from a higher layer into a lower layer.
7. Do not trust hidden inputs for ownership, permissions, or user identity.
8. Do not mix full-page responses and HTMX partial responses accidentally.
9. Do not add Stimulus files without wiring them into Vite.
10. Do not add LESS files without importing them.
11. Do not change model fields without considering migrations.
12. Do not make broad refactors when a targeted change solves the issue.
13. Do not leave debug code, temporary comments, or dead code.
14. Do not claim verification passed unless commands were actually run.

---

## Layer Rules

Architecture:

```text
L0 common
   ↓
L1 core
   ↓
L2 finance_hub / projects / contacts / subscriptions
   ↓
L3 transactions / todo / planner / routines / agenda / income / outcome
   ↓
L4 archibald / archibald_mail

Isolated:
vault / memory_stock / link_storage / workbench / ai_lab