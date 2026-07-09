---
id: TASK-331
sequence_id: 331
type: task
title: Freeze migration vocabulary + additive prefix-line normalization
status: Ready
parent: FEAT-326
author: tech-lead
subentities:
- local_id: ST1
  title: Inline frozen local vocab constants in all historical migration runners
  status: Todo
  story: US4
- local_id: ST2
  title: Additive prefix-line normalization pass; assess/decide SCHEMA_VERSION bump
  status: Todo
  story: US4
created_at: '2026-07-07T14:50:25Z'
updated_at: '2026-07-08T08:30:15Z'
---
<!-- sq:body -->
## Scope

Keep the historical migration runners reproducible after both enums are gone by
pinning the vocabulary each one targets as **inline frozen local constants**
(never the live spec, never a removed enum); add the additive `prefix:`-line
normalization pass; and make the `SCHEMA_VERSION` call. A migration is a
point-in-time transform — it must snapshot the vocabulary as it existed at the
schema version it targets. Serves the "unmodified default behaves identically /
historical runs stay reproducible" acceptance (US4).

## Areas / files

- `_migrations/_v0_1_to_v0_2.py`, `_v0_2_to_v0_3.py`, `_v0_4_to_v0_5.py`,
  `_v0_5_to_v0_7.py` — replace `ItemType.X`, `for item_type in ItemType`, and the
  `_BODY_KIND` enum references with inline frozen literal tuples/maps equal to the
  **type names as they existed at that schema version**.
- `_migrations/_meta_compat.py`, `_v0_4_to_v0_5.py` — same treatment for the
  `Status` references (frozen literal **status** names for that version).
- Normalization pass — an additive `sq migrate` step that stamps the now-canonical
  `prefix:` line onto every legacy built-in item file, so the `from_frontmatter`
  legacy omit-branch can eventually be deleted outright. Reads already tolerate
  its absence (spec backfill at load); this normalizes on disk. Wire it into
  `_migrations/_registry.py::MIGRATIONS` with its `Migration` record + `manual`
  runbook string, run through `sq migrate up` (then `repair` + stamp).
- `SCHEMA_VERSION` (`_models/_schema.py`) — assess and decide: a bump is **not**
  required for read correctness (backfill at load), but is reasonable to
  *normalize* every file. Make the call, record the rationale in this task's
  discussion, and if bumping, add the ordered migration + stamp per the migrate
  runbook. Coordinate with the EPIC-280 / FEAT-281 migration owners (the
  `prefix:`-line normalization is a natural fit for their migration surface).

## Done criteria

- No migration runner references a removed enum or the live spec for its
  vocabulary; each pins frozen local constants.
- The normalization pass stamps `prefix:` on legacy built-in files and runs clean
  via `sq migrate up` + `sq repair`.
- The `SCHEMA_VERSION` decision is recorded (this task's discussion) and, if
  taken, implemented and stamped.
- Historical migration tests still reproduce; `pyright` + `ruff check` +
  `ruff format --check` clean.

## Sequencing note

Lands alongside/after the enum deletions — the runners can only stop referencing
`ItemType`/`Status` once the frozen local constants replace them, which is the
whole point of this task.
<!-- sq:body:end -->

## Subtasks

_Add with `sq task 331 add-subtask "<title>"`; track with `sq task 331 subtask <n> update --status <Status>`._

<!-- sq:summary -->
| Subtask | Status | Assignee | Title | Story |
| --- | --- | --- | --- | --- |
| ST1 | Todo |  | Inline frozen local vocab constants in all historical migration runners | US4 |
| ST2 | Todo |  | Additive prefix-line normalization pass; assess/decide SCHEMA_VERSION bump | US4 |
<!-- sq:summary:end -->

<!-- sq:subtasks -->

<!-- sq:subtask:ST1 -->
### ST1 — Inline frozen local vocab constants in all historical migration runners

<!-- sq:subtask:ST1:head -->
**Status:** ⚪ Todo
**Implements:** US4 — Unmodified default squad behaves identically
<!-- sq:subtask:ST1:head:end -->

<!-- sq:subtask:ST1:body -->
Replace ItemType.X, 'for item_type in ItemType', the _BODY_KIND enum references, and Status.X in _v0_1_to_v0_2/_v0_2_to_v0_3/_v0_4_to_v0_5/_v0_5_to_v0_7 and _meta_compat.py with inline frozen local literal tuples/maps equal to the type and status names as they existed at each runner's target schema version.
<!-- sq:subtask:ST1:body:end -->

#### Discussion

<!-- sq:subtask:ST1:discussion -->
<!-- sq:subtask:ST1:discussion:end -->
<!-- sq:subtask:ST1:end -->

<!-- sq:subtask:ST2 -->
### ST2 — Additive prefix-line normalization pass; assess/decide SCHEMA_VERSION bump

<!-- sq:subtask:ST2:head -->
**Status:** ⚪ Todo
**Implements:** US4 — Unmodified default squad behaves identically
<!-- sq:subtask:ST2:head:end -->

<!-- sq:subtask:ST2:body -->
Add an additive sq migrate step (wired into _migrations/_registry.py MIGRATIONS with its Migration record + manual runbook) that stamps the now-canonical prefix line onto every legacy built-in item file, so the from_frontmatter omit-branch can later be deleted. Assess and decide the SCHEMA_VERSION bump (not required for read correctness; reasonable to normalize), record the rationale in this task's discussion, and implement+stamp if taken.
<!-- sq:subtask:ST2:body:end -->

#### Discussion

<!-- sq:subtask:ST2:discussion -->
<!-- sq:subtask:ST2:discussion:end -->
<!-- sq:subtask:ST2:end -->
<!-- sq:subtasks:end -->

## Discussion

<!-- sq:discussion -->
<!-- sq:discussion:end -->
