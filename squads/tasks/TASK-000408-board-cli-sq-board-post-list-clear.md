---
id: TASK-408
sequence_id: 408
type: task
title: 'Board CLI: sq board post/list/clear'
status: Done
parent: FEAT-317
author: tech-lead
description: The sq board command group over the board storage layer
subentities:
- local_id: ST1
  title: sq board post -m [--until]; attributable author
  status: Done
  story: US1
- local_id: ST2
  title: 'sq board list: ordinal, author, posted-at, expiry'
  status: Done
  story: US3
- local_id: ST3
  title: 'sq board clear <n>: resolve ordinal to hash id; clean out-of-range'
  status: Done
  story: US4
created_at: '2026-07-15T07:48:19Z'
updated_at: '2026-07-15T11:09:20Z'
---
<!-- sq:body -->
Build the `sq board ...` command group over the board storage layer.

## Commands

- `sq board post -m "<notice>" [--until <date>]` — post a notice; attributable to its author (operator via `--as op-<slug>`, or agent role).

- `sq board list` — show current (unexpired) notices with an ephemeral positional ordinal, author, posted-at, and expiry (if set).

- `sq board clear <n>` — take one down: resolve `<n>` as the n-th entry line of the generated `squads/board/.index.jsonl` (header excluded) to the notice's stable hash id, and remove its file.

## Notes

- The ordinal resolves against the live index at the moment `clear` runs (documented behaviour); an out-of-range ordinal errors cleanly.

- Removal is a real git file deletion, never a side effect of a read. Escape dynamic output with `_cli._common.e()`.
<!-- sq:body:end -->

## Subtasks

_Add with `sq task 384 add-subtask "<title>"`; track with `sq task 384 subtask <n> update --status <Status>`._

<!-- sq:summary -->
| Subtask | Status | Assignee | Title | Story |
| --- | --- | --- | --- | --- |
| ST1 | Done |  | sq board post -m [--until]; attributable author | US1 |
| ST2 | Done |  | sq board list: ordinal, author, posted-at, expiry | US3 |
| ST3 | Done |  | sq board clear <n>: resolve ordinal to hash id; clean out-of-range | US4 |
<!-- sq:summary:end -->

<!-- sq:subtasks -->

<!-- sq:subtask:ST1 -->
### ST1 — sq board post -m [--until]; attributable author

<!-- sq:subtask:ST1:head -->
**Status:** 🟢 Done
**Implements:** US1 — As a lead or operator, I can post a notice to the board with an optional expiry so the team sees it
<!-- sq:subtask:ST1:head:end -->

<!-- sq:subtask:ST1:body -->
`post` creates the notice via the storage layer with author (operator `--as op-<slug>` or agent role), posted-at, optional `--until` expiry, and body; regenerates the index.
<!-- sq:subtask:ST1:body:end -->

#### Discussion

<!-- sq:subtask:ST1:discussion -->
<!-- sq:subtask:ST1:discussion:end -->
<!-- sq:subtask:ST1:end -->

<!-- sq:subtask:ST2 -->
### ST2 — sq board list: ordinal, author, posted-at, expiry

<!-- sq:subtask:ST2:head -->
**Status:** 🟢 Done
**Implements:** US3 — As anyone, I can list current notices to see what's active
<!-- sq:subtask:ST2:head:end -->

<!-- sq:subtask:ST2:body -->
`list` shows unexpired notices with the positional ordinal (entry-line position in the generated index, header excluded), author, posted-at, and expiry if set. Expired filtered out; listing never mutates git-tracked files.
<!-- sq:subtask:ST2:body:end -->

#### Discussion

<!-- sq:subtask:ST2:discussion -->
<!-- sq:subtask:ST2:discussion:end -->
<!-- sq:subtask:ST2:end -->

<!-- sq:subtask:ST3 -->
### ST3 — sq board clear <n>: resolve ordinal to hash id; clean out-of-range

<!-- sq:subtask:ST3:head -->
**Status:** 🟢 Done
**Implements:** US4 — As a lead or operator, I can clear a notice that no longer applies
<!-- sq:subtask:ST3:head:end -->

<!-- sq:subtask:ST3:body -->
`clear <n>` resolves the n-th entry line of the live `squads/board/.index.jsonl` to the notice's stable hash id and removes its file (real deletion). An out-of-range ordinal errors cleanly.
<!-- sq:subtask:ST3:body:end -->

#### Discussion

<!-- sq:subtask:ST3:discussion -->
<!-- sq:subtask:ST3:discussion:end -->
<!-- sq:subtask:ST3:end -->
<!-- sq:subtasks:end -->

## Discussion

<!-- sq:discussion -->
- [2026-07-15T10:31:21Z] Catherine Manager:
  - Dispatching @python-dev on the board CLI. sq board post/list/clear on the BoardMixin (board is team-scoped — NO positional role, unlike sq memory <role>). post -m + --until + --as author; list shows ordinal/author/posted-at/expiry; clear <n>. Take Ready→InProgress; hand to InReview.
- [2026-07-15T10:35:07Z] Elias Python:
  - Implemented sq board post/list/clear (src/squads/_cli/_board.py), registered in _cli/__init__.py. Team-scoped, no positional role.
  - Gates clean: pyright, ruff check/format, tests/meta (23), targeted CLI tests (7). sq check clean.
  - Moving to InReview.
<!-- sq:discussion:end -->
