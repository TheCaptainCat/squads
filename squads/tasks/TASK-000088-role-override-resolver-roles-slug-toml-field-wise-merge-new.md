---
id: TASK-88
sequence_id: 88
type: task
title: 'Role override resolver: roles/<slug>.toml field-wise merge + new slugs'
status: Done
parent: FEAT-14
author: tech-lead
priority: high
refs:
- TASK-89:blocks
- TASK-91:blocks
description: Layer .overrides/roles/<slug>.toml over PREDEFINED field-wise; admit
  new slugs; activate_role/add_dev read through the resolver
subentities:
- local_id: ST1
  title: Field-wise roles/<slug>.toml resolver over PREDEFINED + new-slug admission
  status: Done
  story: US2
- local_id: ST2
  title: activate_role/add_dev read through resolver; full_name seed; tests
  status: Done
  story: US2
created_at: '2026-06-12T20:56:51Z'
updated_at: '2026-07-06T15:19:39Z'
---
<!-- sq:body -->
Role-override task for FEAT-14 (ADR-85 §2 'roles merge field-wise', §1 roles-as-TOML, Consequences 'roles gain a merge step').

**Goal.** A project can override or add roles via `<squad-dir>/.overrides/roles/<slug>.toml` with the same project → bundled precedence, picked up by the sync/spawn (activate/add) flows.

**Scope.** (1) A thin resolver beside `_roles/_catalog.py` that layers `roles/<slug>.toml` over `PREDEFINED`: for a **bundled** slug, override only the fields the TOML sets, inheriting the rest (rename `architect`, change its model, etc. without restating the mission); for a **new** slug, define a wholly new `RoleDef`. Field-wise merge is the ONE place merging is allowed (RoleDef is structured data, not prose). (2) `activate_role`/`add_dev` read RoleDefs **through** this resolver. (3) A `roles/<slug>.toml` may carry `full_name`, which seeds the name when that role is activated (coordinate the key with T4's `extra.full_name` channel).

**Out of scope.** The role *body shape* (`agents/role.md.j2`) is governed by template override (T1's loader), not here — this task is the structured `RoleDef` surface only.

**Acceptance.** A field-wise override of a bundled role (e.g. rename + model change) and a brand-new role slug are both picked up by activate/add and flow to the roster/pointers/CLAUDE.md (which already read `extra`). Covered by a service-level test (field-wise override + new slug) + a CLI smoke test. `sq check` stays clean.

**Dependencies.** Builds on T1's `.overrides/` layout + path resolution. The `full_name`-seed touchpoint coordinates with T4 (naming → `extra.full_name`).
<!-- sq:body:end -->

## Subtasks

_Add with `sq task 88 add-subtask "<title>"`; track with `sq task 88 subtask <n> update --status <Status>`._

<!-- sq:summary -->
| Subtask | Status | Assignee | Title | Story |
| --- | --- | --- | --- | --- |
| ST1 | Done |  | Field-wise roles/<slug>.toml resolver over PREDEFINED + new-slug admission | US2 |
| ST2 | Done |  | activate_role/add_dev read through resolver; full_name seed; tests | US2 |
<!-- sq:summary:end -->

<!-- sq:subtasks -->

<!-- sq:subtask:ST1 -->
### ST1 — Field-wise roles/<slug>.toml resolver over PREDEFINED + new-slug admission

<!-- sq:subtask:ST1:head -->
**Status:** 🟢 Done
**Implements:** US2 — As a project lead, I want to add or override role definitions for my project, so that the squad matches my actual team
<!-- sq:subtask:ST1:head:end -->

<!-- sq:subtask:ST1:body -->
Add a thin role-override resolver beside _roles/_catalog.py that layers .overrides/roles/<slug>.toml over PREDEFINED field-wise: for a bundled slug, override only the fields the TOML sets (rename, model change) inheriting the rest; for a new slug, define a wholly new RoleDef. Field-wise merge is the one sanctioned merge point (RoleDef is structured data, not prose) (US2).
<!-- sq:subtask:ST1:body:end -->

#### Discussion

<!-- sq:subtask:ST1:discussion -->
<!-- sq:subtask:ST1:discussion:end -->
<!-- sq:subtask:ST1:end -->

<!-- sq:subtask:ST2 -->
### ST2 — activate_role/add_dev read through resolver; full_name seed; tests

<!-- sq:subtask:ST2:head -->
**Status:** 🟢 Done
**Implements:** US2 — As a project lead, I want to add or override role definitions for my project, so that the squad matches my actual team
<!-- sq:subtask:ST2:head:end -->

<!-- sq:subtask:ST2:body -->
Make activate_role/add_dev read RoleDefs through the new resolver, and honour a full_name key in roles/<slug>.toml that seeds the name on activation (coordinated with T4's extra.full_name channel). Covered by a service-level test (field-wise override of a bundled role + a brand-new slug flowing to roster/pointers/CLAUDE.md) and a CLI smoke test, with sq check staying clean (US2).
<!-- sq:subtask:ST2:body:end -->

#### Discussion

<!-- sq:subtask:ST2:discussion -->
<!-- sq:subtask:ST2:discussion:end -->
<!-- sq:subtask:ST2:end -->
<!-- sq:subtasks:end -->

## Discussion

<!-- sq:discussion -->
- [2026-06-12T21:29:01Z] Elias Python:
  - Implementation complete. TASK-88 is ready for review.
  - **Resolver** — new private module `src/squads/_roles/_resolver.py` beside the catalog. `resolve_role(slug, squad_dir)` reads `<squad_dir>/.overrides/roles/<slug>.toml` field-wise over `PREDEFINED`: for a bundled slug only the TOML-supplied fields are applied; absent fields inherit from the catalog. For a new slug all four required fields (full_name, title, description, mission) must be present or a `SquadsError` is raised. Slug is always derived from the filename — any slug key in the TOML is silently ignored (ADR §4 — slugs are canonical). Unknown TOML keys are silently dropped for forward compatibility. `resolve_dev_role` wraps `dev_role()` with the same override pattern; explicit `name` kwarg wins over any `full_name` in the TOML.
  - **Wired through** — `activate_role` and `add_dev` in `_services/_roster.py` now call `resolve_role`/`resolve_dev_role` instead of `role_by_slug`/`dev_role` directly. `_refresh_catalog_extra` in `_services/_maintenance.py` and the `author()` fallback in `_services/_base.py` use `resolve_role`. The `sq role show` display path in `_cli/_role.py` also calls `resolve_role` so the catalog card reflects the project-local definition. `full_name` in a TOML seeds the ROLE item's `extra.full_name` channel (T90 naming seam is clean — no further plumbing needed here).
  - **REV-93 F1 addressed** — added an autouse `_reset_engine_state` fixture to `tests/conftest.py` that calls `set_active_squad_dir(None)` and clears `_env_cache` after each test, mirroring the existing `_reset_clock_override`. Engine module-state no longer leaks across tests in order-dependent ways.
  - **Tests** — 20 new tests in `tests/test_role_resolver.py`: bundled baseline (no override unchanged; unknown slug raises; squad_dir=None falls through); field-wise merge (only set fields change; tuple fields; slug in TOML ignored; unknown keys ignored); new-slug admission (full TOML creates role; missing required field raises); malformed TOML raises `SquadsError`; service-level (`activate_role` picks up field override + full_name seed; new-slug creates ROLE item; no-override unchanged; `add_dev` override + explicit-name priority + pool fallback); `resolve_dev_role` unit; two CLI smoke tests (activate with override; activate new slug).
  - Suite: 446 passed, 1 skipped (same 1 as before). `uv run pyright && uv run ruff check . && uv run ruff format --check .` clean. @reviewer ready for review.
- [2026-06-12T21:33:46Z] Paul Reviewer:
  - Reviewed on REV-95 — VERDICT: Approved. @python-dev @tech-lead
  - The role override resolver implements ADR-85 §2 (field-wise merge by slug, project→bundled) and §4 (slugs canonical, non-renamable) correctly. All role-producing paths route through the resolver (activate_role, add_dev, _refresh_catalog_extra, author() fallback, sq role show). Explicit-name precedence for devs is correct. The REV-093 F1 conftest teardown is sound and doesn't mask state bugs. 446 tests green; pyright/ruff clean on the review surface.
  - Two LOW non-blocking findings on REV-95 (F1: new-slug admission admits empty-string required fields; F2: scalar overrides like model=42 aren't type-validated). Optional hardening — your call to address now or defer. Safe to build TASK-89 on this surface as-is.
<!-- sq:discussion:end -->
