---
id: TASK-329
sequence_id: 329
type: task
title: Generic playbook + CLI type registration from spec.items
status: Draft
parent: FEAT-326
author: tech-lead
subentities:
- local_id: ST1
  title: Playbook keyed by str; coverage over work_types(); thin auto-skill fallback
  status: Todo
  story: US3
- local_id: ST2
  title: CLI registers all spec.items types dynamically in deterministic order
  status: Todo
  story: US3
- local_id: ST3
  title: SUBENTITY_* + sq check subtask literal rederive from spec
  status: Todo
  story: US3
created_at: '2026-07-07T14:50:23Z'
updated_at: '2026-07-07T14:52:51Z'
---
<!-- sq:body -->
## Scope

Route every type — built-in and custom — through **one** generic registration
path keyed off `spec.items`, with a **deterministic** iteration order, and
remove today's static-vs-dynamic built-in/custom split. This is ADR-322's "hard
blocker" (the playbook loader) plus the CLI app-build (US3).

## Areas / files

- `_interactions.py` (+ `_interactions/_loader.py`, `_interactions/_models.py`) —
  key the playbook by `str`; delete `_coerce_item_type` / `ItemType(name)`
  coercion; `_check_coverage` requires a playbook entry only for each
  `spec.work_types()` entry. A work type with no bundled playbook entry falls
  back to a thin auto-generated `sq-<type>` skill instead of failing coverage
  (F4).
- `_cli/__init__.py` — register per-type command groups for **all** `spec.items`
  entries dynamically; remove the `_builtin_work_type_names` / `_ORDERED_WORK_TYPES`
  static branch. Ordering must derive from a **deterministic spec order** (define
  and document the order key — not implicit TOML insertion order).
- `_cli/_create.py` — remove the hardcoded work-type tuple; `_make` keyed by
  `str`; register from `spec.items`.
- `_cli/_common.py`, `_cli/_items.py` — drop `ItemType` annotations/parsers →
  `str`.
- `_services/_base.py` — the `SUBENTITY_*` maps derive kind↔type from the spec's
  per-type `subentity_kind`; `sq check`'s residual `"subtask"` literal routes
  through the spec so a dropped/renamed type cleanly loses (not silently keeps)
  its sub-entity checks.

## Done criteria

- The playbook and CLI register every `spec.items` type through one code path, in
  deterministic order; adding a type requires no static-table edit.
- A type absent from the playbook still gets a working thin auto-generated
  `sq-<type>` skill.
- No-override default squad (roster held constant) exposes an identical CLI
  surface and identical generated skills.
- `pyright` + `ruff check` + `ruff format --check` clean.

## Sequencing note

This can land **before** the `ItemType` deletion — `str` keys interoperate with
the surviving `StrEnum`, so the conversion is behavior-preserving on its own. It
leaves the enum-deletion task inheriting `str`-keyed consumers.
<!-- sq:body:end -->

## Subtasks

_Add with `sq task 329 add-subtask "<title>"`; track with `sq task 329 subtask <n> update --status <Status>`._

<!-- sq:summary -->
| Subtask | Status | Assignee | Title | Story |
| --- | --- | --- | --- | --- |
| ST1 | Todo |  | Playbook keyed by str; coverage over work_types(); thin auto-skill fallback | US3 |
| ST2 | Todo |  | CLI registers all spec.items types dynamically in deterministic order | US3 |
| ST3 | Todo |  | SUBENTITY_* + sq check subtask literal rederive from spec | US3 |
<!-- sq:summary:end -->

<!-- sq:subtasks -->

<!-- sq:subtask:ST1 -->
### ST1 — Playbook keyed by str; coverage over work_types(); thin auto-skill fallback

<!-- sq:subtask:ST1:head -->
**Status:** ⚪ Todo
**Implements:** US3 — Playbook + CLI register types generically
<!-- sq:subtask:ST1:head:end -->

<!-- sq:subtask:ST1:body -->
Key the playbook by str and delete the ItemType(name) coercion in _interactions/_loader.py. _check_coverage requires a playbook entry only for each spec.work_types() entry; a work type with no bundled entry falls back to a thin auto-generated sq-<type> skill rather than failing coverage.
<!-- sq:subtask:ST1:body:end -->

#### Discussion

<!-- sq:subtask:ST1:discussion -->
<!-- sq:subtask:ST1:discussion:end -->
<!-- sq:subtask:ST1:end -->

<!-- sq:subtask:ST2 -->
### ST2 — CLI registers all spec.items types dynamically in deterministic order

<!-- sq:subtask:ST2:head -->
**Status:** ⚪ Todo
**Implements:** US3 — Playbook + CLI register types generically
<!-- sq:subtask:ST2:head:end -->

<!-- sq:subtask:ST2:body -->
Register per-type command groups for all spec.items entries dynamically in _cli/__init__.py and _cli/_create.py; remove the _builtin_work_type_names/_ORDERED_WORK_TYPES static branch and the hardcoded work-type tuple. Derive registration order from a documented deterministic spec order, not implicit TOML insertion order.
<!-- sq:subtask:ST2:body:end -->

#### Discussion

<!-- sq:subtask:ST2:discussion -->
<!-- sq:subtask:ST2:discussion:end -->
<!-- sq:subtask:ST2:end -->

<!-- sq:subtask:ST3 -->
### ST3 — SUBENTITY_* + sq check subtask literal rederive from spec

<!-- sq:subtask:ST3:head -->
**Status:** ⚪ Todo
**Implements:** US3 — Playbook + CLI register types generically
<!-- sq:subtask:ST3:head:end -->

<!-- sq:subtask:ST3:body -->
Rederive the SUBENTITY_* kind-to-type maps in _services/_base.py from the spec's per-type subentity_kind, and route sq check's residual 'subtask' literal through the spec so a dropped or renamed type cleanly loses its sub-entity checks instead of silently keeping them.
<!-- sq:subtask:ST3:body:end -->

#### Discussion

<!-- sq:subtask:ST3:discussion -->
<!-- sq:subtask:ST3:discussion:end -->
<!-- sq:subtask:ST3:end -->
<!-- sq:subtasks:end -->

## Discussion

<!-- sq:discussion -->
<!-- sq:discussion:end -->
