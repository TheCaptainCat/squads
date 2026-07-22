---
id: TASK-595
sequence_id: 595
type: task
title: Expose type category on sq workflow types --json catalog
status: InReview
parent: FEAT-570
author: tech-lead
priority: high
created_at: '2026-07-22T13:00:53Z'
updated_at: '2026-07-22T15:38:03Z'
---
<!-- sq:body -->
Implements FEAT-570 US1 — the wire enabler. Expose each type's `category` on the `sq workflow types --json` catalog so both UI clients read the roster/work/records split from one source instead of re-deriving it. Build this FIRST: TASK-598..602 (TUI + VS Code) consume it.

## Scope
- `src/squads/_cli/_workflow_cmd.py`: add `"category"` to `TYPE_CATALOG_FIELDS` and emit it in each `_type_catalog` row (`spec.items[t].category`, one of `roster|work|records`). Keep the existing `reserved` boolean (it is `category == "roster"`) — do not remove it; clients migrate on their own tasks.
- Optionally surface a Category column in the human `sq workflow types` table.
- The `TYPE_CATALOG_FIELDS` tuple is contract-tested (a test asserts the CLI never drifts from the declared field set) — update that contract test so the frozen key set includes `category`.

## Acceptance
- `sq workflow types --json` emits `{type, order, prefix, reserved, category, fields}` for every declared type, present-never-omitted, key set stable across rows.
- Bundled spec: decision/contract/guide -> `records`, epic/feature/task/bug/review -> `work`, role/skill/operator -> `roster`.
- Contract/catalog tests updated and green.

## Gates
`uv run --all-extras pyright && uv run --all-extras ruff check . && uv run --all-extras ruff format --check . && uv run --all-extras pytest` (the `tui` extra must be present). Leave `sq check` clean.
<!-- sq:body:end -->

## Subtasks

_Add with `sq task 595 add-subtask "<title>"`; track with `sq task 595 subtask <n> update --status <Status>`._

<!-- sq:summary -->
<!-- sq:summary:end -->

<!-- sq:subtasks -->
<!-- sq:subtasks:end -->

## Discussion

<!-- sq:discussion -->
- [2026-07-22T13:28:16Z] Elias Python:
  - Added category to sq workflow types --json catalog (_workflow_cmd.py: TYPE_CATALOG_FIELDS, _type_catalog, human Category column) + updated contract test, golden, and human-table test. Gates green (pyright/ruff/tests).
- [2026-07-22T15:38:03Z] Olivia Lead:
  - Carried by FEAT-605: this work (category on sq workflow types --json) is ADR-604-compatible and orthogonal to the role-object change. The FEAT-605 implementer keeps this code as-is; it lands with FEAT-605 from the current tree. Status left InReview for the manager to reconcile once FEAT-605 lands.
<!-- sq:discussion:end -->
