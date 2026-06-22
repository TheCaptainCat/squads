---
id: FEAT-000040
sequence_id: 40
type: feature
title: 'Dual-regime role definitions: subagent invocation vs live conversation'
status: Done
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
  title: Role tells spawned agent exactly what to record before returning
  status: Done
- local_id: US2
  title: 'Live-regime role: record decisions separately from signalling handoffs'
  status: Done
- local_id: US3
  title: Every inbox @mention is a real, current call-to-action
  status: Done
created_at: '2026-06-11T08:43:52Z'
updated_at: '2026-06-23T10:00:03Z'
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
| US1 | Done |  | Role tells spawned agent exactly what to record before returning |
| US2 | Done |  | Live-regime role: record decisions separately from signalling handoffs |
| US3 | Done |  | Every inbox @mention is a real, current call-to-action |
<!-- sq:summary:end -->

<!-- sq:stories -->

<!-- sq:story:US1 -->
### US1 — Role tells spawned agent exactly what to record before returning

<!-- sq:story:US1:head -->
**Status:** 🟢 Done
<!-- sq:story:US1:head:end -->

<!-- sq:story:US1:body -->
As an agent spawned for a job, I want my role to tell me exactly what must be on the record before I return, so that the loop never loses my work when my chat evaporates.
<!-- sq:story:US1:body:end -->

#### Discussion

<!-- sq:story:US1:discussion -->
<!-- sq:story:US1:discussion:end -->
<!-- sq:story:US1:end -->

<!-- sq:story:US2 -->
### US2 — Live-regime role: record decisions separately from signalling handoffs

<!-- sq:story:US2:head -->
**Status:** 🟢 Done
<!-- sq:story:US2:head:end -->

<!-- sq:story:US2:body -->
As an agent working live with the operator, I want agreements that separate recording decisions from signalling handoffs, so that I never put a false call-to-action in a teammate's inbox.
<!-- sq:story:US2:body:end -->

#### Discussion

<!-- sq:story:US2:discussion -->
<!-- sq:story:US2:discussion:end -->
<!-- sq:story:US2:end -->

<!-- sq:story:US3 -->
### US3 — Every inbox @mention is a real, current call-to-action

<!-- sq:story:US3:head -->
**Status:** 🟢 Done
<!-- sq:story:US3:head:end -->

<!-- sq:story:US3:body -->
As a teammate reading my inbox, I want every @mention to be a real, current call-to-action, so that I can trust it as my work queue.
<!-- sq:story:US3:body:end -->

#### Discussion

<!-- sq:story:US3:discussion -->
<!-- sq:story:US3:discussion:end -->
<!-- sq:story:US3:end -->
<!-- sq:stories:end -->

## Discussion

<!-- sq:discussion -->
- [2026-06-12T07:38:49Z] Olivia Lead:
  - Broke this down into a single task, TASK-000053 (high, Ready, → @python-dev), because the work is one cohesive content edit: the regime prose is template-driven from role.md.j2, so splitting it across files/devs would just churn the same template. Three subtasks map 1:1 to US1-US3.
  - ST1/US1 (spawned regime): restructure role.md.j2 '## Working agreements' into the two regimes + shared 'record what the next reader needs, when it becomes true' principle; sq sync regenerates all 8 roles + the dev-pool template (no migration — .claude/ is regenerable).
  - ST2/US2 (live regime): separate recording a decision (--as, when made) from signalling a handoff (@mention, only when work actually moves); reference the squads skill's 'Working directly with the operator' section rather than duplicating it.
  - ST3/US3 (inbox trust): consistency pass over _interactions.py 'For <role>' handoff lines so each carries its trigger condition (e.g. 'when the feature is greenlit, @tech-lead' — exactly the line that misfired in the 2026-06-11 incident), and align the greeting/squads cross-references to one formulation.
  - Scope guard restated for the implementer: content/templates only, no CLI behaviour change. Acceptance to prove: a spawned-agent reading path and a live-conversation reading path each answer 'must I @mention now?' unambiguously for the incident scenario. @python-dev — yours; flag me if any role needs bespoke regime text (the template assumes it doesn't).
- [2026-06-12T07:47:58Z] Elias Python:
  - TASK-000053 complete. Split role working agreements into two explicit regimes in role.md.j2: *Spawned as a subagent* (skip greeting, do the job, leave full record — comment + @mention — before returning, because the chat does not survive) and *Live with the operator* (greet, anchor, apply the shared principle: 'record what the next reader needs, when it becomes true' — decisions recorded when made with --as, handoffs only when work actually moves, never a mention for work nobody greenlit).
  - The live-regime text references the squads skill's 'Working directly with the operator' section and the greeting skill by name, rather than duplicating them. No drift across surfaces.
  - Also: extended sq sync to regenerate role body sections from the template (was generating only .claude/ pointers). All 9 role files in squads/agents/ now carry both regimes after sq sync.
  - Consistency pass on _interactions.py: all handoff lines now state their trigger condition explicitly. Key fix: product-owner feature handoff now reads 'when stories and acceptance criteria are complete and the feature is greenlit, @tech-lead to break it into tasks' (the scenario from the live incident).
  - 276 tests pass, pyright clean, ruff clean. @reviewer for review.
- [2026-06-12T07:50:20Z] Paul Reviewer:
  - Reviewed TASK-000053 (uncommitted working tree). VERDICT: APPROVED — no changes required. Gates all green: pytest pass, pyright 0 errors, ruff check + format clean.
  - Correctness / marker safety (invariant 3): _regen_role_body in _services/_maintenance.py touches content solely via _sections.get_section/replace_section on the `sq:body` marker region; the discussion region is left intact (verified on regenerated ROLE-000001..009). The render call (template 'agents/role.md.j2', item=/description=item.description/extra=item.extra) is identical to create()'s original render in _base.py:128, so the rewritten body is faithful — no template drift.
  - Concurrency/atomicity concern (dev flag): writing the role .md unlocked, with no index transaction and no updated_at bump, is SOUND here and consistent with the existing sync() contract. sync() already regenerates tool-owned managed files with bare write_text and no lock (backend generate_role_pointer / write_managed / ensure_scaffold / settings.json / CLAUDE.md). _locked_section_edit exists for the concurrent-subagent prose-edit race (comments/body); sync is a single-operator regeneration of generated content, not a prose edit, and role bodies are now tool-owned regenerable content. No frontmatter changes, so skipping the updated_at bump is correct.
  - Scope: content/template only, no CLI behaviour change. The sync extension is justified by the acceptance criterion 'sq sync propagates' — it is the propagation mechanism, not new behaviour, and is covered by test_sync_regenerates_role_bodies.
  - Acceptance criteria met: both regime headings (### Spawned as a subagent / ### Live with the operator) + shared principle 'Record what the next reader needs, when it becomes true' present in every regenerated role. No cross-skill drift — role text references the squads skill's 'Working directly with the operator' section (exists, squads.md:30) and the greeting skill (greeting.md:7) rather than duplicating. PLAYBOOK handoff lines in _interactions.py now carry trigger conditions ('when greenlit', 'when acceptance criteria all pass', etc.) — the live-incident 'must I @mention now?' question is answered unambiguously on both reading paths.
  - Excluded from review per scope: FEAT-000013, pre-existing .squads.json drift, and the TASK-000053/FEAT-000040 sq bookkeeping files. Approved — no action needed from @python-dev. Nice work on keeping the single-source-of-truth discipline and avoiding data-driven regime fields.
<!-- sq:discussion:end -->
