---
id: TASK-584
sequence_id: 584
type: task
title: Enforce records + epic no_parent defaults (coordinate FEAT-572)
status: Draft
parent: FEAT-568
author: tech-lead
refs:
- ADR-541
- TASK-582:depends-on
- TASK-583:depends-on
- FEAT-572:depends-on
description: Turn on the two new no_parent enforcements; must land with-or-after the
  5-parented-ADR migration
created_at: '2026-07-22T10:33:02Z'
updated_at: '2026-07-22T10:33:12Z'
---
<!-- sq:body -->
## Scope

Turn on the two deliberate **new** enforcements ADR-541 calls out — the only
non-byte-identical change in FEAT-568:

- Add `no_parent` to the `records` `CATEGORY_BUNDLES` default, so
  `decision`/`contract`/`guide` reject a parent at create/update and `sq check`
  flags any existing parented record.
- Add `no_parent` to `epic` as a per-type addition on the bundled spec's `epic`
  `ItemSpec.validators` (uses the assignment surface — depends on that task),
  enforcing the previously-unenforced work-root constraint. `epic`'s `parents`
  is empty, so this is a pure AND-compose tightening, not a conflict.

## Dependencies / sequencing — READ BEFORE STARTING

- **Hard dependency on FEAT-572** (migrate the 5 parented ADRs —
  ADR-129/155/158/516/527 — to `related` refs). This task **must land
  with-or-after FEAT-572**, never before: turning on records-`no_parent` while
  those 5 ADRs still hold a parent reddens `sq check` on this very repo. Encoded
  as a `depends-on` ref to FEAT-572. Coordinate the merge order with whoever
  picks up FEAT-572 — do not merge this until FEAT-572's migration is in.
- Depends on the routing task (bundles wired) and the assignment-surface task
  (epic needs the `validators` field).

## Acceptance

- With FEAT-572 landed, `uv run sq check` on this repo is **clean** (no parented
  records/epics remain to flag).
- `records` and `epic` reject a parent at create/update (gate) — targeted tests
  for both, asserting the abort message.
- A synthetic parented record / parented epic is reported by `sq check` (Plane-2
  report, not a load brick) — targeted tests.
- Everything else stays byte-identical to the routing task's output.
- Full suite green; pyright + ruff clean.
<!-- sq:body:end -->

## Subtasks

_Add with `sq task 584 add-subtask "<title>"`; track with `sq task 584 subtask <n> update --status <Status>`._

<!-- sq:summary -->
<!-- sq:summary:end -->

<!-- sq:subtasks -->
<!-- sq:subtasks:end -->

## Discussion

<!-- sq:discussion -->
<!-- sq:discussion:end -->
