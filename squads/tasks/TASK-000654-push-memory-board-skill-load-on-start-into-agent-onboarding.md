---
id: TASK-654
sequence_id: 654
type: task
title: Push memory/board/skill load-on-start into agent onboarding surfaces
status: Draft
parent: FEAT-650
author: tech-lead
subentities:
- local_id: ST1
  title: 'All agents: memory+board load-on-start in CLAUDE.md/AGENTS.md + role sheet'
  status: Todo
  story: US1
- local_id: ST2
  title: 'Manager: load squads skill on start + after compaction'
  status: Todo
  story: US2
created_at: '2026-07-24T13:06:23Z'
updated_at: '2026-07-24T13:07:30Z'
---
<!-- sq:body -->
Push the load-on-start practice into the agent-facing onboarding surfaces so every agent — and the main-loop coordinator, which boots without auto-loaded skills — reads it by default.

## Scope

Agent-facing prose only, edited in the generated-file `.j2` templates (never in rendered output — `sq sync` clobbers hand-edits). No schema bump. Keep pyright/ruff clean. Keep the prose terse and non-narrating: describe the practice, no build-process references.

Two subtasks map to the feature's stories (ST1→US1, ST2→US2).

## Files

- `src/squads/_rendering/templates/claude/claude_section.md.j2` — CLAUDE.md managed region.
- `src/squads/_rendering/templates/agents_md/agents_section.md.j2` — AGENTS.md equivalent managed region.
- `src/squads/_rendering/templates/agents/role.md.j2` — the shared role-sheet template.
- Greeting skill `SKILL-000192` (`squads/agents/skills/SKILL-000192-greeting.md`) — a candidate home for the manager-specific start/after-compaction skill-load guidance; implementer confirms whether it lands here or in the CLAUDE.md/AGENTS.md managed region alongside the orchestration-loop/greeting guidance.

## Regeneration / test upkeep (implementer must handle)

- After editing templates, run `sq sync` and confirm the rendered CLAUDE.md, AGENTS.md, and every role sheet under `squads/agents/roles/` carry the new guidance.
- Regenerate the template manifest via `scripts/gen_template_manifest.py` and update any golden fixtures for the managed sections / role sheets so the suite stays green. (The manifest-release gotcha — checking out the prior release's manifest entry — only applies at release-cut, not to this change.)
- Confirm the guidance surfaces in a freshly `sq init`'d project: the generated CLAUDE.md + role sheets carry it.
- Full gate as `uv run --all-extras` (pyright/ruff/pytest); a bare `uv run` prunes the tui extra.

Leave Draft/Todo — do not promote.
<!-- sq:body:end -->

## Subtasks

_Add with `sq task 654 add-subtask "<title>"`; track with `sq task 654 subtask <n> update --status <Status>`._

<!-- sq:summary -->
| Subtask | Status | Assignee | Title | Story |
| --- | --- | --- | --- | --- |
| ST1 | Todo |  | All agents: memory+board load-on-start in CLAUDE.md/AGENTS.md + role sheet | US1 |
| ST2 | Todo |  | Manager: load squads skill on start + after compaction | US2 |
<!-- sq:summary:end -->

<!-- sq:subtasks -->

<!-- sq:subtask:ST1 -->
### ST1 — All agents: memory+board load-on-start in CLAUDE.md/AGENTS.md + role sheet

<!-- sq:subtask:ST1:head -->
**Status:** ⚪ Todo
**Implements:** US1 — All agents: memory+board load-on-start guidance
<!-- sq:subtask:ST1:head:end -->

<!-- sq:subtask:ST1:body -->
Add explicit start-of-run guidance to the shared agent-facing surfaces: the CLAUDE.md managed-region template (src/squads/_rendering/templates/claude/claude_section.md.j2), the AGENTS.md equivalent (.../agents_md/agents_section.md.j2), and the role-sheet template (.../agents/role.md.j2). Guidance: at the start of a run, load your role memory (`sq memory <role> list`, then `show` the relevant entries) and check the team board (`sq board list`). Durable text goes in the .j2 templates — rendered CLAUDE.md/role sheets are clobbered by sq sync. Regenerate + update the template manifest and golden fixtures.
<!-- sq:subtask:ST1:body:end -->

#### Discussion

<!-- sq:subtask:ST1:discussion -->
<!-- sq:subtask:ST1:discussion:end -->
<!-- sq:subtask:ST1:end -->

<!-- sq:subtask:ST2 -->
### ST2 — Manager: load squads skill on start + after compaction

<!-- sq:subtask:ST2:head -->
**Status:** ⚪ Todo
**Implements:** US2 — Manager: load squads skill on start and after compaction
<!-- sq:subtask:ST2:head:end -->

<!-- sq:subtask:ST2:body -->
Add manager-specific guidance that the manager loads the `squads` skill immediately at session start AND again after a context compaction (compaction drops loaded skills). Home: the CLAUDE.md/AGENTS.md managed region where the orchestration-loop/greeting guidance lives, or the greeting skill SKILL-000192 — implementer confirms the right home. Same regeneration/manifest/golden upkeep as ST1 if a managed template is touched.
<!-- sq:subtask:ST2:body:end -->

#### Discussion

<!-- sq:subtask:ST2:discussion -->
<!-- sq:subtask:ST2:discussion:end -->
<!-- sq:subtask:ST2:end -->
<!-- sq:subtasks:end -->

## Discussion

<!-- sq:discussion -->
<!-- sq:discussion:end -->
