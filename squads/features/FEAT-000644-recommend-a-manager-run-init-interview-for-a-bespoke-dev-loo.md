---
id: FEAT-644
sequence_id: 644
type: feature
title: Recommend a manager-run init interview for a bespoke dev-loop skill
status: Done
author: product-owner
refs:
- FEAT-642
- MILE-836:targets
description: Init docs recommend the manager interview the operator and author a self-assigned
  squad-running skill
subentities:
- local_id: US1
  title: Recommend an init-time interview in docs/agents.md
  status: Done
- local_id: US2
  title: Ship the seven-area interview checklist as offered prompts
  status: Done
created_at: '2026-07-24T07:41:51Z'
updated_at: '2026-09-01T08:04:01Z'
---
<!-- sq:body -->
**Capability.** `sq init`'s documentation recommends — but never scaffolds, generates, or enforces — that the manager agent open a squad by interviewing the operator about how they want the squad run, then author and self-assign a bespoke skill (e.g. a "run the dev loop" skill) that encodes the operator's answers.

**Why.** sq deliberately enforces only a hard floor: stable IDs, the status lifecycle, and item structure. Everything about *how* a squad is managed day to day is a per-operator, per-squad style choice, and sq should stay out of the way of that choice rather than impose one. Recommending an init-time interview front-loads those working preferences in one sitting, instead of letting them accrue slowly, one piece of corrective feedback at a time, across many sessions.

**Scope.**

- Add a recommendation to the init documentation: early in a new squad's life, the manager role interviews the operator about how they want work run, then closes the interview by authoring a bespoke skill for itself and self-assigning it, so the operator's answers become durable, discoverable guidance rather than a one-off conversation.

- Ship a suggested interview checklist as documentation content — seven areas the manager can raise, offered as prompts and illustrative questions, not a rigid script: (1) autonomy & escalation — unattended loop vs. pausing at gates, and what must interrupt the operator (schema/migration changes, architectural decisions, design forks, spend, anything user-facing/visual); (2) delegation & roles — who authors what, which specialists are live, custom roles, whether review must be an independent agent from the builder; (3) quality bar — the must-pass gate before a handoff or commit, review rigor for integrity-critical work, and whether to independently verify completion claims; (4) git & releases — commit-message style and trailers, who commits vs. pushes vs. publishes; (5) communication — update verbosity, handoff conventions, and putting the operator's own words on the record; (6) structure & records lifecycle — feature and task grouping style, and whether records like decisions/requirements documents are amended in place or superseded by a new item as they evolve; (7) safety — confirmation before destructive operations, and comfort with parallel agents.

- Explicitly out of scope: sq itself generates nothing from this. No new command, no scaffolded file, no init-time prompt, no validation that the skill exists or matches the checklist. The interview and the resulting skill are ordinary operator/manager-authored content, exactly like any other custom skill — the recommendation lives in documentation only.

- One grouping style raised under structure & records lifecycle — a single larger task broken into subtasks owned by different actors — depends on the work queues (the assignment-routing surfaces an actor checks for their own work) becoming aware of per-subtask assignments; until then, that style routes correctly for the parent item's assignee but not for a different actor assigned only a subtask.

**Acceptance.**

- Init documentation recommends the manager-interview → self-authored-skill flow, clearly framed as optional guidance an operator can decline entirely.

- The seven-area checklist ships as documentation content, usable as-is or adapted.

- No new command, generator, template, or validation step ships — sq's runtime behavior is unchanged; this is a documentation-only change.
<!-- sq:body:end -->

## User Stories

_Add with `sq feature 644 add-story "As a <role>, I want … so that …"`; track with `sq feature 644 story <n> update --status <Status>`._

<!-- sq:summary -->
| Story | Status | Assignee | Title |
| --- | --- | --- | --- |
| US1 | Done |  | Recommend an init-time interview in docs/agents.md |
| US2 | Done |  | Ship the seven-area interview checklist as offered prompts |
<!-- sq:summary:end -->

<!-- sq:stories -->

<!-- sq:story:US1 -->
### US1 — Recommend an init-time interview in docs/agents.md

<!-- sq:story:US1:head -->
**Status:** 🟢 Done
<!-- sq:story:US1:head:end -->

<!-- sq:story:US1:body -->
**As an operator opening a new squad, I want the docs to recommend an init-time
interview so that my working preferences get captured once, up front, instead
of trickling in as corrections over many sessions.**

**Where.** `docs/agents.md` is the manager's operating manual — the doc that already
tells the agent what to do early in a session (greeting, impersonation, registering
the operator). Add a short subsection there, near the existing "You have a name"
material, describing the recommended flow: early in a fresh squad, when the manager
greets the operator for the first time, it can open with a short interview about how
they want work run, then close by authoring a bespoke skill for itself (e.g. a
"run the dev loop" skill) and self-assigning it — turning the answers into durable,
discoverable guidance instead of a one-off conversation. Point to the checklist
(the companion story) for the actual prompts.

**Framing (non-negotiable).** State plainly that this is optional guidance an
operator can decline entirely — never a required step, never something `sq`
prompts for or checks. Word it as something the manager *may* do, not something
`sq` does: no "sq prompts the manager to…" phrasing, no implication of an
interactive flow, generated file, or validation. The skill that results is
ordinary operator/manager-authored content, exactly like any other custom skill.

**Cross-link, don't duplicate.** Add a one-line pointer from the `sq init`/`sq
adopt` walkthroughs (`docs/tutorial.md` step 0, `docs/adoption.md` step 1) to the
new subsection, and update `docs/README.md`'s "Where to go" table row for
`agents.md` so its one-line description mentions the interview recommendation.
Don't restate the flow in three places — one home, linked from the others.

**Acceptance.**
- `docs/agents.md` carries the recommendation, clearly optional/declinable.
- `sq docs agents` (offline, packaged) surfaces the new text with no code change —
  confirmed by running it after the edit.
- `docs/tutorial.md`, `docs/adoption.md`, and the `docs/README.md` index each carry
  a one-line pointer to the new subsection, not a restatement of it.
- No new command, generator, template, or validation ships; nothing under `src/`,
  `tests/`, or `clients/` changes. `sq`'s runtime behaviour is unchanged.
<!-- sq:story:US1:body:end -->

#### Discussion

<!-- sq:story:US1:discussion -->
<!-- sq:story:US1:discussion:end -->
<!-- sq:story:US1:end -->

<!-- sq:story:US2 -->
### US2 — Ship the seven-area interview checklist as offered prompts

<!-- sq:story:US2:head -->
**Status:** 🟢 Done
<!-- sq:story:US2:head:end -->

<!-- sq:story:US2:body -->
**As the manager running an init-time interview, I want a suggested checklist of
areas and illustrative questions so that I don't have to invent the conversation
from scratch, while still adapting it to the operator in front of me.**

**Where.** Same subsection of `docs/agents.md` as the recommendation story (or
immediately following it) — content, not code.

**Shape.** Ship the checklist as offered prompts, not a rigid script: each of the
seven areas below gets a short framing line plus a few illustrative questions the
manager can ask, adapt, skip, or reorder. Avoid imperative "you must ask" phrasing;
use "consider asking" / "worth raising" register throughout, so nothing reads as
an enforced sequence.

1. **Autonomy & escalation** — unattended loop vs. pausing at gates; what must
   interrupt the operator (schema/migration changes, architectural decisions,
   design forks, spend, anything user-facing/visual).
2. **Delegation & roles** — who authors what, which specialists are live, custom
   roles, whether review must be an independent agent from the builder.
3. **Quality bar** — the must-pass gate before a handoff or commit, review rigor
   for integrity-critical work, whether to independently verify completion claims.
4. **Git & releases** — commit-message style and trailers, who commits vs. pushes
   vs. publishes.
5. **Communication** — update verbosity, handoff conventions, putting the
   operator's own words on the record.
6. **Structure & records lifecycle** — feature/task grouping style, and whether
   records (decisions/requirements docs) are amended in place or superseded by a
   new item as they evolve. For the "one larger task, subtasks owned by different
   actors" grouping style specifically: note plainly that it currently routes
   correctly only for the parent item's own assignee, not for an actor assigned
   solely a subtask, until the work-queue surfaces (mine/inbox/workload) become
   aware of per-subtask assignment — describe the limitation, don't cite an
   internal ticket for it, and flag it (in a comment on this story, not the docs
   prose) for a follow-up pass once that lands.
7. **Safety** — confirmation before destructive operations, comfort with parallel
   agents.

**One checklist, not seven.** All seven areas ship as one cohesive section (a
single piece of prose/list the manager reads once), not seven separate doc
fragments — they're one interview, one sitting.

**Acceptance.**
- All seven areas present, each with a framing line + a few sample questions,
  clearly offered rather than mandatory.
- Area 6's grouping-style note accurately reflects the current routing limitation,
  in adopter-appropriate language (no sq item IDs, no repo/dev-process framing).
- `sq docs agents` surfaces it with no code change.
- No new command, generator, template, or validation ships; nothing under `src/`,
  `tests/`, or `clients/` changes.
<!-- sq:story:US2:body:end -->

#### Discussion

<!-- sq:story:US2:discussion -->
<!-- sq:story:US2:discussion:end -->
<!-- sq:story:US2:end -->
<!-- sq:stories:end -->

## Discussion

<!-- sq:discussion -->
- [2026-07-29T09:37:09Z] Pierre Chat:
  - Scheduled for 0.13.
- [2026-07-30T07:57:45Z] Pierre Chat:
  - Third in 0.13, after FEAT-691 and FEAT-642, ahead of FEAT-321.
- [2026-08-03T11:17:44Z] Pierre Chat:
  - Out of 0.13 as well. The release is already carrying the whole spec-driven customization epic, a thirty-finding consumer sweep, the ADR audit and the sub-entity read surfaces. This is additive guidance with nothing forcing it into this cut.
- [2026-08-03T11:22:16Z] Catherine Manager:
  - For whoever builds this: the checklist area covering grouping style carries a caveat about per-subtask assignment routing not being surfaced. That limitation has since been closed — mine, workload and inbox are now sub-entity aware and the JSON surfaces carry sub-entity discussion. Re-verify that caveat against the shipped behaviour before writing it; the ref to that feature is what makes the dependency findable, and it is now Done rather than pending.
- [2026-08-24T20:33:08Z] Olivia Lead:
  - Moved Draft → Ready so the parent does not trail its child: TASK-794 now carries the implementation of both stories and is Ready for dispatch. US1/US2 stay Todo — work has not started.
<!-- sq:discussion:end -->
