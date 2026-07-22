---
id: TASK-596
sequence_id: 596
type: task
title: Category-aware default visibility + empty-view hint (list/tree)
status: InReview
parent: FEAT-570
author: tech-lead
priority: medium
created_at: '2026-07-22T13:00:53Z'
updated_at: '2026-07-22T13:28:24Z'
---
<!-- sq:body -->
Implements FEAT-570 US1 (folds REV-565 F9). Make the default (non-`--all`) visibility of `sq list`/`sq tree` category-aware, and add an empty-view hint so a hidden-but-not-empty view never looks broken.

## Scope
- Add ONE spec-level predicate (e.g. `WorkflowSpec.hidden_by_default(item_type, status)` or `visible_by_default(item)`) as the single source of truth, exposed on the `_workflow/__init__.py` facade for the TUI/CLI:
  - `work` -> hidden iff the status is terminal (today's `is_open` behaviour — byte-identical).
  - `records` -> visible while final-but-live (e.g. `Accepted`, `Published`); hidden only once retired (`Superseded`, `Deprecated`, `Cancelled`).
  - `roster` -> unchanged.
- Detect "retired" for records via the status semantic `role` marker (`StatusSpec.role`), NOT a hardcoded status-name list. Today only `Superseded` carries `role = "superseded"`; `Deprecated`/`Cancelled` carry none. Design decision for this task: extend the retired-role vocabulary (e.g. give `Deprecated` a role marker and treat `Cancelled` as retired) so the rule is spec-driven. Keep the change scoped to the bundled spec's status roles; work-category output must stay byte-identical.
- Route both call sites through the predicate: `src/squads/_cli/_main.py::list_items` (the `if not (all_ or status)` filter) and `src/squads/_services/_base.py::tree_view` (the `include_closed` candidate filter). `is_open` stays as-is for other callers.
- Empty-view hint: when a default view is empty (or all-shown after hiding) because terminal `work` items were hidden, print a dim hint like "N closed items hidden — use --all" on both `sq list` and `sq tree` instead of the bare "no items". Count only the items the default filter dropped.

## Acceptance
- A migrated squad with `Accepted` ADRs and `Done` features shows the ADRs by default and hides the features, without `--all`.
- `work`/`roster` default visibility unchanged; bundled-spec regression byte-identical apart from records staying visible.
- Empty/sparse default views print the closed-count hint.
- Service + CLI tests for records-visible-by-default, records-retired-hidden, and the hint.

## Gates
`uv run --all-extras pyright && uv run --all-extras ruff check . && uv run --all-extras ruff format --check . && uv run --all-extras pytest` (the `tui` extra must be present). Leave `sq check` clean.
<!-- sq:body:end -->

## Subtasks

_Add with `sq task 596 add-subtask "<title>"`; track with `sq task 596 subtask <n> update --status <Status>`._

<!-- sq:summary -->
<!-- sq:summary:end -->

<!-- sq:subtasks -->
<!-- sq:subtasks:end -->

## Discussion

<!-- sq:discussion -->
- [2026-07-22T13:28:24Z] Elias Python:
  - Added WorkflowSpec.hidden_by_default(item_type, status) (+ RETIRED_STATUS_ROLES, role=retired on Deprecated/Cancelled in default_workflow.toml); wired into tree_view's candidate filter and sq list's default gate, plus the closed-count empty-view hint on both list and tree. work/roster stay byte-identical (proven by a dedicated unit test); records now stay visible while final-but-live and hide only when retired. Gates green; sq check clean.
<!-- sq:discussion:end -->
