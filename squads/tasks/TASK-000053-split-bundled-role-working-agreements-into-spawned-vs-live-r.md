---
id: TASK-53
sequence_id: 53
type: task
title: Split bundled role working agreements into spawned vs live regimes
status: Done
parent: FEAT-40
author: tech-lead
assignee: python-dev
priority: high
subentities:
- local_id: ST1
  title: Restructure role.md.j2 working agreements into two regimes
  status: Done
  story: US1
- local_id: ST2
  title: Separate decision-recording from handoff-signalling in live regime
  status: Done
  story: US2
- local_id: ST3
  title: Normalize 'For <role>' handoff lines in _interactions.py
  status: Done
  story: US3
created_at: '2026-06-12T07:38:11Z'
updated_at: '2026-06-23T09:57:47Z'
---
<!-- sq:body -->
**Goal.** Rewrite the bundled roles' 'Working agreements' so they read correctly in BOTH regimes an agent operates in, fixing the rigidity that forces a choice between honesty and compliance (see FEAT-40 Problem: the 2026-06-11 false-inbox incident). Content/template only — NO CLI behaviour changes.

**Single source of the regime text.** The two-regime block lives in the role template `src/squads/_rendering/templates/agents/role.md.j2` (the '## Working agreements' section, currently lines ~28-40). Restructure it into two explicit regimes:

  - *Spawned as a subagent*: skip the greeting, do the scoped job, keep status current, and leave the FULL record (a `sq <type> <n> comment --as <slug>` summary + any `@mention` handoff) BEFORE returning — your chat does not survive.

  - *Live with the operator*: greet (`greeting` skill), anchor to items, keep `sq` truthful as you go — applying the principle **'record what the next reader needs, when it becomes true'**: decisions go on the record when made (attributed `--as`), handoffs only when work actually moves, never a mention that signals work nobody greenlit.

**Don't duplicate — reference.** The regime text should point at the `squads` skill's 'Working directly with the operator' section (`squads_skill.md.j2`, ~line 30) and the `greeting` skill rather than restating them. One formulation, no drift.

**Catalog scope.** Roles are template-driven from `src/squads/_roles/_catalog.py` (the 8 PREDEFINED RoleDefs + the `dev_role()` dev-pool template). The working-agreements prose is in the Jinja template, not per-role data, so a single template edit covers all 8 + the dev pool — confirm no role needs bespoke regime text. If any regime nuance must be data-driven, that is a flag to raise, not to invent fields for.

**Regeneration, not migration.** `.claude/` copies are regenerable: `sq sync` propagates the new template to every managed role pointer + the project's own `squads/agents/roles/*.md`. No schema migration. Verify a clean `uv run sq sync` produces both regimes in every generated role file.

**Tests.** Extend `tests/test_rendering.py` / `tests/test_skills.py`: assert a generated role file contains both regime headings and the shared principle, and that markers stay intact. Keep pyright/ruff clean.
<!-- sq:body:end -->

## Subtasks

_Add with `sq task 53 add-subtask "<title>"`; track with `sq task 53 subtask <n> update --status <Status>`._

<!-- sq:summary -->
| Subtask | Status | Assignee | Title | Story |
| --- | --- | --- | --- | --- |
| ST1 | Done |  | Restructure role.md.j2 working agreements into two regimes | US1 |
| ST2 | Done |  | Separate decision-recording from handoff-signalling in live regime | US2 |
| ST3 | Done |  | Normalize 'For <role>' handoff lines in _interactions.py | US3 |
<!-- sq:summary:end -->

<!-- sq:subtasks -->

<!-- sq:subtask:ST1 -->
### ST1 — Restructure role.md.j2 working agreements into two regimes

<!-- sq:subtask:ST1:head -->
**Status:** 🟢 Done
**Implements:** US1 — As an agent spawned for a job, I want my role to tell me exactly what must be on the record before I return, so that the loop never loses my work when my chat evaporates
<!-- sq:subtask:ST1:head:end -->

<!-- sq:subtask:ST1:body -->
Restructure role.md.j2 working agreements into the two explicit regimes with the shared 'record when it becomes true' principle; sq sync propagates to all 8 roles + dev pool.
<!-- sq:subtask:ST1:body:end -->

#### Discussion

<!-- sq:subtask:ST1:discussion -->
<!-- sq:subtask:ST1:discussion:end -->
<!-- sq:subtask:ST1:end -->

<!-- sq:subtask:ST2 -->
### ST2 — Separate decision-recording from handoff-signalling in live regime

<!-- sq:subtask:ST2:head -->
**Status:** 🟢 Done
**Implements:** US2 — As an agent working live with the operator, I want agreements that separate recording decisions from signalling handoffs, so that I never put a false call-to-action in a teammate's inbox
<!-- sq:subtask:ST2:head:end -->

<!-- sq:subtask:ST2:body -->
In the live-regime text, separate recording a decision (--as, when made) from signalling a handoff (@mention, only when work moves); reference the squads skill's operator section instead of duplicating it.
<!-- sq:subtask:ST2:body:end -->

#### Discussion

<!-- sq:subtask:ST2:discussion -->
<!-- sq:subtask:ST2:discussion:end -->
<!-- sq:subtask:ST2:end -->

<!-- sq:subtask:ST3 -->
### ST3 — Normalize 'For <role>' handoff lines in _interactions.py

<!-- sq:subtask:ST3:head -->
**Status:** 🟢 Done
**Implements:** US3 — As a teammate reading my inbox, I want every @mention to be a real, current call-to-action, so that I can trust it as my work queue
<!-- sq:subtask:ST3:head:end -->

<!-- sq:subtask:ST3:body -->
Consistency pass on _interactions.py 'For <role>' handoff lines so each carries its trigger condition (e.g. 'when the feature is greenlit, @tech-lead'), keeping every @mention a real call-to-action; align greeting/squads skill cross-references.
<!-- sq:subtask:ST3:body:end -->

#### Discussion

<!-- sq:subtask:ST3:discussion -->
<!-- sq:subtask:ST3:discussion:end -->
<!-- sq:subtask:ST3:end -->
<!-- sq:subtasks:end -->

## Discussion

<!-- sq:discussion -->
<!-- sq:discussion:end -->
