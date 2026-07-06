---
id: TASK-223
sequence_id: 223
type: task
title: Role catalog loader with fail-closed validation; rewire _catalog.py onto loaded
  spec
status: Done
parent: FEAT-219
author: tech-lead
subentities:
- local_id: ST1
  title: load_role_catalog via importlib.resources/tomllib + fail-closed validation
  status: Todo
  story: US1
- local_id: ST2
  title: Rewire _catalog.py to shims over the loaded spec; keep dev_role logic + extra
    bridge
  status: Todo
  story: US1
created_at: '2026-06-26T07:35:29Z'
updated_at: '2026-07-06T15:20:55Z'
---
<!-- sq:body -->
## Goal

Implement `load_role_catalog()` (reads bundled `roles.toml`, validates fail-closed, caches a
singleton) and rewire `_catalog.py` consumers to source from the loaded spec — behavior
BYTE-IDENTICAL, zero call-site churn. `dev_role()` logic and the `to_extra`/`from_extra` ExtraKey
bridge stay in Python; only data moves out.

Sequence: **second** — depends on TASK-222 (models + TOML). TASK-224 (golden-lock) gates on this
being behavior-preserving.

## What to build

- **Loader** `load_role_catalog() -> RoleCatalogSpec`: read via
  `importlib.resources.files("squads._roles") / "roles.toml"` + stdlib `tomllib`, parse into the
  models, run validation, cache a module-level singleton (same lifecycle as `WorkflowSpec`). A
  corrupt/invalid bundled catalog raises `SquadsError` — fail closed (subclass of `SquadsError`).
- **Fail-closed validation** (ADR §3, raises `SquadsError`):
  1. unique slugs across all roles;
  2. required fields present and non-empty per role: `slug`, `full_name`, `title`, `description`,
     `mission`;
  3. at most one `is_default = true` (exactly one — manager — in the default);
  4. bundles referential integrity: every slug in any bundle is a defined role; the `all` bundle
     equals the full role set;
  5. dev pool well-formed: `name_pool` non-empty and unique; `model`/`color` non-empty strings;
  6. `model`, if set, is one of `sonnet`/`opus`/`haiku`/`inherit`.
- **Rewire `_catalog.py` as thin shims over the loaded spec** (preserve the public surface so
  consumers don't churn): `PREDEFINED` → `spec.roles`, `BUNDLES` → `spec.bundles`, `DEV_NAME_POOL` →
  `spec.dev.name_pool`; `role_by_slug()` / `resolve_roles()` read the spec.
- **Keep `dev_role()` LOGIC in Python:** slug = `<slugify(tech)>-dev`, surname = tech titlecased,
  name-by-seq from the pool — unchanged; it only sources `name_pool` / default `model` / `color` from
  `spec.dev`. The `RoleDef` dataclass either becomes the `RoleSpec` model directly or a trivial
  adapter; **`to_extra` / `from_extra` move onto/alongside it unchanged** (the ROLE-item frontmatter
  `X.*` extra-key mapping is behavior, not data).
- Retire the hardcoded `RoleDef` instances (no remaining literals outside the TOML; `_catalog.py`
  reduced to shim + logic). Keep the import graph acyclic; no `from __future__ import annotations`.

## Design constraints (ADR-221)

- §3 loader/validation/rewiring; data moves out, logic + extra-key bridge stay in Python. No backend/
  renderer change — how roles are written to `.claude`/AGENTS.md is unchanged; only the source of role
  data moves.

## Acceptance

1. `load_role_catalog()` loads + validates the bundled catalog; invalid catalog raises `SquadsError`.
2. `_catalog.py` is retired to a thin shim over the loaded spec; no hardcoded `RoleDef` instances
   remain outside the TOML; `dev_role()` and the dev-name pool are spec-derived. (FEAT-219 AC#3/#4,
   US1.)
3. All existing tests pass unchanged — no behavioral difference for role resolution, roster, or skill
   generation. (AC#5.)
4. `uv run pyright && uv run ruff check . && uv run pytest` green. (Golden lock added in TASK-224.)
<!-- sq:body:end -->

## Subtasks

_Add with `sq task 223 add-subtask "<title>"`; track with `sq task 223 subtask <n> update --status <Status>`._

<!-- sq:summary -->
| Subtask | Status | Assignee | Title | Story |
| --- | --- | --- | --- | --- |
| ST1 | Todo |  | load_role_catalog via importlib.resources/tomllib + fail-closed validation | US1 |
| ST2 | Todo |  | Rewire _catalog.py to shims over the loaded spec; keep dev_role logic + extra bridge | US1 |
<!-- sq:summary:end -->

<!-- sq:subtasks -->

<!-- sq:subtask:ST1 -->
### ST1 — load_role_catalog via importlib.resources/tomllib + fail-closed validation

<!-- sq:subtask:ST1:head -->
**Status:** ⚪ Todo
**Implements:** US1 — As a maintainer, I want role definitions loaded from roles.toml so adding a role needs no Python edit
<!-- sq:subtask:ST1:head:end -->

<!-- sq:subtask:ST1:body -->
Covers `load_role_catalog()`: read the bundled `roles.toml` via `importlib.resources` + stdlib `tomllib`, parse into the models, and cache a module-level singleton (same lifecycle as `WorkflowSpec`). Includes the fail-closed validation (raises `SquadsError`): unique slugs, required non-empty fields per role, at most one `is_default`, bundle referential integrity (`all` == full role set), dev pool well-formed, and `model` in the sonnet/opus/haiku/inherit whitelist. (US1)
<!-- sq:subtask:ST1:body:end -->

#### Discussion

<!-- sq:subtask:ST1:discussion -->
<!-- sq:subtask:ST1:discussion:end -->
<!-- sq:subtask:ST1:end -->

<!-- sq:subtask:ST2 -->
### ST2 — Rewire _catalog.py to shims over the loaded spec; keep dev_role logic + extra bridge

<!-- sq:subtask:ST2:head -->
**Status:** ⚪ Todo
**Implements:** US1 — As a maintainer, I want role definitions loaded from roles.toml so adding a role needs no Python edit
<!-- sq:subtask:ST2:head:end -->

<!-- sq:subtask:ST2:body -->
Covers rewiring `_catalog.py` into thin shims over the loaded spec so no call site churns: `PREDEFINED` → `spec.roles`, `BUNDLES` → `spec.bundles`, `DEV_NAME_POOL` → `spec.dev.name_pool`, with `role_by_slug()`/`resolve_roles()` reading the spec. Retires the hardcoded `RoleDef` literals while keeping `dev_role()` LOGIC (slug/surname/name-by-seq) and the `to_extra`/`from_extra` ExtraKey bridge in Python — only the data moves out. Import graph stays acyclic. (US1)
<!-- sq:subtask:ST2:body:end -->

#### Discussion

<!-- sq:subtask:ST2:discussion -->
<!-- sq:subtask:ST2:discussion:end -->
<!-- sq:subtask:ST2:end -->
<!-- sq:subtasks:end -->

## Discussion

<!-- sq:discussion -->
<!-- sq:discussion:end -->
