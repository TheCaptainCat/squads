---
id: TASK-386
sequence_id: 386
type: task
title: 'Board skill: posting discipline and memory-vs-board boundary'
status: InReview
parent: FEAT-317
author: tech-lead
assignee: python-dev
description: A managed guiding skill for board posting discipline and the boundary
subentities:
- local_id: ST1
  title: Managed board skill + memory-vs-board boundary
  status: Done
  story: US5
created_at: '2026-07-15T07:48:37Z'
updated_at: '2026-07-15T10:48:19Z'
---
<!-- sq:body -->
Add a managed guiding skill for the board, generated like the other skills.

## Content

- Keep notices short and prescriptive.

- Set `--until` so notices come down on their own.

- Clear notices when stale.

- State the boundary: cross-cutting/announcement → board; personal-learned → memory.

## Notes

- Whether this is its own `sq-board` skill or folded into the shared knowledge (`sq-memory`) skill is left to implementation.
<!-- sq:body:end -->

## Subtasks

_Add with `sq task 386 add-subtask "<title>"`; track with `sq task 386 subtask <n> update --status <Status>`._

<!-- sq:summary -->
| Subtask | Status | Assignee | Title | Story |
| --- | --- | --- | --- | --- |
| ST1 | Done |  | Managed board skill + memory-vs-board boundary | US5 |
<!-- sq:summary:end -->

<!-- sq:subtasks -->

<!-- sq:subtask:ST1 -->
### ST1 — Managed board skill + memory-vs-board boundary

<!-- sq:subtask:ST1:head -->
**Status:** 🟢 Done
**Implements:** US5 — As an agent, a guiding skill teaches board posting discipline and the memory-vs-board boundary
<!-- sq:subtask:ST1:head:end -->

<!-- sq:subtask:ST1:body -->
A managed skill documents: keep notices short and prescriptive; set `--until`; clear when stale; and the boundary (cross-cutting → board, personal-learned → memory). Own `sq-board` skill or folded into the shared knowledge skill — implementation's choice.
<!-- sq:subtask:ST1:body:end -->

#### Discussion

<!-- sq:subtask:ST1:discussion -->
<!-- sq:subtask:ST1:discussion:end -->
<!-- sq:subtask:ST1:end -->
<!-- sq:subtasks:end -->

## Discussion

<!-- sq:discussion -->
- [2026-07-15T10:44:15Z] Catherine Manager:
  - Dispatching @python-dev on the board guiding skill. Per FEAT-317 US5 you may make it its own sq-board skill OR fold into the existing sq-memory skill — your call; keep it coherent and don't duplicate the memory-vs-board boundary (state it once). Take Ready→InProgress; hand to InReview.
- [2026-07-15T10:48:19Z] Elias Python:
  - Folded board guidance into sq-memory (option b) rather than a dedicated sq-board skill — minimal churn, no new bundled-skill wiring, and the SKILL_DESCRIPTIONS text already anticipated a shared 'memory-vs-board boundary' skill. Added a board section (short/prescriptive, --until, clear-when-stale, command surface) after the existing boundary section, referencing it rather than restating it. Regenerated templates_manifest.json (mid-cycle, in-place) and ran sq sync to refresh the dogfood repo's own sq-memory skill files. Gates: pyright/ruff/format clean, tests/meta clean, targeted tests green, sq check clean.
<!-- sq:discussion:end -->
