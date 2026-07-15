---
id: TASK-381
sequence_id: 381
type: task
title: 'sq-memory skill: memory workflow and curation discipline'
status: InReview
parent: FEAT-315
author: tech-lead
assignee: python-dev
description: A managed cross-role sq-memory skill teaching the workflow and curation
subentities:
- local_id: ST1
  title: Managed cross-role sq-memory skill
  status: Done
  story: US6
created_at: '2026-07-15T07:47:29Z'
updated_at: '2026-07-15T09:53:12Z'
---
<!-- sq:body -->
Add a managed `sq-memory` skill, generated like the other skills, teaching the memory workflow and curation discipline.

## Content

- Check your role's index at the start of a run; pull content on recall.

- One fact per memory; keep it small.

- Prune stale or wrong entries (`forget`) so the pool stays trustworthy.

- The boundary: personal-learned → memory; cross-cutting/announcement → the board.

## Notes

- This is cross-role behaviour surfaced to all roles, NOT a per-type `sq-<type>` skill.
<!-- sq:body:end -->

## Subtasks

_Add with `sq task 381 add-subtask "<title>"`; track with `sq task 381 subtask <n> update --status <Status>`._

<!-- sq:summary -->
| Subtask | Status | Assignee | Title | Story |
| --- | --- | --- | --- | --- |
| ST1 | Done |  | Managed cross-role sq-memory skill | US6 |
<!-- sq:summary:end -->

<!-- sq:subtasks -->

<!-- sq:subtask:ST1 -->
### ST1 — Managed cross-role sq-memory skill

<!-- sq:subtask:ST1:head -->
**Status:** 🟢 Done
**Implements:** US6 — As an agent, the sq-memory skill teaches the memory workflow and curation discipline
<!-- sq:subtask:ST1:head:end -->

<!-- sq:subtask:ST1:body -->
A managed `sq-memory` skill, generated like the other skills, documenting: check your index at run start; one fact per memory; prune stale/wrong entries; and the memory-vs-board boundary. Cross-role (surfaced to all roles), not a per-type skill.
<!-- sq:subtask:ST1:body:end -->

#### Discussion

<!-- sq:subtask:ST1:discussion -->
<!-- sq:subtask:ST1:discussion:end -->
<!-- sq:subtask:ST1:end -->
<!-- sq:subtasks:end -->

## Discussion

<!-- sq:discussion -->
- [2026-07-15T09:45:58Z] Catherine Manager:
  - Dispatching @python-dev on the sq-memory skill — a bundled, cross-role managed skill (like greeting/squads), not a per-type sq-<type> skill. Teach the memory workflow + curation discipline. Take Ready→InProgress; hand to InReview.
- [2026-07-15T09:53:08Z] Elias Python:
  - Added a managed sq-memory skill: cross-role (all roles preload it, alongside squads/greeting), not a per-type sq-<type> skill.
  - New template src/squads/_rendering/templates/agents/memory_skill.md.j2; wired in _interactions/__init__.py (MEMORY_SKILL constant + SKILL_DESCRIPTIONS + skills_for_role + bundled_skill_slugs) and _backends/_claude_code/_backend.py write_managed (same pattern as squads/greeting).
  - Teaches: check index at run start (index in, content on recall), one fact per memory, prune via forget, and the memory-vs-board boundary stated conceptually (board/FEAT-317 not built yet — no board commands documented).
  - Regenerated templates_manifest.json for the new template. Updated 2 pre-existing tests whose 'always-on skill pair' assumption (squads, greeting) is now a trio with sq-memory.
  - Gates: pyright/ruff/ruff-format clean, tests/meta green, targeted tests green, sq check clean. Moving to InReview.
<!-- sq:discussion:end -->
