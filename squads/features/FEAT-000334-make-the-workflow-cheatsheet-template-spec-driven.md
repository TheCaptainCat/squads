---
id: FEAT-334
sequence_id: 334
type: feature
title: Make the workflow cheatsheet template spec-driven
status: Draft
parent: EPIC-335
author: product-owner
refs:
- FEAT-326:depends-on
- EPIC-325
subentities:
- local_id: US1
  title: As a team using a customized vocabulary spec, I want an accurate, non-blank
    workflow cheatsheet
  status: Todo
- local_id: US2
  title: As a reader of the cheatsheet, I want a concise cross-type overview, not
    a repeat of the sq-<type> skills
  status: Todo
- local_id: US3
  title: As the operator of the bundled default squad, I want the cheatsheet to stay
    at least as good as it is today
  status: Todo
created_at: '2026-07-08T15:06:36Z'
updated_at: '2026-07-08T15:09:46Z'
---
<!-- sq:body -->
## Problem

`src/squads/_rendering/templates/workflow.md.j2` — the shared source for the `squads`
skill's workflow cheatsheet and `sq workflow` — is written the old, pre-spec-driven way
for its main "Team workflow" section. It hardcodes specific type names (`feature`,
`task`, `story`, `subtask`) and hand-composes guidance with `if item_type == …`-shaped
selection (`authoring_owner('feature')`, `authoring_owner('task')`,
`spec.item_subentity_kind('task') == 'subtask'`, `parent_chain(spec, 'task')`, …).

Two consequences:

1. **Brittle to vocabulary customization.** For a spec that renames or drops those
   specific types, the corresponding `{% if %}` blocks silently produce nothing — a
   customized project's cheatsheet goes near-blank with no guidance for its own
   vocabulary, even though the project's playbook/roster fully describes how its team
   works.
2. **Duplicates data that already lives in the playbook.** `_interactions/playbook.toml`
   (loaded as `ItemPlaybookSpec`/`RoleGuideSpec`) already declares, per type and per
   role, the ordered `enter`/`do`/`handoff`/`watch` guidance — this is the same
   authoritative source the per-type `sq-<type>` skills are generated from. The
   cheatsheet re-narrates a hand-picked slice of that same information by hand instead
   of describing what the loaded playbook + roster actually say.

Some parts of the template (the alias table, the lifecycle table, the retype/remove-vs-
cancel static content) are already properly generic — they iterate `spec.items` and
`spec.machine_for(...)` without naming a type. The "Team workflow" section is the one
that regressed to hardcoding.

## What this delivers

Redesign the "Team workflow" section of `workflow.md.j2` to describe the loaded
playbook + roster **generically** — iterate the spec's declared types and roles in
whatever order they're declared, rendering from `_interactions` data
(`ItemPlaybookSpec`/`RoleGuideSpec`) and the roster, not from hardcoded type/kind
literals. For a default (unmodified) squad this must render output equivalent to (or
better than) what ships today; for a spec with renamed/dropped/added types it must
render an accurate cheatsheet with no blank gaps.

## The key design question: cheatsheet vs. per-type skill altitude

This is the crux of the redesign, not a detail — get this wrong and the fix just moves
the duplication problem rather than solving it.

The per-type `sq-<type>` skills are *also* generated from `_interactions/playbook.toml`
— they render the full `enter`/`do`/`handoff`/`watch` guidance for one type, one role at
a time, in depth. If the cheatsheet redesign just dumps the same playbook data
type-by-type-by-role, it becomes a second, lower-fidelity copy of the `sq-<type>`
skills: same data, same altitude, just worse formatting. That would "fix" the
hardcoding without fixing the actual problem (duplicated authorship of one truth).

So this feature must define — explicitly, before implementation — the cheatsheet's
**distinct role and altitude**, different from the skills it stands alongside:

- **`sq-<type>` skills** = the per-type deep-dive. "I'm working a FEAT right now — what
  exactly do I do, in what order, with which commands, for my role." Full
  `enter`/`do`/`handoff`/`watch` detail, one type at a time.
- **Workflow cheatsheet** = the cross-type, cross-role overview. "What's the shape of
  this team, and how does work generally flow between roles and across types?" It
  should read as a map of the whole system at a glance — who authors what, who hands
  off to whom, roughly in what order — not a restatement of any one type's full
  playbook entry.

Concretely, the cheatsheet should be built by **summarizing/aggregating** across the
playbook (e.g. one condensed line per type-role pairing: who does it, and the single
highest-signal handoff trigger — not the full `do`/`watch` lists), while the
`sq-<type>` skill continues to render the playbook entry in full. The exact
summarization shape (what to keep, what to drop) is a design decision for whoever
implements this — this feature is scoping the *requirement* that a distinct altitude
be chosen and documented in the implementation, not prescribing the literal format.

## Non-goals

- Rewriting or restructuring the per-type `sq-<type>` skills themselves — they stay the
  deep-dive layer and are out of scope here.
- Changing the playbook data model (`_interactions/_models.py`,
  `_interactions/playbook.toml`) — this feature consumes that data as-is.
- Touching the already-generic parts of `workflow.md.j2` (alias table, lifecycle table,
  `workflow_static.md.j2` content) beyond what's needed to keep them consistent with
  the redesigned section.

## Sequencing

Depends on FEAT-326 (remove the `ItemType`/`Status` enums) — a fully generic
cheatsheet only makes sense once item types and statuses are spec-driven end to end;
building the generic cheatsheet against the still-partially-hardcoded engine would mean
redoing it once FEAT-326 lands. Relates to EPIC-325 (the umbrella for the generic item
engine work this feature is part of).

At dispatch (after FEAT-326 lands), this needs a tech-lead to break it into tasks, a
dev to implement the generic rendering, and the tech-writer to sign off on the
cheatsheet's format/voice once the generic version is drafted — this feature defines
the what/why only.
<!-- sq:body:end -->

## User Stories

_Add with `sq feature 334 add-story "As a <role>, I want … so that …"`; track with `sq feature 334 story <n> update --status <Status>`._

<!-- sq:summary -->
| Story | Status | Assignee | Title |
| --- | --- | --- | --- |
| US1 | Todo |  | As a team using a customized vocabulary spec, I want an accurate, non-blank workflow cheatsheet |
| US2 | Todo |  | As a reader of the cheatsheet, I want a concise cross-type overview, not a repeat of the sq-<type> skills |
| US3 | Todo |  | As the operator of the bundled default squad, I want the cheatsheet to stay at least as good as it is today |
<!-- sq:summary:end -->

<!-- sq:stories -->

<!-- sq:story:US1 -->
### US1 — As a team using a customized vocabulary spec, I want an accurate, non-blank workflow cheatsheet

<!-- sq:story:US1:head -->
**Status:** ⚪ Todo
<!-- sq:story:US1:head:end -->

<!-- sq:story:US1:body -->
Generate the cheatsheet against a spec that renames, drops, and adds item types/roles (not the bundled default) and inspect the rendered output.

Acceptance: the rendered 'Team workflow' section contains no literal occurrence of the words feature/task/story/subtask/epic/bug/decision/review/guide as hardcoded template text (they may appear only because the loaded spec's own type names happen to include them) — every type/role name in the output comes from iterating the spec/playbook/roster, never from an if-branch keyed to one specific type.

Acceptance: for every non-meta type declared in the spec that has at least one playbook role guide, the cheatsheet renders at least one line of guidance for it — no type with playbook data is silently dropped because it isn't 'feature' or 'task'.

Acceptance: renaming a type in the spec (e.g. feature -> capability) changes only the rendered name, not whether guidance appears at all.
<!-- sq:story:US1:body:end -->

#### Discussion

<!-- sq:story:US1:discussion -->
<!-- sq:story:US1:discussion:end -->
<!-- sq:story:US1:end -->

<!-- sq:story:US2 -->
### US2 — As a reader of the cheatsheet, I want a concise cross-type overview, not a repeat of the sq-<type> skills

<!-- sq:story:US2:head -->
**Status:** ⚪ Todo
<!-- sq:story:US2:head:end -->

<!-- sq:story:US2:body -->
The cheatsheet is reviewed side by side with the generated sq-<type> skills to confirm it sits at a different, complementary altitude rather than dumping the same content twice.

Acceptance: the cheatsheet's per-type-role content is a condensed summary (e.g. one line per type-role pairing capturing who acts and the primary handoff), not the full enter/do/handoff/watch lists that the corresponding sq-<type> skill already renders in full for that same type-role pairing.

Acceptance: the implementation notes (in code comments or the task that implements this) explicitly state the chosen altitude/summarization rule, so a future editor knows why the cheatsheet stops short of full playbook detail instead of re-deriving it from scratch.

Acceptance: the cross-type overview surfaces the team's overall shape (who authors what, roughly how work flows role to role and type to type) even though no single line matches a full sq-<type> skill's depth.

Non-goal note: this story does not ask to rewrite the sq-<type> skill templates themselves.
<!-- sq:story:US2:body:end -->

#### Discussion

<!-- sq:story:US2:discussion -->
<!-- sq:story:US2:discussion:end -->
<!-- sq:story:US2:end -->

<!-- sq:story:US3 -->
### US3 — As the operator of the bundled default squad, I want the cheatsheet to stay at least as good as it is today

<!-- sq:story:US3:head -->
**Status:** ⚪ Todo
<!-- sq:story:US3:head:end -->

<!-- sq:story:US3:body -->
Render the cheatsheet for the bundled, unmodified squad (default roster + default playbook) before and after the redesign and diff them.

Acceptance: every fact present in today's cheatsheet (feature/story authoring flow, task/subtask-to-story mapping, sub-entity status machines, the hierarchy line, the alias table, the lifecycle table, the retype/remove-vs-cancel/ref-kind static sections) is still present or superseded by an equivalent-or-clearer generic rendering — nothing the default squad relies on today silently disappears.

Acceptance: sq workflow output and the squads skill's rendered cheatsheet both stay coherent, readable prose/tables (not a raw data dump) for the default squad — the generic rewrite is not allowed to regress readability in the one case (the bundled default) most users actually see.

Acceptance: this story is verified by a human/tech-writer read-through of the rendered default cheatsheet, not just an automated diff, since 'equivalent or better' is partly a voice/quality judgment.
<!-- sq:story:US3:body:end -->

#### Discussion

<!-- sq:story:US3:discussion -->
<!-- sq:story:US3:discussion:end -->
<!-- sq:story:US3:end -->
<!-- sq:stories:end -->

## Discussion

<!-- sq:discussion -->
- [2026-07-08T15:07:55Z] Nina Product:
  - Scoped from op-pierre's request: workflow.md.j2's 'Team workflow' section hardcodes feature/task/story/subtask names and if-branches instead of describing the loaded _interactions playbook + roster generically.
  - Framed the crux design question as US2: the cheatsheet must stay a concise cross-type overview (summarized playbook data), distinct in altitude from the sq-<type> skills (full per-type playbook detail) — not a second copy of the same content.
  - depends-on FEAT-326 (generic type/status engine) — a fully generic cheatsheet is only clean once types/statuses are spec-driven; relates-to EPIC-325.
  - Left Draft/backlog, not dispatched. @tech-lead to break into tasks once FEAT-326 lands; will need a dev for the generic render and @tech-writer for format/voice sign-off (see US3).
<!-- sq:discussion:end -->
