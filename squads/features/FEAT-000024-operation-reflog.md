---
id: FEAT-000024
sequence_id: 24
type: feature
title: Operation reflog
status: Ready
parent: EPIC-000012
author: product-owner
priority: medium
refs:
- FEAT-000023
- BUG-000022
- FEAT-000015
description: An append-only JSONL log of every mutating sq operation (who, when, what,
  before/after), with a sq reflog command to read it
subentities:
- local_id: US1
  title: As an operator, I want a chronological log of every mutation with its actor,
    so that I can review what the agents did without having been in their conversations
  status: Todo
- local_id: US2
  title: As a team member investigating an anomaly, I want removals, retypes and forced
    transitions explainable from the squad directory alone, so that a gap or surprise
    reads as history, not corruption
  status: Todo
- local_id: US3
  title: As a tool builder, I want the reflog as stable, documented JSONL, so that
    I can build dashboards and automation on the operation stream
  status: Todo
created_at: '2026-06-10T13:59:11Z'
updated_at: '2026-06-11T07:54:55Z'
---
<!-- sq:body -->
## Problem

squads has no memory of *operations* — only of resulting state. The `.md` files say what an item
is now, `sq check` says whether the present is consistent, and git (when the squad is committed)
captures snapshots at whatever cadence someone commits. Nothing records *who did what, when*: which
agent transitioned a status, when a removal happened, what an item looked like just before a
mutation. Today's incidents made the cost concrete — a deleted item left no trace, a reused number
had no explanation, and reconstructing the sequence of events relied on one operator's memory and
a chat transcript that the rest of the team can't see.

## Value

An append-only **reflog** — one JSONL line per mutating operation — gives the squad an operation
history that survives the conversation:

- **Audit**: a multi-agent team coordinating through `sq` becomes reviewable after the fact
  ("what did the agents do overnight?").
- **Forensics**: number gaps, removals, retypes and force-pushes through the workflow are
  explainable from the squad directory alone — this is the trace mechanism FEAT-000023's audit
  question asks for, generalized.
- **Foundation**: an operation log is the prerequisite for any future undo/revert story, without
  committing to one now.

## Scope

- A JSONL file under the squad dir (e.g. `squads/.reflog.jsonl`), **append-only**, one line per
  mutating operation: timestamp, actor (the `--as`/`--author` slug or invoking agent), operation
  (create/update/status/body/comment/sub-entity/ref/remove/repair/migrate/…), target item ID(s),
  and a compact before→after delta (e.g. `status: Ready→InProgress`). Reads are not logged.
- Written **inside the same transaction** as the mutation — a committed change and its log line
  never diverge.
- `sq reflog` read command: tail by default, filterable (`--item`, `--actor`, `--op`, `--since`),
  `--json` passthrough (the shapes join FEAT-000015's frozen-surface work).
- **Explicitly not source of truth**: the index stays rebuildable from frontmatter alone; the
  reflog is history, never consulted for state, and a missing/truncated reflog is never an error.
- Design questions for the ADR: line schema + its stability tier in the 1.0 contract
  (FEAT-000013); rotation/size policy; whether `repair` records what it reconciled (BUG-000022's
  "surface missing items" wish would live here naturally).

## Acceptance

- Every mutating command appends exactly one well-formed JSONL line, atomically with the mutation;
  a crash never produces a logged-but-not-applied (or applied-but-not-logged) pair.
- `sq reflog` reads and filters the log; `--json` shape documented and golden-tested.
- A squad with no reflog file behaves identically (back-compat with every existing squad).
- The line schema is documented, versioned, and its stability promise stated in the contract doc.
<!-- sq:body:end -->

## User Stories

_Add with `sq feature 24 add-story "As a <role>, I want … so that …"`; track with `sq feature 24 story <n> update --status <Status>`._

<!-- sq:summary -->
| Story | Status | Assignee | Title |
| --- | --- | --- | --- |
| US1 | Todo |  | As an operator, I want a chronological log of every mutation with its actor, so that I can review what the agents did without having been in their conversations |
| US2 | Todo |  | As a team member investigating an anomaly, I want removals, retypes and forced transitions explainable from the squad directory alone, so that a gap or surprise reads as history, not corruption |
| US3 | Todo |  | As a tool builder, I want the reflog as stable, documented JSONL, so that I can build dashboards and automation on the operation stream |
<!-- sq:summary:end -->

<!-- sq:stories -->

<!-- sq:story:US1 -->
### US1 — As an operator, I want a chronological log of every mutation with its actor, so that I can review what the agents did without having been in their conversations

<!-- sq:story:US1:head -->
**Status:** ⚪ Todo
<!-- sq:story:US1:head:end -->

<!-- sq:story:US1:body -->
**Acceptance:** every mutating command appends one line (timestamp, actor, op, item, delta) atomically with the change; `sq reflog` tails and filters by --item/--actor/--op/--since.
<!-- sq:story:US1:body:end -->

#### Discussion

<!-- sq:story:US1:discussion -->
<!-- sq:story:US1:discussion:end -->
<!-- sq:story:US1:end -->

<!-- sq:story:US2 -->
### US2 — As a team member investigating an anomaly, I want removals, retypes and forced transitions explainable from the squad directory alone, so that a gap or surprise reads as history, not corruption

<!-- sq:story:US2:head -->
**Status:** ⚪ Todo
<!-- sq:story:US2:head:end -->

<!-- sq:story:US2:body -->
**Acceptance:** remove/retype/forced-status/repair operations are reconstructable from reflog lines alone (FEAT-000023's audit trail and BUG-000022's repair-reporting wish land here); a squad with no reflog file still works identically.
<!-- sq:story:US2:body:end -->

#### Discussion

<!-- sq:story:US2:discussion -->
<!-- sq:story:US2:discussion:end -->
<!-- sq:story:US2:end -->

<!-- sq:story:US3 -->
### US3 — As a tool builder, I want the reflog as stable, documented JSONL, so that I can build dashboards and automation on the operation stream

<!-- sq:story:US3:head -->
**Status:** ⚪ Todo
<!-- sq:story:US3:head:end -->

<!-- sq:story:US3:body -->
**Acceptance:** the line schema is versioned and documented; `sq reflog --json` shape is golden-tested (FEAT-000015) and its stability tier stated in the contract doc (FEAT-000013).
<!-- sq:story:US3:body:end -->

#### Discussion

<!-- sq:story:US3:discussion -->
<!-- sq:story:US3:discussion:end -->
<!-- sq:story:US3:end -->
<!-- sq:stories:end -->

## Discussion

<!-- sq:discussion -->
<!-- sq:discussion:end -->
