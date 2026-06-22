---
id: TASK-000055
sequence_id: 55
type: task
title: Onboarding texts direct to sq commands, not squads/ file paths
status: Done
parent: FEAT-000041
author: tech-lead
assignee: python-dev
priority: high
subentities:
- local_id: ST1
  title: Rewrite CLAUDE.md impersonation paragraph to direct to sq role show
  status: Done
  story: US2
created_at: '2026-06-12T07:52:37Z'
updated_at: '2026-06-23T09:58:03Z'
---
<!-- sq:body -->
## Goal
Every agent-facing onboarding *instruction* in generated content must teach an `sq` command, not a path under `squads/`. The rule: **machinery may use paths; instructions teach commands.** This matters for remote mode (FEAT-000033), where there is no filesystem to detour to.

## Confirmed sweep (done during breakdown)
The **only** offender is the generated CLAUDE.md section template:
- `src/squads/_rendering/templates/claude/claude_section.md.j2`, lines 43–44 (Impersonation paragraph): 'load their role definition from `{{ squad_dir }}/agents/roles/`'. Replace with guidance to run `sq role show <slug>` (resolve by name/slug, then `sq role show`).
- Clean (verified, no change needed): the `squads`, `greeting`, `skill`, `item_skill`, `operator` skill templates, the `workflow.md.j2` cheatsheet, and the role catalog source bodies — none contain a path-read onboarding instruction.

## Exempt (do NOT touch)
- `src/squads/_rendering/templates/claude/pointer_agent.md.j2` — the `@{{ squad_path }}` include is backend plumbing (how Claude Code boots a subagent), not agent guidance.

## Gap to note, not invent (per scope)
- `sq skill show` already exists but prints only metadata (id/slug/status/file/when-to-use), **not the skill body**. The CLAUDE.md text already names skills by handle (`squads`/`greeting`) rather than by path, so no instruction currently sends agents to a skill file — but if a 'read your skill' instruction is wanted in future, `sq skill show` would need to render the body first. Record this as a candidate follow-up; do NOT expand `sq skill show` in this task unless a path-read instruction is found that requires it.

## Propagation
- After editing the template, `sq sync` regenerates the CLAUDE.md section in this repo. The CLAUDE.md change is a regenerated artifact, not a hand-edit.

## Acceptance (US2)
- The generated CLAUDE.md section contains no agent-facing instruction to read files under `squads/` for content an sq command provides; pointer files unchanged.
- A grep for 'squads/agents/roles' in agent-facing *generated text* (excluding pointer files) comes back empty.
- An agent following only the onboarding texts can brief on their role with zero file reads (replay the live scenario through `sq role show` — depends on TASK-000054).

## Tests
- Assert the rendered CLAUDE.md section mentions `sq role show` and does not contain `agents/roles`.
- CLI/integration smoke that `sq sync` propagates the change.
<!-- sq:body:end -->

## Subtasks

_Add with `sq task 55 add-subtask "<title>"`; track with `sq task 55 subtask <n> update --status <Status>`._

<!-- sq:summary -->
| Subtask | Status | Assignee | Title | Story |
| --- | --- | --- | --- | --- |
| ST1 | Done |  | Rewrite CLAUDE.md impersonation paragraph to direct to sq role show | US2 |
<!-- sq:summary:end -->

<!-- sq:subtasks -->

<!-- sq:subtask:ST1 -->
### ST1 — Rewrite CLAUDE.md impersonation paragraph to direct to sq role show

<!-- sq:subtask:ST1:head -->
**Status:** 🟢 Done
**Implements:** US2 — As an agent following the onboarding texts, I want every read they prescribe to be an sq command, so that one interface covers work and identity — locally and, someday, remotely
<!-- sq:subtask:ST1:head:end -->

<!-- sq:subtask:ST1:body -->
Rewrite the CLAUDE.md impersonation paragraph to direct to sq role show; verify the rest of the generated onboarding text is path-free and sync propagates.
<!-- sq:subtask:ST1:body:end -->

#### Discussion

<!-- sq:subtask:ST1:discussion -->
<!-- sq:subtask:ST1:discussion:end -->
<!-- sq:subtask:ST1:end -->
<!-- sq:subtasks:end -->

## Discussion

<!-- sq:discussion -->
<!-- sq:discussion:end -->
