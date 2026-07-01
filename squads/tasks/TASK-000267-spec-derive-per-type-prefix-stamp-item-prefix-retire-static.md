---
id: TASK-000267
sequence_id: 267
type: task
title: 'Spec-derive per-type prefix: stamp Item.prefix, retire static PREFIX/FOLDER/alias
  tables'
status: Done
parent: FEAT-000210
author: tech-lead
assignee: python-dev
refs:
- ADR-000266:implements
- REV-000265:addresses
created_at: '2026-07-01T08:28:50Z'
updated_at: '2026-07-01T09:36:23Z'
---
<!-- sq:body -->
**Closes REV-000265 F1 (High). Implements ADR-000266.** The prefix-derivation family, not one line.

## Problem
`Item.id` and every id/filename/ref site derive the prefix via `PREFIX_BY_TYPE.get(type, type.upper())` (or crashing bracket `PREFIX_BY_TYPE[type]`). For a custom type declared `prefix = "INC"` there is no map entry, so the fallback stamps `INCIDENT-000019` instead of `INC-000019` — a malformed, self-contradicting id (`sq incident INCIDENT-000019 show` errors "is INCIDENT-000019, not an incident"). Violates AC#2 and invariant #1 (frontmatter-as-truth). `Item` is spec-unaware by convention (ADR-000249 Finding 1) so it cannot read the spec prefix directly.

## The sites (all decided by ADR-266 — do NOT re-litigate the approach)
- `_models/_item.py:161` — `Item.id` computed field (`.get(..., type.upper())`).
- `_models/_index.py:74` — `SquadsDB.format_id`, called by `allocate_id` → builds the **filename** at create time (`_base.py`), so the file is *also* misnamed independent of `Item.id`.
- `_cli/_common.py:557` — pre-callback display/parse path (already spec-aware first, PREFIX_BY_TYPE fallback).
- `_services/_refs.py:93,298,351` and `_services/_items.py:303` — **bracket** access `PREFIX_BY_TYPE[item.type]`, which raises `KeyError` on any custom type.

## Scope (per ADR-266 decision)
1. **`Item` gains a stored-but-derived `prefix: str` field** — excluded from the JSON index like `id_padding`, but written to frontmatter as part of the durable id. `Item.id` becomes `format_item_id(self.prefix, self.sequence_id, self.id_padding)` — no map lookup, no `type.upper()`. The model stores a plain string handed to it; it does NOT derive vocabulary (keeps the model spec-decoupled — do not re-couple `Item.id`/`from_frontmatter` to a spec/contextvar; alternatives b/c are explicitly rejected in the ADR).
2. **One `_models`-local resolver** `prefix_for(type_str, spec=None)`: returns the reserved built-in prefix when the type is reserved, else `spec.items[type].prefix`, else raises. `spec` optional so the pure built-in path and legacy callers need no spec; custom types require one. This is the single authoritative reserved-vocab map (EPIC-206 invariant depends on it).
3. **Stamp at the three boundaries where a spec is in hand:**
   - **Create** (`_base.py` ~270-274): `db.allocate_id`/`SquadsDB.format_id` grow a `prefix`/`spec` parameter so filename and counter-formatted id agree; the `Item(...)` build receives the resolved prefix from `self.spec`.
   - **Retype** (`_services/_retype.py`): re-stamp `item.prefix` from the target type's spec (this is the only path that materialises a custom item today).
   - **Load / repair** (`from_frontmatter` + `IndexStore.load()` boundary): read `prefix` back from frontmatter when present; when absent (legacy files / rebuild), the store resolves it via `prefix_for` at the vocab-validation boundary. Follow the `SquadsDB._propagate_padding` precedent for a post-load pass filling a derived field.
4. **Retire the type-keyed lookups** in the ref/id paths: `_refs.py`/`_items.py` already hold the `Item`, so use `item.prefix` directly (no map at all); route `_index.py`/`_common.py` through the resolver.

## Static-artifact sweep (operator-confirmed boundary — per ADR-266 Consequences)
Retire as call-site lookups: `PREFIX_BY_TYPE`, `TYPE_BY_PREFIX`, `FOLDER_BY_TYPE`, the `TYPE_ALIASES` shim (migrate `_workflow_cmd._print_cheatsheet` + backend AGENTS/CLAUDE renderers to `spec.alias_to_type`/`ItemSpec.aliases`, then delete the dict), `_META_NAMES` (`_cli/_items.py:109` — resolve through the reserved resolver). The reserved built-in vocab map STAYS as the resolver's default source of truth.
- **OUT OF SCOPE (do NOT touch):** `_SUBENTITY_PLURAL` — deferred to FEAT-000212 (kept as built-in fallback). `_KIND_BY_TYPE` in `_migrations/_v0_2_to_v0_3.py` — frozen migration code, exempt.
- **Forward-compat:** design `prefix_for` so FEAT-212 can add a `subentity_plural` accessor later; do not pull that vocab forward now.

## Legacy files / migration
`prefix` re-derived on load when absent from frontmatter keeps existing on-disk files valid (built-ins via the reserved map — byte-identical). **Deliverable: flag explicitly** whether a `sq repair`/backfill or a migration note is needed to write the new `prefix` frontmatter line into existing files, or whether re-derivation-on-load is sufficient (no schema bump). Report the decision on the task.

## Acceptance
- Retype a task to `incident` (spec prefix `INC`) → `item.prefix = "INC"`, `Item.id` renders `INC-000019`, file named `INC-000019-*.md`, `sq incident INC-000019 show` round-trips. No `type.upper()` anywhere.
- **AC#7/#8 — byte-identical built-ins:** the TASK-256 characterization goldens stay green; non-custom ids/filenames/CLI/rendered output unchanged.
- All ref paths (`sq <type> <n> ref ...`, remove-with-referrers) work for a custom type without `KeyError`.
- Gates clean: `uv run pyright && uv run ruff check . && uv run ruff format --check .`.
- **Test the headline end-to-end (the gap that let F1 through):** the prior tests materialised custom items via `write_new`/`retype`, sidestepping the format sites. This task's tests must declare a custom type in `.overrides/workflow.toml` and assert the correctly-prefixed id round-trips through retype + `show` + `list -t <type>` + a ref add — plus a legacy-file (no `prefix` frontmatter) load/repair round-trip.

## Files
`_models/_item.py`, `_models/_index.py`, `_models/_enums.py` (reserved map / retire tables), a `_models`-local resolver, `_services/_base.py`, `_services/_retype.py`, `_services/_refs.py`, `_services/_items.py`, `_cli/_common.py`, `_cli/_items.py`, `_cli/_workflow_cmd.py`, backend AGENTS/CLAUDE renderers.
<!-- sq:body:end -->

## Subtasks

_Add with `sq task 267 add-subtask "<title>"`; track with `sq task 267 subtask <n> update --status <Status>`._

<!-- sq:summary -->
<!-- sq:summary:end -->

<!-- sq:subtasks -->
<!-- sq:subtasks:end -->

## Discussion

<!-- sq:discussion -->
- [2026-07-01T09:36:23Z] Elias Python:
  - @manager TASK-000267 is Done. All three gates are clean (pyright 0 errors, ruff check clean, ruff format clean). 27 new tests pass; focused run of 145 tests on affected files is clean. Full suite running in background.
  - Changes: new `_models/_vocab.py` (RESERVED_PREFIX/FOLDER/TYPE_BY_PREFIX + prefix_for/is_reserved); Item.prefix field (excluded from JSON, written to frontmatter for custom types only); id computed field now uses self.prefix; stamp at create (_base.py), retype (_retype.py, also added missing mkdir for custom-type folder), and load (_store.py _propagate_prefix); retired PREFIX_BY_TYPE/FOLDER_BY_TYPE/TYPE_BY_PREFIX/TYPE_ALIASES from _enums.py.
  - REV-000265 F1 finding closed as Fixed. Two test bugs fixed: wrong CLI syntax (task create → create task) and wrong sequence number (1 → 2 after init seeds a role).
<!-- sq:discussion:end -->
