---
id: FEAT-000040
sequence_id: 40
type: feature
title: 'Dual-regime role definitions: subagent invocation vs live conversation'
status: Ready
parent: EPIC-000012
author: product-owner
priority: high
refs:
- FEAT-000014
description: 'Bundled roles'' working agreements split by regime: spawned-for-a-job
  (record everything before you vanish) vs live with the operator (judgment on when
  handoffs become true) — fixing the rigidity that produces false inbox signals'
subentities:
- local_id: US1
  title: As an agent spawned for a job, I want my role to tell me exactly what must
    be on the record before I return, so that the loop never loses my work when my
    chat evaporates
  status: Todo
- local_id: US2
  title: As an agent working live with the operator, I want agreements that separate
    recording decisions from signalling handoffs, so that I never put a false call-to-action
    in a teammate's inbox
  status: Todo
- local_id: US3
  title: As a teammate reading my inbox, I want every @mention to be a real, current
    call-to-action, so that I can trust it as my work queue
  status: Todo
created_at: '2026-06-11T08:43:52Z'
updated_at: '2026-06-11T09:16:31Z'
---
<!-- sq:body -->
## Problem

The bundled role definitions state their working agreements as absolutes: *always* comment on
finish, *always* hand off with an `@mention`. Those rules are written for one regime — an agent
spawned for a job, whose chat evaporates when it returns — and applied to the other regime they
misfire. Live incident (2026-06-11, this squad): the product owner, working a drafting session
with the operator, either had to put a false call-to-action in the tech-lead's inbox
(`@tech-lead` on an epic explicitly not greenlit) or violate her role text. The ecosystem is
already half-aware of the distinction — the `greeting` skill says "skip when spawned", the
`squads` skill has a "working directly with the operator" section — but the role files, the layer
agents actually re-read to know their duties, don't carry it.

## Value

Agents that behave correctly in both regimes without choosing between honesty and compliance:
spawned agents leave a complete record before vanishing (the loop's lifeblood), conversational
agents exercise judgment about *when* an obligation becomes true — decisions go on the record when
made, handoffs when work actually moves. Inboxes stay meaningful: a mention is a real
call-to-action, never ceremony. And since FEAT-000014 will soon let projects fork these templates,
fixing the upstream wording first means forks inherit the distinction instead of the rigidity.

## Scope

- **Restructure the working agreements** in every bundled role (the 8 catalog roles + the dev
  pool template) into two explicit regimes:
  - *Spawned as a subagent*: skip the greeting, do the scoped job, keep status current, and leave
    the full record (comment + `@mention` handoff) before returning — your chat does not survive.
  - *Live with the operator*: greet, anchor to items, keep `sq` truthful as you go — and apply
    the principle **"record what the next reader needs, when it becomes true"**: decisions when
    made (attributed `--as`), handoffs when work actually moves, never a mention that signals
    work nobody greenlit.
- **One source for the principle**: the regime text lives in the role template
  (`role.md.j2`/catalog), references the `squads` skill's operator section rather than duplicating
  it; `sq sync` regenerates all managed copies (no migration — `.claude/` files are regenerable).
- **Consistency pass** over the per-type skills' "For <role>" hand-off lines so they say *when*
  the handoff applies (e.g. "when the feature is greenlit", not just "tell the tech-lead").
- Out of scope: changing the orchestration loop itself or any CLI behaviour — this is content.

## Acceptance

- Every bundled role file shows the two regimes with the shared principle; `sq sync` propagates;
  generated skills' handoff lines carry their trigger condition.
- The `greeting`/`squads` skills and role texts reference each other consistently (one
  formulation, no drift).
- A spawned-agent reading path and a live-conversation reading path each answer "must I @mention
  now?" unambiguously in the scenario from the live incident above.
<!-- sq:body:end -->

## User Stories

_Add with `sq feature 40 add-story "As a <role>, I want … so that …"`; track with `sq feature 40 story <n> update --status <Status>`._

<!-- sq:summary -->
| Story | Status | Assignee | Title |
| --- | --- | --- | --- |
| US1 | Todo |  | As an agent spawned for a job, I want my role to tell me exactly what must be on the record before I return, so that the loop never loses my work when my chat evaporates |
| US2 | Todo |  | As an agent working live with the operator, I want agreements that separate recording decisions from signalling handoffs, so that I never put a false call-to-action in a teammate's inbox |
| US3 | Todo |  | As a teammate reading my inbox, I want every @mention to be a real, current call-to-action, so that I can trust it as my work queue |
<!-- sq:summary:end -->

<!-- sq:stories -->

<!-- sq:story:US1 -->
### US1 — As an agent spawned for a job, I want my role to tell me exactly what must be on the record before I return, so that the loop never loses my work when my chat evaporates

<!-- sq:story:US1:head -->
**Status:** ⚪ Todo
<!-- sq:story:US1:head:end -->

<!-- sq:story:US1:body -->
**Acceptance:** the spawned-regime section lists the non-negotiables (status current, comment summarizing, @mention the next role) and states why (chat does not survive); generated for all roles via the template.
<!-- sq:story:US1:body:end -->

#### Discussion

<!-- sq:story:US1:discussion -->
<!-- sq:story:US1:discussion:end -->
<!-- sq:story:US1:end -->

<!-- sq:story:US2 -->
### US2 — As an agent working live with the operator, I want agreements that separate recording decisions from signalling handoffs, so that I never put a false call-to-action in a teammate's inbox

<!-- sq:story:US2:head -->
**Status:** ⚪ Todo
<!-- sq:story:US2:head:end -->

<!-- sq:story:US2:body -->
**Acceptance:** the live-regime section carries the 'record what the next reader needs, when it becomes true' principle with the decision-vs-handoff distinction, and references the squads skill's operator section instead of duplicating it.
<!-- sq:story:US2:body:end -->

#### Discussion

<!-- sq:story:US2:discussion -->
<!-- sq:story:US2:discussion:end -->
<!-- sq:story:US2:end -->

<!-- sq:story:US3 -->
### US3 — As a teammate reading my inbox, I want every @mention to be a real, current call-to-action, so that I can trust it as my work queue

<!-- sq:story:US3:head -->
**Status:** ⚪ Todo
<!-- sq:story:US3:head:end -->

<!-- sq:story:US3:body -->
**Acceptance:** per-type skill handoff lines state their trigger ('when greenlit', 'when findings are filed', …); the drafting-session scenario (Ready epic, no greenlight) resolves to no mention, decision recorded.
<!-- sq:story:US3:body:end -->

#### Discussion

<!-- sq:story:US3:discussion -->
<!-- sq:story:US3:discussion:end -->
<!-- sq:story:US3:end -->
<!-- sq:stories:end -->

## Discussion

<!-- sq:discussion -->
<!-- sq:discussion:end -->
