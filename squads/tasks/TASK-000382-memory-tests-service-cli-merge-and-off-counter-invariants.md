---
id: TASK-382
sequence_id: 382
type: task
title: 'Memory tests: service + CLI, merge and off-counter invariants'
status: Draft
parent: FEAT-315
author: tech-lead
description: Service + CLI coverage for memory incl. merge behaviour and off-counter/outside-.squads.json
  invariants
subentities:
- local_id: ST1
  title: Test add writes file + regenerates index; no counter allocation
  status: Todo
  story: US1
- local_id: ST2
  title: Test list/search/show and slug addressing
  status: Todo
  story: US3
- local_id: ST3
  title: Test forget deletes + regenerates; clean error on missing slug
  status: Todo
  story: US4
- local_id: ST4
  title: Test independent-branch merge + outside-.squads.json + repair
  status: Todo
  story: US5
created_at: '2026-07-15T07:47:41Z'
updated_at: '2026-07-15T07:47:44Z'
---
<!-- sq:body -->
Cover the memory behaviour through the service and CLI, per the repo testing conventions (all file generation in tmp dirs; assert generated files — valid frontmatter, JSONL header + entry lines, preserved bodies).

## Coverage

- **add** creates a slug-named file and regenerates the index; assert no global-counter allocation (counter unchanged).

- **list / search / show** behave as specified; `show` is slug-addressed, not index-position.

- **forget** deletes the file and regenerates the index; a missing slug raises a clean error.

- **Merge / invariants** — two independent adds produce separate files (no conflict); memory lives outside `.squads.json` and `sq repair` neither rebuilds nor disturbs it.
<!-- sq:body:end -->

## Subtasks

_Add with `sq task 382 add-subtask "<title>"`; track with `sq task 382 subtask <n> update --status <Status>`._

<!-- sq:summary -->
| Subtask | Status | Assignee | Title | Story |
| --- | --- | --- | --- | --- |
| ST1 | Todo |  | Test add writes file + regenerates index; no counter allocation | US1 |
| ST2 | Todo |  | Test list/search/show and slug addressing | US3 |
| ST3 | Todo |  | Test forget deletes + regenerates; clean error on missing slug | US4 |
| ST4 | Todo |  | Test independent-branch merge + outside-.squads.json + repair | US5 |
<!-- sq:summary:end -->

<!-- sq:subtasks -->

<!-- sq:subtask:ST1 -->
### ST1 — Test add writes file + regenerates index; no counter allocation

<!-- sq:subtask:ST1:head -->
**Status:** ⚪ Todo
**Implements:** US1 — As an agent, I can jot a small learned fact to my role's memory so it persists for future runs
<!-- sq:subtask:ST1:head:end -->

<!-- sq:subtask:ST1:body -->
Add creates `<slug>.md` with light frontmatter and regenerates `.index.jsonl` (header line + one entry). Assert the global counter is not advanced.
<!-- sq:subtask:ST1:body:end -->

#### Discussion

<!-- sq:subtask:ST1:discussion -->
<!-- sq:subtask:ST1:discussion:end -->
<!-- sq:subtask:ST1:end -->

<!-- sq:subtask:ST2 -->
### ST2 — Test list/search/show and slug addressing

<!-- sq:subtask:ST2:head -->
**Status:** ⚪ Todo
**Implements:** US3 — As an agent, I can list, search, and show my role's memories to pull full content when relevant
<!-- sq:subtask:ST2:head:end -->

<!-- sq:subtask:ST2:body -->
`list` reflects the index entries; `search` matches content; `show <slug>` returns the right body by slug, independent of line position.
<!-- sq:subtask:ST2:body:end -->

#### Discussion

<!-- sq:subtask:ST2:discussion -->
<!-- sq:subtask:ST2:discussion:end -->
<!-- sq:subtask:ST2:end -->

<!-- sq:subtask:ST3 -->
### ST3 — Test forget deletes + regenerates; clean error on missing slug

<!-- sq:subtask:ST3:head -->
**Status:** ⚪ Todo
**Implements:** US4 — As an agent or operator, I can prune a stale or wrong memory so the pool stays trustworthy
<!-- sq:subtask:ST3:head:end -->

<!-- sq:subtask:ST3:body -->
`forget` removes the file and rewrites the index; forgetting an unknown slug raises a clean `SquadsError`.
<!-- sq:subtask:ST3:body:end -->

#### Discussion

<!-- sq:subtask:ST3:discussion -->
<!-- sq:subtask:ST3:discussion:end -->
<!-- sq:subtask:ST3:end -->

<!-- sq:subtask:ST4 -->
### ST4 — Test independent-branch merge + outside-.squads.json + repair

<!-- sq:subtask:ST4:head -->
**Status:** ⚪ Todo
**Implements:** US5 — As a teammate, committed per-role memory arrives on checkout and merges cleanly across branches
<!-- sq:subtask:ST4:head:end -->

<!-- sq:subtask:ST4:body -->
Two distinct memories written independently coexist as separate files (no conflict). Memory sits outside `.squads.json`; `sq repair` leaves memory files and the index untouched.
<!-- sq:subtask:ST4:body:end -->

#### Discussion

<!-- sq:subtask:ST4:discussion -->
<!-- sq:subtask:ST4:discussion:end -->
<!-- sq:subtask:ST4:end -->
<!-- sq:subtasks:end -->

## Discussion

<!-- sq:discussion -->
<!-- sq:discussion:end -->
