---
id: TASK-794
sequence_id: 794
type: task
title: Document the manager-run init interview and its checklist
status: Done
parent: FEAT-644
author: tech-lead
assignee: tech-writer
description: Write the optional init-time interview recommendation and the seven-area
  checklist into docs/agents.md
subentities:
- local_id: ST1
  title: Write the interview recommendation into docs/agents.md
  status: Done
  story: US1
- local_id: ST2
  title: Ship the seven-area checklist as offered prompts
  status: Done
  story: US2
- local_id: ST3
  title: Re-verify the grouping-style routing caveat before writing it
  status: Done
  story: US2
created_at: '2026-08-24T20:31:24Z'
updated_at: '2026-08-25T14:04:21Z'
---
<!-- sq:body -->
## What ships

`docs/agents.md` gains a short subsection recommending that, early in a fresh squad, the
manager role interview the operator about how they want work run, and close the interview
by authoring a bespoke skill for itself (e.g. a "run the dev loop" skill) and
self-assigning it — so the operator's answers become durable, discoverable guidance
instead of a one-off conversation that has to be re-had, one correction at a time, across
many sessions.

The same subsection ships the seven-area interview checklist as offered prompts.

`docs/agents.md` is the home. `docs/tutorial.md` step 0, `docs/adoption.md` step 1 and the
"Where to go" table in `docs/README.md` each get a one-line pointer to it — a pointer, not
a restatement.

## The constraint that defines this work

**`sq` generates nothing, scaffolds nothing, prompts for nothing and validates nothing.**
No new command, no template, no init-time prompt, no check rule, no generated file, no
assertion that the skill exists or matches the checklist. The interview is a conversation
a manager may choose to have; the skill that results is ordinary operator/manager-authored
content, exactly like any other custom skill.

This is not a simplification or a first increment — it is the feature's whole point. sq
deliberately enforces only a hard floor (stable IDs, the status lifecycle, item structure)
and stays out of *how* a squad is run day to day, because that is a per-operator, per-squad
style choice. A command that asked the seven questions would be sq imposing the very choice
it is declining to impose.

So: nothing under `src/`, `tests/` or `clients/` changes. If the work seems to need a code
change, that is the signal to stop and hand back, not to build one.

## Register

Optional throughout. The manager *may* open with an interview; the operator may decline it
entirely. Never "sq prompts the manager to…", never an implied interactive flow. The
checklist is "consider asking" / "worth raising", not "you must ask" — seven areas the
manager can adapt, skip or reorder, not a script to read out.

Adopter register: no sq item IDs, no references to this repository's own build process.

## Dependencies

FEAT-642 is Done, so nothing gates this work. It also matters to the content — see ST3.

## Acceptance

- `docs/agents.md` carries the recommendation and the seven-area checklist as one cohesive
  section, clearly optional and declinable.
- `docs/tutorial.md`, `docs/adoption.md` and `docs/README.md` each carry a one-line
  pointer, not a copy.
- `sq docs agents` (offline, packaged) surfaces the new text with no code change —
  confirmed by running it after the edit.
- `git status` shows changes under `docs/` only. `sq`'s runtime behaviour is unchanged.
<!-- sq:body:end -->

## Subtasks

_Add with `sq task 794 add-subtask "<title>"`; track with `sq task 794 subtask <n> update --status <Status>`._

<!-- sq:summary -->
| Subtask | Status | Assignee | Title | Story |
| --- | --- | --- | --- | --- |
| ST1 | Done |  | Write the interview recommendation into docs/agents.md | US1 |
| ST2 | Done |  | Ship the seven-area checklist as offered prompts | US2 |
| ST3 | Done |  | Re-verify the grouping-style routing caveat before writing it | US2 |
<!-- sq:summary:end -->

<!-- sq:subtasks -->

<!-- sq:subtask:ST1 -->
### ST1 — Write the interview recommendation into docs/agents.md

<!-- sq:subtask:ST1:head -->
**Status:** 🟢 Done
**Implements:** US1 — Recommend an init-time interview in docs/agents.md
<!-- sq:subtask:ST1:head:end -->

<!-- sq:subtask:ST1:body -->
Maps to US1.

**Where.** `docs/agents.md`, near the existing "You have a name" material — the part of
the manager's operating manual that already covers what an agent does early in a session
(greeting, impersonation, registering the operator). The recommendation belongs beside
those, not in a section of its own at the end.

**What it says.** Early in a fresh squad, when the manager greets the operator for the
first time, it can open with a short interview about how they want work run, then close by
authoring a bespoke skill for itself — a "run the dev loop" skill, say — and self-assigning
it. That turns the answers into durable, discoverable guidance instead of a conversation
that evaporates. Point to the checklist (ST2) for the actual prompts; do not restate them
here.

**Framing.** State plainly that this is optional guidance the operator can decline
entirely. It is never a required step and never something `sq` prompts for or checks.
Word it as something the manager *may* do, not something `sq` does: no "sq prompts the
manager to…", no implication of an interactive flow, a generated file, or validation.

**Cross-link, don't duplicate.** One-line pointers from `docs/tutorial.md` step 0 and
`docs/adoption.md` step 1, and an updated one-line description in the `agents.md` row of
`docs/README.md`'s "Where to go" table. One home, linked from three places — not the flow
told four times.

Done when: `docs/agents.md` carries the recommendation, clearly optional; the three
pointers exist and are one line each; `sq docs agents` surfaces the new text with no code
change; nothing under `src/`, `tests/` or `clients/` changed.
<!-- sq:subtask:ST1:body:end -->

#### Discussion

<!-- sq:subtask:ST1:discussion -->
<!-- sq:subtask:ST1:discussion:end -->
<!-- sq:subtask:ST1:end -->

<!-- sq:subtask:ST2 -->
### ST2 — Ship the seven-area checklist as offered prompts

<!-- sq:subtask:ST2:head -->
**Status:** 🟢 Done
**Implements:** US2 — Ship the seven-area interview checklist as offered prompts
<!-- sq:subtask:ST2:head:end -->

<!-- sq:subtask:ST2:body -->
Maps to US2.

**Where.** The same subsection of `docs/agents.md` as ST1, or immediately following it.
All seven areas ship as **one cohesive section** the manager reads once — they are one
interview in one sitting, not seven doc fragments.

**Shape.** Offered prompts, not a script. Each area gets a short framing line plus a few
illustrative questions the manager can ask, adapt, skip or reorder. "Consider asking" /
"worth raising" register throughout; no imperative "you must ask", nothing that reads as
an enforced sequence.

The seven areas:

1. **Autonomy & escalation** — unattended loop vs. pausing at gates; what must interrupt
   the operator (schema or migration changes, architectural decisions, design forks,
   spend, anything user-facing or visual).
2. **Delegation & roles** — who authors what, which specialists are live, custom roles,
   whether review must be an independent agent from the builder.
3. **Quality bar** — the must-pass gate before a handoff or commit, review rigor for
   integrity-critical work, whether to independently verify completion claims.
4. **Git & releases** — commit-message style and trailers, who commits vs. pushes vs.
   publishes.
5. **Communication** — update verbosity, handoff conventions, putting the operator's own
   words on the record.
6. **Structure & records lifecycle** — grouping style for features and units of work, and
   whether records such as decisions and requirements documents are amended in place or
   superseded by a new item as they evolve. The routing caveat this area used to carry is
   ST3's subject — write this area's text only after ST3 settles it.
7. **Safety** — confirmation before destructive operations, comfort with parallel agents.

Adopter register: no sq item IDs, no repo or dev-process framing.

Done when: all seven areas are present, each with a framing line and a few sample
questions, clearly offered rather than mandatory; they read as one section; `sq docs
agents` surfaces them; nothing under `src/`, `tests/` or `clients/` changed.
<!-- sq:subtask:ST2:body:end -->

#### Discussion

<!-- sq:subtask:ST2:discussion -->
<!-- sq:subtask:ST2:discussion:end -->
<!-- sq:subtask:ST2:end -->

<!-- sq:subtask:ST3 -->
### ST3 — Re-verify the grouping-style routing caveat before writing it

<!-- sq:subtask:ST3:head -->
**Status:** 🟢 Done
**Implements:** US2 — Ship the seven-area interview checklist as offered prompts
<!-- sq:subtask:ST3:head:end -->

<!-- sq:subtask:ST3:body -->
Maps to US2.

Area 6 of the checklist was specified with a caveat attached: for the "one larger unit of
work, sub-items owned by different actors" grouping style, the work-queue surfaces an
actor checks for their own work were not aware of per-sub-item assignment, so that style
routed correctly for the parent item's assignee but not for someone assigned only a
sub-item.

**That limitation has since been closed.** `mine`, `workload` and `inbox` are sub-entity
aware and the JSON surfaces carry sub-entity discussion, delivered by the feature FEAT-644
references as its dependency, which is now Done.

So: verify the caveat against the shipped behaviour before writing a word of it. Drive it
against a real squad — assign a sub-item to one actor and the parent to another, and read
each surface — rather than inferring it from the feature's own description. Then either
drop the caveat entirely, or narrow it to whatever genuinely remains.

Whatever ships must describe the behaviour in adopter language. No internal ticket cited
in the prose, no "this was fixed in…" framing — an adopter reading the checklist is
learning how the tool routes work today, not its history.

Done when: each of the three surfaces has been exercised against a squad with a sub-item
assigned away from its parent's assignee; area 6's text reflects what was observed; and
the observations are recorded in a comment on this subtask so the next reader does not
repeat the check.
<!-- sq:subtask:ST3:body:end -->

#### Discussion

<!-- sq:subtask:ST3:discussion -->
- [2026-08-25T13:46:39Z] Theo Writer:
  - Verified by driving a scratch squad, not by reading the feature body. Setup: a fresh `sq init`, a task assigned to one role, one subtask on it assigned to a different role, and a mention of the second role inside the subtask discussion.
  - Observed. `sq mine <sub-item assignee>` returns the parent row with a **Matched** column reading "ST1 (Todo)" — so an actor assigned only a sub-item does find their work, and is told which sub-item and what state it is in. `sq mine <parent assignee>` returns the same row with an empty Matched column. `sq inbox <sub-item assignee>` surfaces the mention and names its exact region (subtask:ST1:discussion#1). `sq workload` gives the sub-item assignee 0 items and 1 sub-item, in dedicated Sub Open / Sub Closed / Sub Total columns. The `--json` forms carry the same: `mine --json` adds a `matched_subentities` array, `inbox --json` a `regions` array.
  - Conclusion: the caveat is fully stale and is dropped, not narrowed — nothing observed routes wrongly on any of the three surfaces. Area 6 now states the positive fact instead, in adopter language: either grouping style routes fine, someone assigned only a sub-item still finds it in `sq mine` on the parent row tagged with the sub-item they own, and `sq workload` counts the two kinds of assignment separately. No history framing, no ticket cited.
<!-- sq:subtask:ST3:discussion:end -->
<!-- sq:subtask:ST3:end -->
<!-- sq:subtasks:end -->

## Discussion

<!-- sq:discussion -->
- [2026-08-24T20:33:07Z] Olivia Lead:
  - Broken out from FEAT-644 and moved to Ready: one task, three subtasks mapped ST1→US1, ST2/ST3→US2. Both stories are one docs section in one file, so splitting them across tasks would only split a single edit.
  - The documentation-only constraint is stated in the body as the feature's point, not as a scope cut — a developer reading "recommend an interview" will otherwise reach for a command.
  - ST3 exists because the area-6 routing caveat FEAT-644 specified is now stale: FEAT-642 shipped sub-entity aware mine/inbox/workload. Verify against behaviour before writing that text.
  - @tech-writer ready for dispatch; nothing gates it.
- [2026-08-24T20:40:49Z] Catherine Manager:
  - Dispatch paused by the operator before any file was written; the task is InProgress but no work has landed yet. Resume from the task body as specified.
- [2026-08-25T13:46:54Z] Theo Writer:
  - Done and in review. `docs/agents.md` gains one section, "Opening a new squad: the interview", sitting between the identity/greeting material and the loop — the recommendation and the seven-area checklist together, as one thing a manager reads in one sitting.
  - The constraint is written as the point, not a scope cut: the section says plainly that `sq` does not run the interview — no command, no prompt at init, no scaffolded file, nothing checking the skill exists — and then says why, that `sq` enforces a hard floor and stops there because how a squad is run is a per-team choice, so a command asking those questions would impose exactly the choice it is declining to make. The intent is that the next reader understands it and does not reach for a generator.
  - Register is "consider asking" throughout, framed as a suggestion an operator can decline outright, with an explicit licence to adapt, reorder, skip and stop early. The three commands the section shows (`skill add`, `skill … body --file`, `skill … link-role`) were driven against a scratch squad and all work as written.
  - Pointers are one line each and do not restate: the tutorial install step, the adoption scaffold step, and the agents.md row of the README index table.
  - Area 6: the routing caveat was stale and is dropped rather than narrowed — full observations on ST3. Area 6 now states the positive behaviour instead.
  - Gates: changes for this task are under `docs/` only; nothing in `src/`, `tests/` or `clients/` moved for it. `sq docs agents` surfaces the new section offline. ruff check and format clean, `sq check` clean, and the meta plus docs test modules pass. Full suite left to the coordinator.
  - @tech-lead ready for review.
- [2026-08-25T14:02:25Z] Theo Writer:
  - Second pass, addressing all four review findings. All four now Fixed with a note on each.
  - F1 (the real defect): the "every later session loads" claim is gone, and the advice changed with it. The section now says to scope the skill to the roles the answers apply to, explains that a role preloads only the skills linked to it, calls out that the quality bar, the commit/release conventions and the destructive-operation rules govern what developers and reviewers do, and shows a second `link-role` call with "one role per call — repeat for each". Driven verbatim: both calls exit 0, exactly those two pointers preload the skill, `sq check` clean.
  - F2: the hard-floor list no longer names the status lifecycle and item shape as fixed — which would have contradicted the overrides documentation. It now names the structural guarantees (stable identifier, a declared status and a lifecycle that governs how an item may move, state in frontmatter rather than prose) and says explicitly that which types, statuses and lifecycles a squad declares is the squad's own call, linking to the overrides page. The rhetorical point — structure, not method — is intact.
  - F3: "init-time interview" now appears on the page itself, so the pointers that use the term land somewhere that uses it. The adoption pointer drops "init-time", which was contradicting its own "Once the squad exists" opener. Heading and anchor unchanged, so no inbound link moved.
  - F4: block kept, duplication labelled. The prose under it now names roles.md as the home for the skill surface and this as that surface with the interview's slug in it, so either copy points at the other; the mechanics roles.md owns are not repeated here.
  - Gates: docs-only change, `sq docs agents` renders it, meta and docs test modules pass (185), ruff clean, `sq check` clean. Staying in review — @reviewer over to you.
<!-- sq:discussion:end -->
