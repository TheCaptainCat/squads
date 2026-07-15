---
id: TASK-385
sequence_id: 385
type: task
title: 'Board boot-surfacing: unexpired notices (content) via backend'
status: Draft
parent: FEAT-317
author: tech-lead
description: Surface current board notices content-and-all at boot through the backend
  abstraction
subentities:
- local_id: ST1
  title: Surface unexpired notices content-and-all via backend
  status: Todo
  story: US2
created_at: '2026-07-15T07:48:29Z'
updated_at: '2026-07-15T07:48:29Z'
---
<!-- sq:body -->
Surface the current board notices at role-boot through the active backend into the managed `CLAUDE.md`/`AGENTS.md` region — not hard-coded. Unlike memory (index-only), the board's notices are short and prescriptive, so they are surfaced content-and-all.

## Scope

- At boot, unexpired notices are surfaced into the agent's context through the active backend — content and all, not just an index.

- Expired notices are excluded from boot surfacing (`--until` keeps the boot payload bounded).

- An empty or all-expired board surfaces nothing.

- Goes through the backend abstraction; the AGENTS.md backend does the equivalent.
<!-- sq:body:end -->

## Subtasks

_Add with `sq task 385 add-subtask "<title>"`; track with `sq task 385 subtask <n> update --status <Status>`._

<!-- sq:summary -->
| Subtask | Status | Assignee | Title | Story |
| --- | --- | --- | --- | --- |
| ST1 | Todo |  | Surface unexpired notices content-and-all via backend | US2 |
<!-- sq:summary:end -->

<!-- sq:subtasks -->

<!-- sq:subtask:ST1 -->
### ST1 — Surface unexpired notices content-and-all via backend

<!-- sq:subtask:ST1:head -->
**Status:** ⚪ Todo
**Implements:** US2 — As any agent, current board notices are surfaced at the start of a run so I'm aware of standing notices
<!-- sq:subtask:ST1:head:end -->

<!-- sq:subtask:ST1:body -->
At boot, unexpired notices are surfaced content-and-all through the active backend into the managed region. Expired notices excluded; an empty or all-expired board surfaces nothing. Backend-neutral.
<!-- sq:subtask:ST1:body:end -->

#### Discussion

<!-- sq:subtask:ST1:discussion -->
<!-- sq:subtask:ST1:discussion:end -->
<!-- sq:subtask:ST1:end -->
<!-- sq:subtasks:end -->

## Discussion

<!-- sq:discussion -->
<!-- sq:discussion:end -->
