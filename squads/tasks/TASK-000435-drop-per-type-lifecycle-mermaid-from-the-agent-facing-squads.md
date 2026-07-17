---
id: TASK-435
sequence_id: 435
type: task
title: Drop per-type lifecycle mermaid from the agent-facing squads skill
status: Done
author: tech-lead
refs:
- FEAT-377:addresses
description: 'Skill-only: drop the 7 per-type lifecycle stateDiagram-v2 blocks from
  the squads skill; keep them in sq workflow'
created_at: '2026-07-16T16:03:20Z'
updated_at: '2026-07-17T11:46:06Z'
---
<!-- sq:body -->
## Goal

Trim the mermaid diagrams from the agent-facing `squads` skill. Drop the 7 per-type lifecycle `stateDiagram-v2` blocks from the `squads` **skill only**; keep them in the `sq workflow` terminal output.

## Scope

- Remove the 7 per-type lifecycle `stateDiagram-v2` blocks from the agent-facing `squads` skill render.
- **Keep** them in `sq workflow` terminal output (unchanged).
- **Keep** in the skill: the small hierarchy `flowchart TD` and the compact one-line lifecycle table.

## Rationale

- The skill is read by agents as raw text — mermaid does not render there, so the diagram source is noise.
- The per-type diagrams are ~200 lines and triplicated (epic/feature/task are byte-identical).
- The one-line lifecycle table already conveys the same statuses + transitions.

## Implementation note

`src/squads/_rendering/templates/workflow.md.j2` is currently **shared** by the `squads` skill and `sq workflow`. This needs a **template split or a context flag** so the skill variant omits the per-type diagrams while `sq workflow` keeps them.

## Acceptance criteria

- The agent-facing `squads` skill no longer contains the per-type lifecycle `stateDiagram-v2` blocks; it retains the hierarchy `flowchart TD` and the one-line lifecycle table.
- `sq workflow` terminal output still shows the per-type lifecycle diagrams.
- Goldens/tests for the skill render are regenerated/updated; a test verifies `sq workflow` still emits the diagrams.
- CHANGELOG note added for the skill trim.

Follow-up to FEAT-377 (which added the diagrams in 0.9.0).
<!-- sq:body:end -->

## Subtasks

_Add with `sq task 435 add-subtask "<title>"`; track with `sq task 435 subtask <n> update --status <Status>`._

<!-- sq:summary -->
<!-- sq:summary:end -->

<!-- sq:subtasks -->
<!-- sq:subtasks:end -->

## Discussion

<!-- sq:discussion -->
- [2026-07-16T16:04:16Z] Pierre Chat:
  - My call: the per-type lifecycle mermaid diagrams don't belong in the agent-facing squads skill — agents read it as raw text (mermaid doesn't render there), it's ~200 lines of triplicated content (epic/feature/task are byte-identical), and the one-line lifecycle table already conveys the same statuses+transitions. Drop those 7 stateDiagram blocks from the SKILL only; keep them in sq workflow, and keep the hierarchy flowchart + lifecycle table in the skill.
- [2026-07-17T09:42:27Z] Elias Python:
  - Split workflow.md.j2 via a for_skill render flag (set true only in squads_skill.md.j2's include; sq workflow/AGENTS.md unaffected).
  - Skill: 0 stateDiagram-v2, hierarchy flowchart + lifecycle table retained. sq workflow: still emits all 7 per-type diagrams (verified + test-covered).
  - Regenerated the dogfood squads skill via sq sync, refreshed templates_manifest.json (mid-cycle 0.9.0 key), added a skill-content test, CHANGELOG note added.
  - @reviewer ready for review.
<!-- sq:discussion:end -->
