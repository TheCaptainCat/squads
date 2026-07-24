---
id: FEAT-650
sequence_id: 650
type: feature
title: Push agents to load memory/board/skills on start
status: Done
author: product-owner
subentities:
- local_id: US1
  title: 'All agents: memory+board load-on-start guidance'
  status: Done
- local_id: US2
  title: 'Manager: load squads skill on start and after compaction'
  status: Done
created_at: '2026-07-24T12:50:08Z'
updated_at: '2026-07-24T13:49:42Z'
---
<!-- sq:body -->
Right now good guidance (per-role memory, the team board, the squads/sq-memory skills) exists but nothing pushes an agent to load it by default. A spawned subagent boots with its role+skills preloaded, but a main-loop coordinator (e.g. the manager) must consciously invoke skills — and no instruction does that, so correct guidance can sit inside a skill that's never loaded.

Deliver, as onboarding instructions (not code/schema):
- CLAUDE.md's managed region (templates/claude/claude_section.md.j2) AND each role sheet (templates/agents/role.md.j2) tell every agent: at the start of a run, load your own role memory (sq memory <role> list, then show relevant entries) and check the team board (sq board list).
- The manager's guidance additionally says: load the squads skill immediately at session start, and again after any context compaction (compaction drops loaded skills).

Acceptance: a fresh sq sync-rendered CLAUDE.md and every rendered role sheet under squads/agents/roles/ contain the memory+board load-on-start instruction; the manager's rendered role sheet (and/or CLAUDE.md) additionally contains the skill-load-on-start-and-after-compaction instruction.
<!-- sq:body:end -->

## User Stories

_Add with `sq feature 650 add-story "As a <role>, I want … so that …"`; track with `sq feature 650 story <n> update --status <Status>`._

<!-- sq:summary -->
| Story | Status | Assignee | Title |
| --- | --- | --- | --- |
| US1 | Done |  | All agents: memory+board load-on-start guidance |
| US2 | Done |  | Manager: load squads skill on start and after compaction |
<!-- sq:summary:end -->

<!-- sq:stories -->

<!-- sq:story:US1 -->
### US1 — All agents: memory+board load-on-start guidance

<!-- sq:story:US1:head -->
**Status:** 🟢 Done
<!-- sq:story:US1:head:end -->

<!-- sq:story:US1:body -->
Add the memory+board load-on-start instruction to CLAUDE.md's managed-region template and to the role-sheet template, so every rendered agent-facing file carries it.
<!-- sq:story:US1:body:end -->

#### Discussion

<!-- sq:story:US1:discussion -->
<!-- sq:story:US1:discussion:end -->
<!-- sq:story:US1:end -->

<!-- sq:story:US2 -->
### US2 — Manager: load squads skill on start and after compaction

<!-- sq:story:US2:head -->
**Status:** 🟢 Done
<!-- sq:story:US2:head:end -->

<!-- sq:story:US2:body -->
Add manager-specific guidance (in CLAUDE.md and/or the manager's role sheet) to load the squads skill at session start and again after any context compaction.
<!-- sq:story:US2:body:end -->

#### Discussion

<!-- sq:story:US2:discussion -->
<!-- sq:story:US2:discussion:end -->
<!-- sq:story:US2:end -->
<!-- sq:stories:end -->

## Discussion

<!-- sq:discussion -->
<!-- sq:discussion:end -->
