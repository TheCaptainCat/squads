---
id: TASK-651
sequence_id: 651
type: task
title: Expose display labels in JSON + clients render them
status: Done
parent: FEAT-647
author: tech-lead
refs:
- ADR-646:addresses
subentities:
- local_id: ST1
  title: Add resolved labels to sq workflow types --json
  status: Done
  story: US3
- local_id: ST2
  title: Extension renders per-type Records buckets with plural labels
  status: Done
  story: US3
- local_id: ST3
  title: Route Work tree group-by-type headers through the shared resolver
  status: Done
  story: US3
- local_id: ST4
  title: De-hardcode Roster tree bucket labels from the catalog
  status: Done
  story: US3
created_at: '2026-07-24T12:55:56Z'
updated_at: '2026-07-27T08:32:00Z'
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
| ST1 | Done |  | Add resolved labels to sq workflow types --json | US3 |
| ST2 | Done |  | Extension renders per-type Records buckets with plural labels | US3 |
| ST3 | Done |  | Route Work tree group-by-type headers through the shared resolver | US3 |
| ST4 | Done |  | De-hardcode Roster tree bucket labels from the catalog | US3 |
<!-- sq:summary:end -->

<!-- sq:subtasks -->

<!-- sq:subtask:ST1 -->
### ST1 — Add resolved labels to sq workflow types --json

<!-- sq:subtask:ST1:head -->
**Status:** 🟢 Done
**Implements:** US3 — Clients render per-type display labels
<!-- sq:subtask:ST1:head:end -->

<!-- sq:subtask:ST1:body -->
Added a `labels` object {singular, plural, singular_lower, plural_lower} to each row of `sq workflow types --json`, resolved via labels_for(type, spec) (pin-else-derive). Additive only; TYPE_CATALOG_FIELDS extended, golden regenerated, new tests added.
<!-- sq:subtask:ST1:body:end -->

#### Discussion

<!-- sq:subtask:ST1:discussion -->
<!-- sq:subtask:ST1:discussion:end -->
<!-- sq:subtask:ST1:end -->

<!-- sq:subtask:ST2 -->
### ST2 — Extension renders per-type Records buckets with plural labels

<!-- sq:subtask:ST2:head -->
**Status:** 🟢 Done
**Implements:** US3 — Clients render per-type display labels
<!-- sq:subtask:ST2:head:end -->

<!-- sq:subtask:ST2:body -->
Shape guard for the new labels field + shared TS resolver (domain/typeLabels.ts::pluralLabel) + Records tree bucket headers routed through it.
<!-- sq:subtask:ST2:body:end -->

#### Discussion

<!-- sq:subtask:ST2:discussion -->
<!-- sq:subtask:ST2:discussion:end -->
<!-- sq:subtask:ST2:end -->

<!-- sq:subtask:ST3 -->
### ST3 — Route Work tree group-by-type headers through the shared resolver

<!-- sq:subtask:ST3:head -->
**Status:** 🟢 Done
**Implements:** US3 — Clients render per-type display labels
<!-- sq:subtask:ST3:head:end -->

<!-- sq:subtask:ST3:body -->
Work tree's group-by-type headers (domain/listView.ts::groupListItems) routed through the shared pluralLabel resolver.
<!-- sq:subtask:ST3:body:end -->

#### Discussion

<!-- sq:subtask:ST3:discussion -->
<!-- sq:subtask:ST3:discussion:end -->
<!-- sq:subtask:ST3:end -->

<!-- sq:subtask:ST4 -->
### ST4 — De-hardcode Roster tree bucket labels from the catalog

<!-- sq:subtask:ST4:head -->
**Status:** 🟢 Done
**Implements:** US3 — Clients render per-type display labels
<!-- sq:subtask:ST4:head:end -->

<!-- sq:subtask:ST4:body -->
Roster tree bucket labels (domain/metaView.ts) now resolved from the type catalog via pluralLabel; META_BUCKETS keeps only the 3 fixed reserved types, no longer the TS-literal labels.
<!-- sq:subtask:ST4:body:end -->

#### Discussion

<!-- sq:subtask:ST4:discussion -->
<!-- sq:subtask:ST4:discussion:end -->
<!-- sq:subtask:ST4:end -->
<!-- sq:subtasks:end -->

## Discussion

<!-- sq:discussion -->
- [2026-07-24T14:02:54Z] Elias Python:
  - ST1 done: sq workflow types --json now includes a labels object {singular, plural, singular_lower, plural_lower} per type row, resolved via labels_for(type, spec) (pin-else-derive). Additive only — existing keys unchanged. TYPE_CATALOG_FIELDS extended to include 'labels'; golden tests/goldens/workflow_types.json regenerated. Ready for ST2 (extension resolver reads labels.plural, falls back to raw type if absent).
- [2026-07-24T14:23:36Z] Ada Typescript:
  - ST2/ST3/ST4 done: added domain/typeLabels.ts (pluralLabel/buildTypeLabelMap), the single shared resolver every per-type group header now routes through.
  - sqAdapter.ts shape guard extended for the optional labels object (older sq without it still parses fine).
  - Records tree (recordsView.ts), Work tree (listView.ts groupListItems), and Roster tree (metaView.ts, via de-hardcoded META_BUCKETS) all resolve their bucket/group headers from the type catalog now; reserved bucket types (role/skill/operator) unchanged.
  - Rendered output is unchanged in the normal case (Roles/Skills/Operators, Decisions/Guides, etc. render exactly as before) -- this is a single-source-of-truth refactor, not a visible change.
  - Gates green: tsc, eslint --max-warnings 0, prettier --check, vitest (399 passed), plus test:canary against a real sq binary.
  - Needs the operator's visual check on the Windows VS Code dev host before Done.
<!-- sq:discussion:end -->
