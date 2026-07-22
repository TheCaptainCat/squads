---
id: TASK-586
sequence_id: 586
type: task
title: Re-home 5 parented ADRs onto related refs
status: Done
parent: FEAT-572
author: tech-lead
created_at: '2026-07-22T11:51:27Z'
updated_at: '2026-07-22T11:53:49Z'
---
<!-- sq:body -->
## Scope

Re-home the 5 ADRs that still hold a `parent` onto a `related` ref to the work
item they inform, closing the live gap ADR-541/EPIC-538 cite (records take no
parent). Pure content edits through existing `sq` commands — no new `sq` support
needed. Each edit is `sq decision <n> update --no-parent` plus, where the target
is not already a `related` ref, `sq decision <n> ref add <target> --kind related`.

### The 5 migrations (verified refs as of cut)

- **ADR-516** → EPIC-28: no existing ref — add `related` EPIC-28, then clear parent.
- **ADR-527** → EPIC-28: refs ADR-516 only — add `related` EPIC-28, then clear parent.
- **ADR-155** → EPIC-121: refs FEAT-122/BUG-152 — add `related` EPIC-121, then clear parent.
- **ADR-158** → EPIC-121: refs FEAT-125/ADR-155/FEAT-24 — add `related` EPIC-121, then clear parent.
- **ADR-129** → FEAT-17: **FEAT-17 is already a `related` ref** — clear parent only.
  Do NOT re-add the ref (would duplicate).

## Verification

- For each ADR, confirm no other tooling depended on the parent edge before
  clearing it: `sq tree` on the old parent no longer lists the ADR as a child
  (expected — records relate through refs, not hierarchy), and item rendering
  is unaffected (parent line drops, `related` ref shows in the refs table).
- `sq check` clean before AND after (baseline is clean at cut time — exit 0).
  This migration removes exactly the 5 parented-record cases the `records`
  `no_parent` validator default (TASK-584, FEAT-568) would otherwise flag.
- No other ADR gains or loses a parent as a side effect.

## Acceptance

- All 5 ADRs have no `parent` and carry the listed `related` ref.
- `sq check` exit 0, and `grep -c '</\?content>'` across the touched `.md` == 0.
- Full suite green; pyright + ruff clean (no source changes expected — this is
  content-only, but run the gate to confirm nothing regressed).

## Sequencing

- No upstream dependency beyond Phase A (FEAT-567, committed) — dispatch anytime.
- **Unblocks TASK-584**: TASK-584 (`records`/`epic` `no_parent` enforcement)
  carries a `depends-on` ref to FEAT-572 and must not land until this migration
  is in, or turning on the default reddens `sq check` on this repo.
<!-- sq:body:end -->

## Subtasks

_Add with `sq task 586 add-subtask "<title>"`; track with `sq task 586 subtask <n> update --status <Status>`._

<!-- sq:summary -->
<!-- sq:summary:end -->

<!-- sq:subtasks -->
<!-- sq:subtasks:end -->

## Discussion

<!-- sq:discussion -->
<!-- sq:discussion:end -->
