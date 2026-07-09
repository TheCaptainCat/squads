---
id: TASK-331
sequence_id: 331
type: task
title: Freeze migration vocabulary + additive prefix-line normalization
status: Cancelled
parent: FEAT-326
author: tech-lead
subentities:
- local_id: ST1
  title: Additive prefix-line normalization pass wired into MIGRATIONS
  status: Todo
  story: US4
- local_id: ST2
  title: Assess/decide/record the SCHEMA_VERSION bump
  status: Todo
  story: US4
created_at: '2026-07-07T14:50:25Z'
updated_at: '2026-07-08T16:05:34Z'
---
<!-- sq:body -->
## Scope

Land the disk-normalization side of the type-axis change: an **additive
`prefix:`-line normalization** `sq migrate` pass that stamps the now-canonical
`prefix:` line onto every legacy built-in item file, plus the `SCHEMA_VERSION`
assess/decide-and-record call. Serves the "unmodified default behaves
identically / historical runs stay reproducible" acceptance (US4).

**Migration-vocabulary freeze moved out.** Freezing the migration runners'
`ItemType` references to inline frozen local constants now lives in TASK-328,
and their `Status` references in TASK-330 — each enum's freeze had to land in
the same task that deletes that enum, since the delete is only grep/pyright-clean
once every reference is gone. This task no longer touches the runners' vocabulary;
it only adds the new normalization pass and makes the schema-version call.

## Areas / files

- Normalization pass — an additive `sq migrate` step that stamps the now-canonical
  `prefix:` line onto every legacy built-in item file, so the `from_frontmatter`
  legacy omit-branch can eventually be deleted outright. Reads already tolerate
  its absence (spec backfill at load, added in TASK-328); this normalizes on
  disk. Wire it into `_migrations/_registry.py::MIGRATIONS` with its `Migration`
  record + `manual` runbook string, run through `sq migrate up` (then `repair` +
  stamp).
- `SCHEMA_VERSION` (`_models/_schema.py`) — assess and decide: a bump is **not**
  required for read correctness (backfill at load), but is reasonable to
  *normalize* every file. Make the call, record the rationale in this task's
  discussion, and if bumping, add the ordered migration + stamp per the migrate
  runbook. Coordinate with the EPIC-280 / FEAT-281 migration owners (the
  `prefix:`-line normalization is a natural fit for their migration surface).

## Done criteria

- The normalization pass stamps `prefix:` on legacy built-in files and runs clean
  via `sq migrate up` + `sq repair`.
- The `SCHEMA_VERSION` decision is recorded (this task's discussion) and, if
  taken, implemented and stamped.
- Historical migration tests still reproduce; `pyright` + `ruff check` +
  `ruff format --check` clean.

## Sequencing note

Lands last on the type/status axis, after the enum deletions (TASK-328/330) —
the normalization pass writes the canonical `prefix:` line that TASK-328's
spec-free round-trip and load-backfill establish, so it depends on that work
being in place. The migration-runner vocabulary freeze it used to own now lands
inside those enum-deletion tasks.
<!-- sq:body:end -->

## Subtasks

_Add with `sq task 331 add-subtask "<title>"`; track with `sq task 331 subtask <n> update --status <Status>`._

<!-- sq:summary -->
| Subtask | Status | Assignee | Title | Story |
| --- | --- | --- | --- | --- |
| ST1 | Todo |  | Additive prefix-line normalization pass wired into MIGRATIONS | US4 |
| ST2 | Todo |  | Assess/decide/record the SCHEMA_VERSION bump | US4 |
<!-- sq:summary:end -->

<!-- sq:subtasks -->

<!-- sq:subtask:ST1 -->
### ST1 — Additive prefix-line normalization pass wired into MIGRATIONS

<!-- sq:subtask:ST1:head -->
**Status:** ⚪ Todo
**Implements:** US4 — Unmodified default squad behaves identically
<!-- sq:subtask:ST1:head:end -->

<!-- sq:subtask:ST1:body -->
Add an additive sq migrate step that stamps the now-canonical prefix line onto every legacy built-in item file (so the from_frontmatter omit-branch can later be deleted). Wire it into _migrations/_registry.py MIGRATIONS with its Migration record + manual runbook; runs through sq migrate up (then repair + stamp). Reads already tolerate its absence via TASK-328's load backfill; this normalizes on disk.
<!-- sq:subtask:ST1:body:end -->

#### Discussion

<!-- sq:subtask:ST1:discussion -->
<!-- sq:subtask:ST1:discussion:end -->
<!-- sq:subtask:ST1:end -->

<!-- sq:subtask:ST2 -->
### ST2 — Assess/decide/record the SCHEMA_VERSION bump

<!-- sq:subtask:ST2:head -->
**Status:** ⚪ Todo
**Implements:** US4 — Unmodified default squad behaves identically
<!-- sq:subtask:ST2:head:end -->

<!-- sq:subtask:ST2:body -->
Assess and decide the SCHEMA_VERSION bump: not required for read correctness (backfill at load), but reasonable to normalize every file. Record the rationale in this task's discussion; if bumping, add the ordered migration + stamp per the migrate runbook. Coordinate with the EPIC-280/FEAT-281 migration owners. NOTE: the migration-vocabulary freeze (ItemType/Status) formerly in this task moved to TASK-328/TASK-330.
<!-- sq:subtask:ST2:body:end -->

#### Discussion

<!-- sq:subtask:ST2:discussion -->
<!-- sq:subtask:ST2:discussion:end -->
<!-- sq:subtask:ST2:end -->
<!-- sq:subtasks:end -->

## Discussion

<!-- sq:discussion -->
- [2026-07-08T11:40:41Z] Olivia Lead:
  - Re-scoped (pre-dispatch): NARROWED. Removed 'freeze all migration vocabulary' — that's now split into TASK-328 (ItemType refs) and TASK-330 (Status refs), because each enum's freeze must land in the same task that deletes that enum (the delete is only grep/pyright-clean once every reference is gone; a last-in-sequence freeze would leave 328/330 red).
  - Remaining scope is exactly: (a) the additive prefix-line normalization sq migrate pass wired into _migrations/_registry.py MIGRATIONS with its Migration record + manual runbook, and (b) the SCHEMA_VERSION assess/decide-and-record call. Still lands last on the axis — it depends on TASK-328's spec-free round-trip + load backfill. Repurposed ST1 (normalization pass) and ST2 (schema-version decision) accordingly.
- [2026-07-08T12:50:38Z] Catherine Manager:
  - Correction: TASK-331 is NOT complete. The TASK-328 dev's handoff claimed 331 was 'folded in, nothing remains' — that conflated the load-time prefix backfill (which IS part of 328, ADR §3) with 331's actual remaining scope.
  - 331 still owns: (ST1) the ADDITIVE sq migrate normalization pass that stamps the canonical prefix: line onto legacy built-in files on disk (wired into _migrations/_registry.py MIGRATIONS with a Migration record + manual runbook), so the from_frontmatter unset-prefix branch can eventually be deleted; and (ST2) the SCHEMA_VERSION assess/decide-and-record call. Verified neither was done: SCHEMA_VERSION is still 0.7, no new normalization runner, no registry change. Staying Ready — dispatch after 330.
- [2026-07-08T16:05:34Z] Catherine Manager:
  - Cancelled: op-pierre identified that carrying a separate prefix: line on every item is redundant — the prefix is already recoverable from the item's stored id (PREFIX-nnn). The fix is to derive the prefix from the id on read and drop the frontmatter field, which eliminates the need for this task's normalization migration and the SCHEMA_VERSION 0.7->0.8 bump entirely (nothing to normalize). Superseded by a rework of TASK-328's prefix mechanism + an ADR-322 §3 correction. All of this task's uncommitted work (runner, schema bump, dogfood prefix-stamps, corpus/goldens) has been reverted.
<!-- sq:discussion:end -->
