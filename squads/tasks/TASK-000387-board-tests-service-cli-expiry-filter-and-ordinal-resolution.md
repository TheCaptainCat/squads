---
id: TASK-387
sequence_id: 387
type: task
title: 'Board tests: service + CLI, expiry filter and ordinal resolution'
status: Draft
parent: FEAT-317
author: tech-lead
description: Service + CLI coverage for the board incl. expiry filtering, positional
  ordinal, off-counter invariants
subentities:
- local_id: ST1
  title: Test post writes notice + hash id + index; distinct ids
  status: Todo
  story: US1
- local_id: ST2
  title: Test list ordinal; expired filtered; no spurious diffs
  status: Todo
  story: US3
- local_id: ST3
  title: Test clear resolves ordinal to hash and deletes; out-of-range error
  status: Todo
  story: US4
- local_id: ST4
  title: Test boot surfacing excludes expired; empty surfaces nothing
  status: Todo
  story: US2
created_at: '2026-07-15T07:48:50Z'
updated_at: '2026-07-15T07:48:53Z'
---
<!-- sq:body -->
Cover the board behaviour through the service and CLI, per the repo testing conventions (all file generation in tmp dirs; assert generated files — valid frontmatter, JSONL header + entry lines, no spurious diffs on read).

## Coverage

- **post** writes a notice with a short-hash id and regenerates the index; assert no global-counter allocation; distinct ids across independent posts.

- **list** shows unexpired notices with the positional ordinal; expired notices are filtered out at read time; listing produces no git diffs.

- **clear <n>** resolves the n-th entry line of the live index to the hash id and deletes the file; an out-of-range ordinal errors cleanly.

- **boot surfacing** excludes expired notices; an empty or all-expired board surfaces nothing. Board lives outside `.squads.json`; `sq repair` ignores it.
<!-- sq:body:end -->

## Subtasks

_Add with `sq task 387 add-subtask "<title>"`; track with `sq task 387 subtask <n> update --status <Status>`._

<!-- sq:summary -->
| Subtask | Status | Assignee | Title | Story |
| --- | --- | --- | --- | --- |
| ST1 | Todo |  | Test post writes notice + hash id + index; distinct ids | US1 |
| ST2 | Todo |  | Test list ordinal; expired filtered; no spurious diffs | US3 |
| ST3 | Todo |  | Test clear resolves ordinal to hash and deletes; out-of-range error | US4 |
| ST4 | Todo |  | Test boot surfacing excludes expired; empty surfaces nothing | US2 |
<!-- sq:summary:end -->

<!-- sq:subtasks -->

<!-- sq:subtask:ST1 -->
### ST1 — Test post writes notice + hash id + index; distinct ids

<!-- sq:subtask:ST1:head -->
**Status:** ⚪ Todo
**Implements:** US1 — As a lead or operator, I can post a notice to the board with an optional expiry so the team sees it
<!-- sq:subtask:ST1:head:end -->

<!-- sq:subtask:ST1:body -->
Post writes a notice `.md` with a short-hash id and regenerates `.index.jsonl`. Assert the global counter is not advanced and independent posts get distinct ids (no merge collision).
<!-- sq:subtask:ST1:body:end -->

#### Discussion

<!-- sq:subtask:ST1:discussion -->
<!-- sq:subtask:ST1:discussion:end -->
<!-- sq:subtask:ST1:end -->

<!-- sq:subtask:ST2 -->
### ST2 — Test list ordinal; expired filtered; no spurious diffs

<!-- sq:subtask:ST2:head -->
**Status:** ⚪ Todo
**Implements:** US3 — As anyone, I can list current notices to see what's active
<!-- sq:subtask:ST2:head:end -->

<!-- sq:subtask:ST2:body -->
`list` shows unexpired notices with the correct entry-line ordinal (header excluded); expired notices are filtered at read time; listing mutates no git-tracked files.
<!-- sq:subtask:ST2:body:end -->

#### Discussion

<!-- sq:subtask:ST2:discussion -->
<!-- sq:subtask:ST2:discussion:end -->
<!-- sq:subtask:ST2:end -->

<!-- sq:subtask:ST3 -->
### ST3 — Test clear resolves ordinal to hash and deletes; out-of-range error

<!-- sq:subtask:ST3:head -->
**Status:** ⚪ Todo
**Implements:** US4 — As a lead or operator, I can clear a notice that no longer applies
<!-- sq:subtask:ST3:head:end -->

<!-- sq:subtask:ST3:body -->
`clear <n>` resolves the n-th live entry line to the hash id and removes the file (real deletion); an out-of-range ordinal raises a clean error.
<!-- sq:subtask:ST3:body:end -->

#### Discussion

<!-- sq:subtask:ST3:discussion -->
<!-- sq:subtask:ST3:discussion:end -->
<!-- sq:subtask:ST3:end -->

<!-- sq:subtask:ST4 -->
### ST4 — Test boot surfacing excludes expired; empty surfaces nothing

<!-- sq:subtask:ST4:head -->
**Status:** ⚪ Todo
**Implements:** US2 — As any agent, current board notices are surfaced at the start of a run so I'm aware of standing notices
<!-- sq:subtask:ST4:head:end -->

<!-- sq:subtask:ST4:body -->
Boot surfacing includes unexpired notice content and excludes expired ones; an empty or all-expired board surfaces nothing. Board sits outside `.squads.json`; `sq repair` ignores it.
<!-- sq:subtask:ST4:body:end -->

#### Discussion

<!-- sq:subtask:ST4:discussion -->
<!-- sq:subtask:ST4:discussion:end -->
<!-- sq:subtask:ST4:end -->
<!-- sq:subtasks:end -->

## Discussion

<!-- sq:discussion -->
<!-- sq:discussion:end -->
