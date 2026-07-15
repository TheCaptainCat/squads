---
id: TASK-379
sequence_id: 379
type: task
title: 'Memory CLI: sq memory <role> list/search/show/add/forget'
status: InReview
parent: FEAT-315
author: tech-lead
description: The sq memory command group, role as a positional subject over the storage
  layer
subentities:
- local_id: ST1
  title: sq memory <role> add [--file]
  status: Done
  story: US1
- local_id: ST2
  title: sq memory <role> list / search <query> / show <slug>
  status: Done
  story: US3
- local_id: ST3
  title: sq memory <role> forget <slug>; clean errors
  status: Done
  story: US4
created_at: '2026-07-15T07:47:00Z'
updated_at: '2026-07-15T08:27:56Z'
---
<!-- sq:body -->
Build the `sq memory <role> ...` command group over the memory storage layer. Role is a positional subject, consistent with `sq inbox <role>` / `sq mine <role>`.

## Commands

- `sq memory <role> add "<fact>" [--file f]` — jot a memory (delegates to the storage add; regenerates the index).

- `sq memory <role> list` — print the role's `.index.jsonl` entries (one line per memory: slug, filename, description).

- `sq memory <role> search <query>` — return memories whose content matches (plain content search over the `.md` files).

- `sq memory <role> show <slug>` — print one memory's full body, addressed by slug (not by index position).

- `sq memory <role> forget <slug>` — prune a memory.

## Notes

- An unknown role or slug raises a clean `SquadsError` (via `@handle_errors`), never a stack trace.

- Escape dynamic output with `_cli._common.e()` when printing content strings.
<!-- sq:body:end -->

## Subtasks

_Add with `sq task 379 add-subtask "<title>"`; track with `sq task 379 subtask <n> update --status <Status>`._

<!-- sq:summary -->
| Subtask | Status | Assignee | Title | Story |
| --- | --- | --- | --- | --- |
| ST1 | Done |  | sq memory <role> add [--file] | US1 |
| ST2 | Done |  | sq memory <role> list / search <query> / show <slug> | US3 |
| ST3 | Done |  | sq memory <role> forget <slug>; clean errors | US4 |
<!-- sq:summary:end -->

<!-- sq:subtasks -->

<!-- sq:subtask:ST1 -->
### ST1 — sq memory <role> add [--file]

<!-- sq:subtask:ST1:head -->
**Status:** 🟢 Done
**Implements:** US1 — As an agent, I can jot a small learned fact to my role's memory so it persists for future runs
<!-- sq:subtask:ST1:head:end -->

<!-- sq:subtask:ST1:body -->
Wire `add` to the storage layer: create the slug-named file and regenerate the index. `--file` reads a raw-markdown body from a path ('-' = stdin).
<!-- sq:subtask:ST1:body:end -->

#### Discussion

<!-- sq:subtask:ST1:discussion -->
<!-- sq:subtask:ST1:discussion:end -->
<!-- sq:subtask:ST1:end -->

<!-- sq:subtask:ST2 -->
### ST2 — sq memory <role> list / search <query> / show <slug>

<!-- sq:subtask:ST2:head -->
**Status:** 🟢 Done
**Implements:** US3 — As an agent, I can list, search, and show my role's memories to pull full content when relevant
<!-- sq:subtask:ST2:head:end -->

<!-- sq:subtask:ST2:body -->
`list` prints the index entries; `search` matches over content; `show <slug>` prints the full body addressed by slug, not index position.
<!-- sq:subtask:ST2:body:end -->

#### Discussion

<!-- sq:subtask:ST2:discussion -->
<!-- sq:subtask:ST2:discussion:end -->
<!-- sq:subtask:ST2:end -->

<!-- sq:subtask:ST3 -->
### ST3 — sq memory <role> forget <slug>; clean errors

<!-- sq:subtask:ST3:head -->
**Status:** 🟢 Done
**Implements:** US4 — As an agent or operator, I can prune a stale or wrong memory so the pool stays trustworthy
<!-- sq:subtask:ST3:head:end -->

<!-- sq:subtask:ST3:body -->
`forget <slug>` prunes a memory. An unknown role or slug raises a clean `SquadsError`, not a stack trace.
<!-- sq:subtask:ST3:body:end -->

#### Discussion

<!-- sq:subtask:ST3:discussion -->
<!-- sq:subtask:ST3:discussion:end -->
<!-- sq:subtask:ST3:end -->
<!-- sq:subtasks:end -->

## Discussion

<!-- sq:discussion -->
- [2026-07-15T08:20:49Z] Catherine Manager:
  - Dispatching @python-dev on the memory CLI now that the storage/service layer (TASK-378) is in. Wire sq memory <role> list/search/show/add/forget onto the MemoryMixin service; add memory_search (content grep) to the service/store. Take Ready→InProgress; hand to InReview.
- [2026-07-15T08:27:55Z] Elias Python:
  - Implemented sq memory <role> list/search/show/add/forget (src/squads/_cli/_memory.py) + memory_search in Service/store. pyright/ruff/format clean, sq check clean; 7 new CLI tests + full memory suite (24) green.
<!-- sq:discussion:end -->
