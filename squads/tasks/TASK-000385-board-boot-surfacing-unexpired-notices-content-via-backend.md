---
id: TASK-385
sequence_id: 385
type: task
title: 'Board boot-surfacing: unexpired notices (content) via backend'
status: InReview
parent: FEAT-317
author: tech-lead
assignee: python-dev
description: Surface current board notices content-and-all at boot through the backend
  abstraction
subentities:
- local_id: ST1
  title: Surface unexpired notices content-and-all via backend
  status: Done
  story: US2
created_at: '2026-07-15T07:48:29Z'
updated_at: '2026-07-15T10:42:47Z'
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
| ST1 | Done |  | Surface unexpired notices content-and-all via backend | US2 |
<!-- sq:summary:end -->

<!-- sq:subtasks -->

<!-- sq:subtask:ST1 -->
### ST1 — Surface unexpired notices content-and-all via backend

<!-- sq:subtask:ST1:head -->
**Status:** 🟢 Done
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
- [2026-07-15T10:36:38Z] Catherine Manager:
  - Dispatching @python-dev on board boot-surfacing. Unlike memory (index-only, per-role), the board surfaces CONTENT (full unexpired notices), team-scoped, through the backend — mirror the _memory_surface seam. Expiry-filtered at read time, empty→nothing. Take Ready→InProgress; hand to InReview.
- [2026-07-15T10:42:47Z] Elias Python:
  - Board boot-surfacing done: new _backends/_board_surface.py (board_notice_lines) mirrors _memory_surface.py; both backends' write_managed call it and pass board_lines into the shared claude_section.md.j2/agents_section.md.j2 templates (team-scoped '## Board', content-and-all, omitted when empty/all-expired).
  - Tests: TestBoardBootSurfacing in tests/integration/test_backend_lifecycle_contract.py (parametrized over both backends) + fixture updates in the 3 golden/spec-derived tests that render those templates directly.
  - Regenerated templates_manifest.json (v0.8.0 entry) since both templates changed. Gates green: pyright, ruff check+format, tests/meta -n0, targeted tests. sq check clean.
<!-- sq:discussion:end -->
