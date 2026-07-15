---
id: TASK-380
sequence_id: 380
type: task
title: 'Memory boot-surfacing: role index into managed region via backend'
status: InReview
parent: FEAT-315
author: tech-lead
description: Surface the agent's own role memory index at boot through the backend
  abstraction
subentities:
- local_id: ST1
  title: Surface role memory index (index-only) via backend
  status: Done
  story: US2
created_at: '2026-07-15T07:47:18Z'
updated_at: '2026-07-15T08:42:04Z'
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
| ST1 | Done |  | Surface role memory index (index-only) via backend | US2 |
<!-- sq:summary:end -->

<!-- sq:subtasks -->

<!-- sq:subtask:ST1 -->
### ST1 — Surface role memory index (index-only) via backend

<!-- sq:subtask:ST1:head -->
**Status:** 🟢 Done
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
- [2026-07-15T08:31:47Z] Catherine Manager:
  - Dispatching @python-dev on memory boot-surfacing. Surface the role's memory .index.jsonl at boot THROUGH the backend (not hard-coded) — index-only (not full bodies), slug-addressed, empty pool surfaces nothing. Take Ready→InProgress; hand to InReview.
- [2026-07-15T08:42:04Z] Elias Python:
  - Implemented: role memory index surfaces at boot through the AgentBackend ABC.
  - Seam: per-role artifacts each backend already regenerates on sq sync — the Claude Code pointer (.claude/agents/<slug>.md, via generate_role_entry) and the AGENTS.md per-role section (via write_managed, mirroring how mission text is compiled). New shared formatter squads/_backends/_memory_surface.py::memory_index_lines reads the role's generated .index.jsonl (squads/_memory/_store.py::read_index, new) and renders slug+summary bullet lines; both backends call it and pass memory_lines into their templates, rendered only when non-empty (no header noise on an empty pool).
  - Tests: tests/integration/test_backend_lifecycle_contract.py::TestMemoryBootSurfacing (parametrized over both backends) — empty pool surfaces nothing, index reaches the managed output, only summary (never body) surfaces, and a memory added after first sync only reaches output on the next regeneration (proves the backend path, not a one-off write).
  - Gates green: pyright, ruff check, ruff format --check, tests/meta -q -n0, targeted suite (backend/memory/golden tests), sq check clean. Regenerated the template manifest (pointer_agent.md.j2 + agents_section.md.j2 hashes) and added memory_lines to the AGENTS.md golden-section synthetic roster fixture.
  - Not committed per instructions.
<!-- sq:discussion:end -->
