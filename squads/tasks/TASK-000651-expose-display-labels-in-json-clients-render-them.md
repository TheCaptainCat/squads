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
- local_id: ST3
  title: Route Work tree group-by-type headers through the shared resolver
  status: Todo
  story: US3
- local_id: ST4
  title: De-hardcode Roster tree bucket labels from the catalog
  status: Todo
  story: US3
created_at: '2026-07-24T12:55:56Z'
updated_at: '2026-07-24T13:49:08Z'
---
<!-- sq:body -->
Completes FEAT-647: the display labels + resolver exist (label_for/labels_for in _models/_vocab.py, TASK-648 Done), but no --json surface exposes them, so the VS Code trees render the raw lowercase type instead of pretty names. Expose the labels in JSON, then STANDARDIZE the extension's per-type group headers onto one spec-driven source across all three trees.

Today the grouping labels come from three inconsistent sources:
- Roster tree hard-codes them in clients/vscode/src/domain/reservedTypes.ts (META_BUCKETS: role→Roles, skill→Skills, operator→Operators as TS literals).
- Work tree groups by raw type (clients/vscode/src/domain/listView.ts, ~line 131 groupDisplayNode).
- Records tree uses the raw type.

`sq workflow types --json` already lists every type including the roster ones (role/skill/operator, category=roster), so ST1's label forms cover all three trees.

Scope: additive machine-surface change on `sq workflow types --json` + a single shared TS label resolver routed through every per-type group header. No schema/version bump (labels are derived-by-default). Subtasks mapped to US3.

Sequencing: ST1 (Python JSON exposure) MUST land before the TS subtasks can consume the new field.

Gates: Python side `uv run --all-extras pyright/ruff/pytest`; TS side the extension's own tsc + eslint + prettier + its tests. The coordinating loop owns the full Python suite. Keep the type-aware lint gate intact — the repo pins VS Code TS at 6.0.3; do NOT weaken lint to compile.

Completion: the final gate is a HUMAN visual check on the operator's Windows VS Code dev host — an agent cannot self-verify the rendered trees. So this task completes at InReview for the operator, NOT auto-Done.
<!-- sq:body:end -->

## Subtasks

_Add with `sq task 651 add-subtask "<title>"`; track with `sq task 651 subtask <n> update --status <Status>`._

<!-- sq:summary -->
| Subtask | Status | Assignee | Title | Story |
| --- | --- | --- | --- | --- |
| ST1 | Todo |  | Add resolved labels to sq workflow types --json | US3 |
| ST2 | Todo |  | Extension renders per-type Records buckets with plural labels | US3 |
| ST3 | Todo |  | Route Work tree group-by-type headers through the shared resolver | US3 |
| ST4 | Todo |  | De-hardcode Roster tree bucket labels from the catalog | US3 |
<!-- sq:summary:end -->

<!-- sq:subtasks -->

<!-- sq:subtask:ST1 -->
### ST1 — Add resolved labels to sq workflow types --json

<!-- sq:subtask:ST1:head -->
**Status:** ⚪ Todo
**Implements:** US3 — Clients render per-type display labels
<!-- sq:subtask:ST1:head:end -->

<!-- sq:subtask:ST1:body -->
Python (JSON exposure). Add the four resolved label forms to each entry of `sq workflow types --json` — covers every type, including the roster ones (role/skill/operator, category=roster), so all three trees can consume it.

Builder: `_type_catalog` in src/squads/_cli/_workflow_cmd.py — add a `"labels"` key to each row via `labels_for(t, spec)` (returns the dict of all four forms) from _models/_vocab.py. Derived-by-default for bundled types (decision → singular "Decision", plural "Decisions"; role → "Roles" etc.; acronym/irregular types resolve per their pinned overrides). Extend the frozen TYPE_CATALOG_FIELDS tuple to include "labels" so the contract test tracks it.

Additive only — no key removed, no schema/version bump. Add a test asserting the JSON carries the label forms (e.g. decision plural == "Decisions", role plural == "Roles").

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
TypeScript. Depends on ST1 landing first. Shared resolver + Records tree.

Add ONE shared TS helper that resolves a type's PLURAL display label from the `sq workflow types --json` catalog (`labels.plural`), falling back to the raw type when the field is absent (older sq). This helper becomes the single source of truth every per-type group header routes through (ST3, ST4 reuse it).

- Extend the `sq workflow types --json` shape guard in clients/vscode/src/sqAdapter.ts (~line 247) for the new `labels` field.
- Route the Records tree bucket headers (clients/vscode/src/recordsTreeDataProvider.ts) through the shared helper.
- Add TS tests for the shared resolver (pinned + derived-fallback + raw-fallback) and the Records header.

Gates: extension tsc + eslint + prettier + its tests. Keep the type-aware lint gate intact (TS pinned 6.0.3; do NOT weaken lint to compile).
<!-- sq:subtask:ST2:body:end -->

#### Discussion

<!-- sq:subtask:ST2:discussion -->
<!-- sq:subtask:ST2:discussion:end -->
<!-- sq:subtask:ST2:end -->

<!-- sq:subtask:ST3 -->
### ST3 — Route Work tree group-by-type headers through the shared resolver

<!-- sq:subtask:ST3:head -->
**Status:** ⚪ Todo
**Implements:** US3 — Clients render per-type display labels
<!-- sq:subtask:ST3:head:end -->

<!-- sq:subtask:ST3:body -->
TypeScript. Depends on ST2's shared resolver.

Route the Work tree's group-by-type headers through the shared plural-label resolver instead of the raw type. Site: clients/vscode/src/domain/listView.ts (~line 131, groupDisplayNode).

Add/adjust a TS test for the Work-tree grouping header. Same gates: extension tsc + eslint + prettier + its tests; keep the type-aware lint gate intact (TS 6.0.3, do not weaken lint).
<!-- sq:subtask:ST3:body:end -->

#### Discussion

<!-- sq:subtask:ST3:discussion -->
<!-- sq:subtask:ST3:discussion:end -->
<!-- sq:subtask:ST3:end -->

<!-- sq:subtask:ST4 -->
### ST4 — De-hardcode Roster tree bucket labels from the catalog

<!-- sq:subtask:ST4:head -->
**Status:** ⚪ Todo
**Implements:** US3 — Clients render per-type display labels
<!-- sq:subtask:ST4:head:end -->

<!-- sq:subtask:ST4:body -->
TypeScript. Depends on ST2's shared resolver.

De-hardcode the Roster tree's rendered LABELS: resolve them from the type catalog via the shared plural-label resolver instead of the TS literals in clients/vscode/src/domain/reservedTypes.ts (META_BUCKETS) / metaView.ts.

KEEP the three fixed reserved bucket TYPES (role/skill/operator are the reserved set; META_BUCKETS also drives the Work tree's exclusion of roster types — that stays). Only the label strings move to the catalog.

The rendered labels are unchanged (derived plurals Roles/Skills/Operators == today's literals) — the point is a single source of truth, not a visible change. State that in any test so the intent is clear.

Add/adjust a TS test for the Roster header labels. Same gates: extension tsc + eslint + prettier + its tests; keep the type-aware lint gate intact (TS 6.0.3, do not weaken lint).
<!-- sq:subtask:ST4:body:end -->

#### Discussion

<!-- sq:subtask:ST4:discussion -->
<!-- sq:subtask:ST4:discussion:end -->
<!-- sq:subtask:ST4:end -->
<!-- sq:subtasks:end -->

## Discussion

<!-- sq:discussion -->
<!-- sq:discussion:end -->
