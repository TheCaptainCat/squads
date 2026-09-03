---
id: TASK-654
sequence_id: 654
type: task
title: Push memory/board/skill load-on-start into agent onboarding surfaces
status: Done
parent: FEAT-650
author: tech-lead
subentities:
- local_id: ST1
  title: 'All agents: memory+board load-on-start in CLAUDE.md/AGENTS.md + role sheet'
  status: Done
  story: US1
- local_id: ST2
  title: 'Manager: load squads skill on start + after compaction'
  status: Done
  story: US2
created_at: '2026-07-24T13:06:23Z'
updated_at: '2026-07-24T13:49:22Z'
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

<!-- sq:subtasks -->

<!-- sq:subtask:ST1 -->
### ST1 — All agents: memory+board load-on-start in CLAUDE.md/AGENTS.md + role sheet

<!-- sq:subtask:ST1:body -->
Added memory+board load-on-start to CLAUDE.md/AGENTS.md managed regions (new Start of a run section) and refined role.md.j2's existing line to also mention sq memory show <slug>.
<!-- sq:subtask:ST1:body:end -->

#### Discussion

<!-- sq:subtask:ST1:discussion -->
<!-- sq:subtask:ST1:discussion:end -->
<!-- sq:subtask:ST1:end -->

<!-- sq:subtask:ST2 -->
### ST2 — Manager: load squads skill on start + after compaction

<!-- sq:subtask:ST2:body -->
Added skill-load-on-start-and-after-compaction line to the Orchestration loop section of claude_section.md.j2 (read unconditionally every session, unlike a skill).
<!-- sq:subtask:ST2:body:end -->

#### Discussion

<!-- sq:subtask:ST2:discussion -->
<!-- sq:subtask:ST2:discussion:end -->
<!-- sq:subtask:ST2:end -->
<!-- sq:subtasks:end -->

## Discussion

<!-- sq:discussion -->
- [2026-07-24T13:39:42Z] Elias Python:
  - ST1: added a terse 'Start of a run' section (memory list/show + board list) to claude_section.md.j2 and agents_section.md.j2; refined role.md.j2's existing memory/board line to also mention 'sq memory <slug> show <slug>'.
  - ST2: added the squads-skill-load-on-start-and-after-compaction line to the Orchestration loop section of claude_section.md.j2 (chosen home: it's read unconditionally every session, unlike a skill, which is what makes the after-compaction reminder work).
  - Regenerated templates_manifest.json + goldens (claude_md_section.txt, agents_md_section.txt); verified fresh sq init + sq sync render the new lines in CLAUDE.md, AGENTS.md, and role sheets. pyright/ruff/format clean; touched test files green. sq sync'd this repo's own squad; sq check clean.
  - @reviewer ready for review.
- [2026-07-24T13:49:17Z] Paul Reviewer:
  - Verified: CLAUDE.md/AGENTS.md 'Start of a run' + orchestration-loop skill-load line + role-sheet memory/board line; ST2 correctly placed in the always-loaded CLAUDE.md (survives compaction). Manifest + goldens regenerated; fresh-init render confirmed; full suite green.
<!-- sq:discussion:end -->
