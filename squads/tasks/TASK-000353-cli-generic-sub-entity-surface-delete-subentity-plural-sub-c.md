---
id: TASK-353
sequence_id: 353
type: task
title: 'CLI: generic sub-entity surface; delete _SUBENTITY_PLURAL/_SUB_COLS'
status: Draft
parent: FEAT-212
author: tech-lead
refs:
- TASK-351:depends-on
- TASK-352:depends-on
subentities:
- local_id: ST1
  title: add-<kind> verb built dynamically from spec; e.g. incident add-action
  status: Todo
  story: US1
created_at: '2026-07-09T21:31:33Z'
updated_at: '2026-07-09T21:33:44Z'
---
<!-- sq:body -->
ADR-348 §5 CLI half + FEAT-212 AC1/AC2/AC3: build the whole sub-entity CLI surface generically from the resolved SubentityKindSpec, and delete the last static per-type vocabulary artifacts. This is where `sq incident <n> add-action ...` starts working with no code change.

## Scope

Delete `_SUBENTITY_PLURAL` (FEAT-212's named deliverable — the last static per-type vocab artifact; op-pierre confirmed the boundary) and `_SUB_COLS`. In `build_item_app(item_type)`, resolve the kind via `spec.item_subentity_kind(item_type)` -> `SubentityKindSpec` and build the surface from it.

`add-<kind>`: base flags (title, --assignee, -m/--message, --file, --json) + one `--<field-code>` option per declared field (ADR-323-derived, same as item-level field flags) + `--story` iff `maps_parent_story`. Replaces the three hand-written _register_add closures.

`<plural>` list verb + the nested `<kind> <n> ...` subgroup (show/update/body/comment) built the same generic way; `update` derives its `--<field-code>` flags identically. Replaces _register_update's per-kind branches.

All verbs call the **public kind-taking generic service methods** (TASK-351) instead of `getattr(svc, f"list_{plural}"|f"get_{kind}"|f"set_{kind}_body")`. The list table consumes the shared field-driven column derivation from TASK-352.

Use the new `subentity_plural` resolver accessor (add it to the resolver surface if not already present) for the plural vocab; no _SUBENTITY_PLURAL fallback remains.

## Files owned

- src/squads/_cli/_items.py (_SUBENTITY_PLURAL + _SUB_COLS deleted; _register_subentity/_register_add/_register_update/_register_sub_verbs/_sub_table generic field-driven; getattr-per-kind dispatch replaced with the public service surface)

## Acceptance

- AC1: a custom type declaring a custom kind gets `sq <type> <n> add-<kind> ...` + a summary table with derived columns, no code change.

- AC2: update/body/comment resolve the kind from the spec for built-in and custom kinds.

- AC3: _SUBENTITY_PLURAL deleted; plural vocab comes from the subentity_plural resolver accessor.

- AC4: built-in story/subtask/finding CLI verbs, flags, and output unchanged.

- Full suite green (add a CLI smoke test for a custom-kind add-<kind> per CLAUDE.md).

## Depends on

TASK-351 (public kind-taking service surface) and TASK-352 (shared column derivation); transitively TASK-349.
<!-- sq:body:end -->

## Subtasks

_Add with `sq task 353 add-subtask "<title>"`; track with `sq task 353 subtask <n> update --status <Status>`._

<!-- sq:summary -->
| Subtask | Status | Assignee | Title | Story |
| --- | --- | --- | --- | --- |
| ST1 | Todo |  | add-<kind> verb built dynamically from spec; e.g. incident add-action | US1 |
<!-- sq:summary:end -->

<!-- sq:subtasks -->

<!-- sq:subtask:ST1 -->
### ST1 — add-<kind> verb built dynamically from spec; e.g. incident add-action

<!-- sq:subtask:ST1:head -->
**Status:** ⚪ Todo
**Implements:** US1 — As a project admin, I want to define custom sub-entity kinds for my custom types in TOML
<!-- sq:subtask:ST1:head:end -->

<!-- sq:subtask:ST1:body -->
_Describe this subtask here — free-form paragraphs or bullet lists._
<!-- sq:subtask:ST1:body:end -->

#### Discussion

<!-- sq:subtask:ST1:discussion -->
<!-- sq:subtask:ST1:discussion:end -->
<!-- sq:subtask:ST1:end -->
<!-- sq:subtasks:end -->

## Discussion

<!-- sq:discussion -->
<!-- sq:discussion:end -->
