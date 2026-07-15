---
id: TASK-393
sequence_id: 393
type: task
title: Boot directive to review memory + board before starting
status: Draft
parent: FEAT-392
author: tech-lead
subentities:
- local_id: ST1
  title: Add the boot directive to role.md.j2
  status: Todo
  story: US1
- local_id: ST2
  title: Regenerate manifest; flag golden churn
  status: Todo
  story: US1
created_at: '2026-07-15T11:47:07Z'
updated_at: '2026-07-15T11:47:28Z'
---
<!-- sq:body -->
Implements US1 of the parent feature.

## Goal

Add an always-seen directive to the role boot definition telling a spawning agent to skim its `## Your memory` index and the team `## Board`, and apply anything relevant, before starting work. Today the only such nudge lives in the on-demand `sq-memory` skill, which may not be loaded on a given spawn.

## Where

`src/squads/_rendering/templates/agents/role.md.j2` — the single template every role's generated boot content renders from, and which already carries both the memory index and the board sections. The directive belongs in the always-seen boot prose (e.g. alongside the working-agreements / "spawned as a subagent" material), not behind a skill.

## Requirements

- One short directive, in substance: before you start, review `## Your memory` and the team `## Board` and apply anything relevant.
- Serves every role (it renders from the shared template, unconditionally).
- Covers both surfaces (memory index + board) in the one directive.
- Renders cleanly whether or not the pool/board is empty — either it stands unconditionally over empty sections, or it is phrased to no-op gracefully when there is nothing there. Implementer's call.
- Keep it terse.

## Artifacts to regenerate / flag

- Regenerate `templates_manifest.json` (this is a mid-cycle template change).
- The `list` command and managed-section goldens may need refreshing once the boot text changes — flag any golden churn for the main loop to verify against the full suite rather than silently rewriting expectations.

## Verify

- Fresh init renders the directive in the generated role boot content for every role.
- Renders with an empty memory pool and an empty board without dangling/awkward output.
<!-- sq:body:end -->

## Subtasks

_Add with `sq task 393 add-subtask "<title>"`; track with `sq task 393 subtask <n> update --status <Status>`._

<!-- sq:summary -->
| Subtask | Status | Assignee | Title | Story |
| --- | --- | --- | --- | --- |
| ST1 | Todo |  | Add the boot directive to role.md.j2 | US1 |
| ST2 | Todo |  | Regenerate manifest; flag golden churn | US1 |
<!-- sq:summary:end -->

<!-- sq:subtasks -->

<!-- sq:subtask:ST1 -->
### ST1 — Add the boot directive to role.md.j2

<!-- sq:subtask:ST1:head -->
**Status:** ⚪ Todo
**Implements:** US1 — Boot directive: review memory + board before starting
<!-- sq:subtask:ST1:head:end -->

<!-- sq:subtask:ST1:body -->
Add the always-seen 'review your memory + the board before starting, apply what's relevant' directive to the shared role boot template. Covers both surfaces in one line; must render cleanly with an empty memory pool and empty board.
<!-- sq:subtask:ST1:body:end -->

#### Discussion

<!-- sq:subtask:ST1:discussion -->
<!-- sq:subtask:ST1:discussion:end -->
<!-- sq:subtask:ST1:end -->

<!-- sq:subtask:ST2 -->
### ST2 — Regenerate manifest; flag golden churn

<!-- sq:subtask:ST2:head -->
**Status:** ⚪ Todo
**Implements:** US1 — Boot directive: review memory + board before starting
<!-- sq:subtask:ST2:head:end -->

<!-- sq:subtask:ST2:body -->
Regenerate templates_manifest.json (mid-cycle template change). If the list command or managed-section goldens shift from the new boot text, flag the churn for the main loop to verify against the full suite rather than rewriting expectations blindly.
<!-- sq:subtask:ST2:body:end -->

#### Discussion

<!-- sq:subtask:ST2:discussion -->
<!-- sq:subtask:ST2:discussion:end -->
<!-- sq:subtask:ST2:end -->
<!-- sq:subtasks:end -->

## Discussion

<!-- sq:discussion -->
<!-- sq:discussion:end -->
