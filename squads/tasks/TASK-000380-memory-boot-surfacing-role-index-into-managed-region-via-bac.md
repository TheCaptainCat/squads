---
id: TASK-380
sequence_id: 380
type: task
title: 'Memory boot-surfacing: role index into managed region via backend'
status: Draft
parent: FEAT-315
author: tech-lead
description: Surface the agent's own role memory index at boot through the backend
  abstraction
subentities:
- local_id: ST1
  title: Surface role memory index (index-only) via backend
  status: Todo
  story: US2
created_at: '2026-07-15T07:47:18Z'
updated_at: '2026-07-15T07:47:19Z'
---
<!-- sq:body -->
Surface the agent's own role memory `.index.jsonl` at role-boot through the active backend into the managed `CLAUDE.md`/`AGENTS.md` region — not hard-coded. Consistent with pull-with-a-nudge: index in, content on recall.

## Scope

- The Claude Code backend includes the role's memory index (one line per memory) in its managed region; the AGENTS.md backend does the equivalent.

- Only the index is surfaced, not full bodies. Memory is slug-addressed; line position carries no meaning.

- An empty pool surfaces nothing (no noise).

- Surfacing goes through the backend abstraction so a non-Claude backend does the equivalent (invariant: don't reach into `.claude/` outside a backend).
<!-- sq:body:end -->

## Subtasks

_Add with `sq task 380 add-subtask "<title>"`; track with `sq task 380 subtask <n> update --status <Status>`._

<!-- sq:summary -->
| Subtask | Status | Assignee | Title | Story |
| --- | --- | --- | --- | --- |
| ST1 | Todo |  | Surface role memory index (index-only) via backend | US2 |
<!-- sq:summary:end -->

<!-- sq:subtasks -->

<!-- sq:subtask:ST1 -->
### ST1 — Surface role memory index (index-only) via backend

<!-- sq:subtask:ST1:head -->
**Status:** ⚪ Todo
**Implements:** US2 — As an agent, my role's memory index is surfaced at boot so relevant facts don't slip past me
<!-- sq:subtask:ST1:head:end -->

<!-- sq:subtask:ST1:body -->
At boot, the agent's own role `.index.jsonl` is surfaced into context through the active backend into the managed region — index only, slug-addressed, empty pool surfaces nothing. Backend-neutral, mirroring the managed-region writer.
<!-- sq:subtask:ST1:body:end -->

#### Discussion

<!-- sq:subtask:ST1:discussion -->
<!-- sq:subtask:ST1:discussion:end -->
<!-- sq:subtask:ST1:end -->
<!-- sq:subtasks:end -->

## Discussion

<!-- sq:discussion -->
<!-- sq:discussion:end -->
