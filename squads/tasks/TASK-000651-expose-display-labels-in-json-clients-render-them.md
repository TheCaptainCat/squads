---
id: TASK-651
sequence_id: 651
type: task
title: Expose display labels in JSON + clients render them
status: Draft
parent: FEAT-647
author: tech-lead
refs:
- ADR-646:addresses
subentities:
- local_id: ST1
  title: Add resolved labels to sq workflow types --json
  status: Todo
  story: US3
- local_id: ST2
  title: Extension renders per-type Records buckets with plural labels
  status: Todo
  story: US3
created_at: '2026-07-24T12:55:56Z'
updated_at: '2026-07-24T12:56:59Z'
---
<!-- sq:body -->
Completes FEAT-647: the display labels + resolver exist (label_for/labels_for in _models/_vocab.py, TASK-648 Done), but no --json surface exposes them, so the VS Code Records tree still renders the raw lowercase type (decision/guide) instead of pretty names — the opposite of the Roster tree's "Roles/Skills". Expose the labels in JSON, then have the extension render them.

Scope: additive machine-surface change on `sq workflow types --json` + extension render. No schema/version bump (labels are derived-by-default). Two subtasks, mapped to US3.

Sequencing: ST1 (Python JSON exposure) MUST land before ST2 (TS render) can consume the new field.

Gates: Python side `uv run --all-extras pyright/ruff/pytest`; TS side the extension's own tsc + eslint + prettier + its tests. The coordinating loop owns the full Python suite. Keep the type-aware lint gate intact — the repo pins VS Code TS at 6.0.3; do NOT weaken lint to compile.

Completion: the final gate is a HUMAN visual check on the operator's Windows VS Code dev host — an agent cannot self-verify the rendered tree. So this task completes at InReview for the operator, NOT auto-Done.
<!-- sq:body:end -->

## Subtasks

_Add with `sq task 651 add-subtask "<title>"`; track with `sq task 651 subtask <n> update --status <Status>`._

<!-- sq:summary -->
| Subtask | Status | Assignee | Title | Story |
| --- | --- | --- | --- | --- |
| ST1 | Todo |  | Add resolved labels to sq workflow types --json | US3 |
| ST2 | Todo |  | Extension renders per-type Records buckets with plural labels | US3 |
<!-- sq:summary:end -->

<!-- sq:subtasks -->

<!-- sq:subtask:ST1 -->
### ST1 — Add resolved labels to sq workflow types --json

<!-- sq:subtask:ST1:head -->
**Status:** ⚪ Todo
**Implements:** US3 — Clients render per-type display labels
<!-- sq:subtask:ST1:head:end -->

<!-- sq:subtask:ST1:body -->
Python (JSON exposure). Add the four resolved label forms to each entry of `sq workflow types --json`.

Builder: `_type_catalog` in src/squads/_cli/_workflow_cmd.py — add a `"labels"` key to each row via `labels_for(t, spec)` (returns the dict of all four forms) from _models/_vocab.py. Derived-by-default for bundled types (decision → singular "Decision", plural "Decisions", *_lower forms; acronym/irregular types resolve per their pinned overrides). Extend the frozen TYPE_CATALOG_FIELDS tuple to include "labels" so the contract test tracks it.

Additive only — no key removed, no schema/version bump. Add a test asserting the JSON carries the label forms (e.g. decision's plural == "Decisions").

Gates: uv run --all-extras pyright/ruff; fast pytest selector while iterating (coordinating loop owns the full suite). If you add any module-level constant, run tests/meta.
<!-- sq:subtask:ST1:body:end -->

#### Discussion

<!-- sq:subtask:ST1:discussion -->
<!-- sq:subtask:ST1:discussion:end -->
<!-- sq:subtask:ST1:end -->

<!-- sq:subtask:ST2 -->
### ST2 — Extension renders per-type Records buckets with plural labels

<!-- sq:subtask:ST2:head -->
**Status:** ⚪ Todo
**Implements:** US3 — Clients render per-type display labels
<!-- sq:subtask:ST2:head:end -->

<!-- sq:subtask:ST2:body -->
TypeScript (extension render). Depends on ST1 landing first.

Render each Records per-type bucket header using the type's PLURAL label from the catalog, falling back to the raw type if the label field is absent (for older sq). Match how the Roster tree renders pretty names (metaTreeDataProvider.ts / domain/metaView.ts show "Roles/Skills/Operators").

Touch points:
- clients/vscode/src/sqAdapter.ts — extend the `sq workflow types --json` shape guard (~line 247) for the new `labels` field.
- clients/vscode/src/recordsTreeDataProvider.ts — consume the plural label for the per-type bucket header (fallback to raw type).
Add/adjust a TS test.

Gates: the extension's own tsc + eslint + prettier + its tests. Keep the type-aware lint gate intact — repo pins VS Code TS at 6.0.3; do NOT weaken lint to compile.

Completion note: the rendered tree can only be verified by a human on the operator's Windows VS Code dev host — parent task completes at InReview for the operator.
<!-- sq:subtask:ST2:body:end -->

#### Discussion

<!-- sq:subtask:ST2:discussion -->
<!-- sq:subtask:ST2:discussion:end -->
<!-- sq:subtask:ST2:end -->
<!-- sq:subtasks:end -->

## Discussion

<!-- sq:discussion -->
<!-- sq:discussion:end -->
