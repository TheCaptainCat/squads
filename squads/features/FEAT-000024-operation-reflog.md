---
id: FEAT-000024
sequence_id: 24
type: feature
title: Operation reflog
status: Done
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
  status: Done
- local_id: US2
  title: As a team member investigating an anomaly, I want removals, retypes and forced
    transitions explainable from the squad directory alone, so that a gap or surprise
    reads as history, not corruption
  status: Done
- local_id: US3
  title: As a tool builder, I want the reflog as stable, documented JSONL, so that
    I can build dashboards and automation on the operation stream
  status: Done
created_at: '2026-06-10T13:59:11Z'
updated_at: '2026-06-15T10:24:04Z'
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
| US1 | Done |  | As an operator, I want a chronological log of every mutation with its actor, so that I can review what the agents did without having been in their conversations |
| US2 | Done |  | As a team member investigating an anomaly, I want removals, retypes and forced transitions explainable from the squad directory alone, so that a gap or surprise reads as history, not corruption |
| US3 | Done |  | As a tool builder, I want the reflog as stable, documented JSONL, so that I can build dashboards and automation on the operation stream |
<!-- sq:summary:end -->

<!-- sq:stories -->

<!-- sq:story:US1 -->
### US1 — As an operator, I want a chronological log of every mutation with its actor, so that I can review what the agents did without having been in their conversations

<!-- sq:story:US1:head -->
**Status:** 🟢 Done
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
**Status:** 🟢 Done
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
**Status:** 🟢 Done
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
- [2026-06-15T08:22:01Z] Olivia Lead:
  - Broken down into two tasks (@python-dev). TASK-000112 — reflog core: the append-only JSONL writer hooked into the single IndexStore.transaction() seam (src/squads/_index/_store.py), atomic-with-commit, plus threading the actor (--as/--author) down to the store since today only `comment` carries one. Covers US1 (actor'd line per mutation) + US2 (remove/retype/forced-status/repair reconstructable). TASK-000113 — sq reflog read command (tail + --item/--actor/--op/--since + --json), versioned/documented schema, golden tests, contract tier. Covers US1/US2/US3.
  - Sequencing: TASK-000112 wraps the SAME transaction() core that FEAT-000020 (retype) and FEAT-000023 (removal) mutate — high conflict surface. Recommend reflog lands LAST of the three, after 20/23 settle the store/remove_item shape, so the reflog hook wraps a stable seam. Open ADR questions (flagged to architect, not decided here): exact append-vs-commit ordering/fsync, ambient-vs-explicit actor threading, and the line-schema stability tier — that last one is a FEAT-000013 deferral obligation.
  - TASK-000113 depends on TASK-000112.
- [2026-06-15T09:23:57Z] Robert Architect:
  - ADR-000117 settles the reflog durability/threading questions Olivia flagged (builds on ADR-114, doesn't relitigate that the reflog is in-transaction and NOT source of truth). @python-dev, TASK-000112 is unblocked against this contract:
  - (1) Ordering: append the line AFTER `_atomic_write`'s os.replace, while still holding the lock — never before. Logged-without-applied is UNACCEPTABLE (history would lie); applied-without-logged is the TOLERATED failure (one missing advisory line, state is correct). A failed append warns to stderr and must NOT fail/roll back the committed mutation. NO per-line fsync — the index already fsyncs; the reflog is advisory, a power-loss line gap is accepted over an fsync on every mutation.
  - (2) Append atomicity: one O_APPEND, single-write, newline-terminated JSON line per op (no embedded newlines). Reader (TASK-000113) MUST skip a trailing partial/unparseable line as an interrupted append (never an error), and warn-skip interior bad lines rather than abort.
  - (3) Actor: AMBIENT per-invocation, mirroring _clock — a _clock-shaped module (set_actor/current_actor, default 'system') set ONCE at the CLI root callback (same place --at calls clock.set_now), cleared per invocation via try/finally. No actor parameter threaded through service methods. op + before/after delta are captured at each CALL SITE (only it knows what changed) and buffered on the transaction context; the writer joins them with the ambient actor + clock.iso timestamp at commit.
  - (4) Line shape (versioned from day one): v (schema version), ts, actor, op (closed vocab), target id/type, delta (before/after SUMMARY). Forward-compatible by addition; readers key off v and ignore unknown fields.
  - FEAT-000013 DEFERRAL OBLIGATION (binding): the reflog file location (<squad>/.reflog.jsonl), the exact frozen line schema (field set), the version-field convention, and each field's stability tier through 1.0 are deferred to FEAT-000013's reflog-schema promise (US3 already routes there; ADR-114 deferred the remove-line fields + 'gaps are sanctioned' onto the same doc). ADR-117 fixes the shape only; FEAT-000013 freezes it.
- [2026-06-15T10:03:07Z] Robert Architect:
  - Reflog implementation is reviewed and the contract holds. REV-000118 (Paul) APPROVED both tasks against ADR-000117/ADR-000114 — all 5 checks pass, including empirical confirmation that the actor does not leak across invocations.
  - I addressed the two low findings that touched the ADR-117 §1 durability guarantee: F6 (serialization now inside append_line's guard + a catch-all on the post-commit append loop, so logging can never break a committed mutation) and F7 (rewrote the dead no-rollback test into three real ones). Full gate green.
  - Remaining before close: F8 doc cleanup (@python-dev) — stale docstrings + the actor-comment reword + the migrate/repad op-key nit; all cosmetic, non-gating. After that, TASK-000112/113 can go Done and FEAT-000024 closed. Reminder: the FEAT-000013 deferral (reflog file location, frozen line schema, version-field convention, per-field stability tier) is still owed by the 1.0 contract work — ADR-117 fixed the shape only.
- [2026-06-15T10:16:21Z] Mara Tester:
  - QA VERIFICATION COMPLETE — FEAT-000024 partially passes. One gap found.
  - PASS US1 (chronological log with actor): every mutating command except retype appends exactly one line with timestamp, actor, op, target, delta. Filters and tail work correctly. Atomicity: append-after-commit ordering confirmed in code and by design (no logged-without-applied possible; applied-without-logged is tolerated per ADR-117).
  - FAIL US2 (removals/retypes/forced-transitions reconstructable): retype is NOT logged. sq task N retype <type> appends zero reflog lines — verified empirically (line count unchanged) and by code inspection (_retype.py has no store._log() call). This breaks the 'retype reconstructable from squad directory alone' promise in FEAT-000024/TASK-000112 ST2. Removals (op=remove with gone-item snapshot), forced-status (logged as normal status op with before/after showing the jump), and repair are all correctly logged.
  - PASS US3 (stable documented JSONL): line schema versioned (v=0.3), documented in docs/workflow.md, golden-tested via tests/goldens/reflog_shape.json. --json shape verified. Stability tier for delta deferred to FEAT-000013 as documented.
  - PASS not-a-source-of-truth guarantee: empirically confirmed — corrupt or missing reflog has zero effect on sq repair, sq check, or any read/write command. sq repair rebuilds identically with and without reflog. sq check is clean.
  - Full suite: 699 passed, 1 skipped. Filing a bug for the retype gap. @tech-lead please assign TASK-000112 a fix for _retype.py to call store._log() with op='retype' and a delta containing old_id/new_id/status_carried.
<!-- sq:discussion:end -->
