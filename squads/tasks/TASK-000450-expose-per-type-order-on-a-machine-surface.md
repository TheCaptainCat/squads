---
id: TASK-450
sequence_id: 450
type: task
title: Expose per-type order on a machine surface
status: Done
parent: FEAT-449
author: tech-lead
assignee: python-dev
refs:
- ADR-427:addresses
description: 'Core: additive --json type catalog exposing ItemSpec.order (US5/F1 core
  half)'
created_at: '2026-07-17T13:23:45Z'
updated_at: '2026-07-17T15:49:03Z'
---
<!-- sq:body -->
Story: US5 (type-group ordering). Covers REV-448 finding F1 — the **core half** only; the client-side sort is a dependent task.

## Problem

No machine surface exposes the workflow spec's per-type ordering. `sq tree --json` and `sq list --json` give each node's type *name* but not its order. `ItemSpec.order` exists in the spec (`_workflow/_models.py`; `float`, defaulting to `math.inf`, type-name string breaks ties; bundled defaults epic=10 / feature=20 / task=30 / bug=40 / decision=50 / review=60 / guide=70) but is invisible to any consumer.

## Scope

Additively expose the per-type `order` on a `--json` machine surface so the client can sort type groups spec-driven. Recommended surface: a **type catalog** on `sq workflow --json` (each declared type with at least its name and `order`; reuse/extend the pattern behind the existing `playbook_spec.json` if it fits). Order is a per-*type* property, so do NOT repeat it per node on tree/list — a type catalog is the right shape.

Design note to settle with the architect before building: exact surface (a `--json` flag on `sq workflow` vs. a new sub-command) and whether to include other already-derivable per-type metadata (prefix, reserved-flag). Keep it minimal and additive.

## Requirements

- Spec-driven: read `ItemSpec.order` from the active workflow spec; never a hardcoded type list.
- Additive/superset only — no existing `--json` shape changes.
- Represent un-ordered types (`math.inf`) so the client can sort them last (serialize as `null`, or omit the field) — document the choice.
- Golden-frozen: new golden under `tests/goldens/` with a test asserting a byte-identical shape.
- Reviewer-gated (independent review before merge).

## Acceptance

- The new `--json` surface emits every declared type with its resolved order; `math.inf` types are represented so a consumer sorts them last.
- Golden committed + test pinning the shape.
- Full Python suite + `pyright` strict + `ruff` (check & format) green; `sq check` clean.
- CHANGELOG note (additive surface).
<!-- sq:body:end -->

## Subtasks

_Add with `sq task 450 add-subtask "<title>"`; track with `sq task 450 subtask <n> update --status <Status>`._

<!-- sq:summary -->
<!-- sq:summary:end -->

<!-- sq:subtasks -->
<!-- sq:subtasks:end -->

## Discussion

<!-- sq:discussion -->
- [2026-07-17T14:04:43Z] Robert Architect:
  - Surface settled in ADR-459 (Proposed) — build against it. Command: NEW subcommand `sq workflow types` (NOT a --json flag on the cheatsheet callback; that stays free for F8's --raw). Default prints a Rich table; `--json` emits the machine shape.
  - Shape: a bare JSON array (matches tree/list/show convention), one object per declared type, emitted in ascending resolved order (type-name tiebreak — the same ordering the CLI registers per-type commands with). Include ALL declared types, work AND reserved.
  - Fields per object: `type` (type key, e.g. "task"), `order` (JSON number, or `null` when +inf — present-but-null, not omitted, so the key set is stable; consumer sorts null last), `prefix` (e.g. "TASK"), `reserved` (bool = ItemSpec.is_meta). No title (type key is the label — derivable), no folder (on-disk internal, off-limits per ADR-427), no lifecycle/status (separate surface).
  - Spec-driven: read the active WorkflowSpec (.types / work_types() + meta types), never a hardcoded list. Additive-superset only; new golden tests/goldens/workflow_types.json + a test pinning the byte-identical shape and asserting the field set matches the model. @python-dev this unblocks the build.
- [2026-07-17T15:41:44Z] Elias Python:
  - Built `sq workflow types` (src/squads/_cli/_workflow_cmd.py): default Rich table, --json bare array {type, order|null, prefix, reserved} in ascending resolved order, all declared types incl. reserved meta-types. Extracted a pure _type_catalog(spec) helper for testability.
  - Golden: tests/goldens/workflow_types.json (wired into the shared golden-shape harness in tests/cli/test_json_output_shape.py). New tests/cli/test_workflow_types_cli.py covers CLI table/json, field-set-vs-model contract, and null-order representation for an unordered custom type.
  - Scoped tests green (75), tests/meta clean (no ticket IDs in source), pyright + ruff clean on touched files, sq check clean. CHANGELOG updated. Left at InReview -- did not commit.
  - @reviewer ready for independent review.
<!-- sq:discussion:end -->
