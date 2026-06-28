---
id: FEAT-000208
sequence_id: 208
type: feature
title: De-type Item model from enums to str + reify TypeSpec capability flags
status: Draft
parent: EPIC-000206
author: product-owner
refs:
- FEAT-000207:depends-on
subentities:
- local_id: US1
  title: As a maintainer, I want Item type/status to be str-typed so unknown values
    don't raise at load time
  status: Todo
- local_id: US2
  title: As a maintainer, I want engine spine checks replaced by TypeSpec flags so
    custom types can declare their own semantics
  status: Todo
created_at: '2026-06-25T13:17:57Z'
updated_at: '2026-06-25T13:22:19Z'
---
<!-- sq:body -->
## What this delivers

F1 externalizes the workflow spec but leaves the Pydantic models still typed on `ItemType` and `Status` enums. Those enum-typed fields are the obstacle that makes the vocabulary closed: frontmatter with an unknown `type` or `status` value raises at model construction time, so custom vocabulary literally cannot be read.

F2 removes that obstacle. It widens `Item.type` and `Item.status` (and sub-entity status) from enum types to `str`, and shifts validation from "enum construction raises" to "service-boundary validation against the loaded `WorkflowSpec`". It also eliminates the ~20 hardcoded `is ItemType.X` identity checks in the engine — the places where Python code "knows" it is handling a task, decision, or skill specifically — by reifying each semantic into a declared capability flag on `TypeSpec`.

**This is the highest-risk feature in the epic.** The pyright/typing inversion is irreversible and pervasive: we are deliberately trading compile-time enum exhaustiveness for load-time spec validation. That trade-off is recorded in the epic and is a conscious choice. Mitigations: strong `WorkflowSpec.validate()` (fail-closed on load) and `sq workflow lint` (F3).

**This feature is gated by the spike.** The throwaway F1+F2 spike described in EPIC-000206 must prove that `uv run pyright && ruff && pytest` stay green with the de-typed models and the ~20 reified checks before this feature is committed to implementation.

## Scope

- Widen `Item.type: ItemType` → `Item.type: str` and `Item.status: Status` → `Item.status: str`; same for `SubEntity.status`. Frontmatter round-trips losslessly (existing item files need no rewrite — every current value is a valid string).
- Move validation from Pydantic field construction to the service boundary: `open_service` / `ItemStore.load` checks that item type/status values are known to the loaded `WorkflowSpec`.
- Identify and reify all ~20 hardcoded `is ItemType.X` / `is ItemType.TASK` / `is ItemType.DECISION` etc. identity checks in `_maintenance.py`, `_items.py`, `_common.py`, `_backends/`, `_paths.py`. Each becomes a declared boolean flag or named capability on `TypeSpec` (e.g. `is_meta`, `enforce_parent`, `ref_rules`, `subentity_kind`). The engine asks `spec.type_spec(t).enforce_parent` instead of `item.type is ItemType.TASK`.
- Update `parse_type` / `parse_status` in `_cli/_common.py` to iterate `spec.managed_types()` instead of `list(ItemType)` / `list(Status)`.
- Demote the `ItemType` and `Status` enums: they become seed-data constants used to generate the bundled default TOML (F1); they are no longer the runtime vocabulary. They may be retained temporarily as string constants for internal reference during the transition.
- All 152 `ItemType.*` and 21 `Status.*` references are resolved; pyright reports zero errors in strict mode.

## Dependencies

Requires F1 (FEAT-000207). The `WorkflowSpec` must exist and be loaded before validation can move to the service boundary.

## Acceptance criteria

1. `Item.type` and `Item.status` are `str`-typed; Pydantic construction no longer raises on unknown values from frontmatter.
2. All ~20 `is ItemType.X` / `is Status.X` identity checks in the engine are eliminated; each is replaced by a `TypeSpec` capability flag query.
3. `parse_type` and `parse_status` derive their valid-value sets from the loaded spec, not enum iteration.
4. The F1 golden test remains green — default behavior is unchanged.
5. `uv run pyright` passes in strict mode with zero errors.
6. `uv run ruff check .` passes clean.
7. Full test suite (`uv run pytest`) passes with no regressions.
8. No existing `.md` item file requires rewriting (frontmatter round-trips as-is).
<!-- sq:body:end -->

## User Stories

_Add with `sq feature 208 add-story "As a <role>, I want … so that …"`; track with `sq feature 208 story <n> update --status <Status>`._

<!-- sq:summary -->
| Story | Status | Assignee | Title |
| --- | --- | --- | --- |
| US1 | Todo |  | As a maintainer, I want Item type/status to be str-typed so unknown values don't raise at load time |
| US2 | Todo |  | As a maintainer, I want engine spine checks replaced by TypeSpec flags so custom types can declare their own semantics |
<!-- sq:summary:end -->

<!-- sq:stories -->

<!-- sq:story:US1 -->
### US1 — As a maintainer, I want Item type/status to be str-typed so unknown values don't raise at load time

<!-- sq:story:US1:head -->
**Status:** ⚪ Todo
<!-- sq:story:US1:head:end -->

<!-- sq:story:US1:body -->
As a squads maintainer, I want `Item.type` and `Item.status` to be `str`-typed fields validated against the loaded `WorkflowSpec` at the service boundary, so that frontmatter with a future custom type or status value round-trips losslessly instead of raising at Pydantic construction.

**Acceptance:** Pydantic model construction accepts any string; unknown values surface as a spec-validation error with a clear message at service init, not a model parse error. Existing item files load unchanged.
<!-- sq:story:US1:body:end -->

#### Discussion

<!-- sq:story:US1:discussion -->
<!-- sq:story:US1:discussion:end -->
<!-- sq:story:US1:end -->

<!-- sq:story:US2 -->
### US2 — As a maintainer, I want engine spine checks replaced by TypeSpec flags so custom types can declare their own semantics

<!-- sq:story:US2:head -->
**Status:** ⚪ Todo
<!-- sq:story:US2:head:end -->

<!-- sq:story:US2:body -->
As a squads maintainer, I want every hardcoded `is ItemType.TASK` / `is ItemType.DECISION` / `is ItemType.SKILL` identity check in the engine replaced by a declared `TypeSpec` capability flag query, so that the engine's behavior is driven by spec declarations rather than compiled-in type knowledge.

**Acceptance:** zero `is ItemType.X` pattern matches remain in src/squads; each semantic (enforce_parent, fix-ref rule, supersede warning, is_meta) has a named flag on `TypeSpec`; the bundled default spec sets those flags to reproduce today's behavior exactly; `uv run pyright` strict passes.
<!-- sq:story:US2:body:end -->

#### Discussion

<!-- sq:story:US2:discussion -->
<!-- sq:story:US2:discussion:end -->
<!-- sq:story:US2:end -->
<!-- sq:stories:end -->

## Discussion

<!-- sq:discussion -->
<!-- sq:discussion:end -->
