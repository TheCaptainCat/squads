---
id: FEAT-336
sequence_id: 336
type: feature
title: Audit agent/user-facing surfaces for vocab-hardcoding defects
status: Draft
parent: EPIC-335
author: product-owner
refs:
- FEAT-326:depends-on
- FEAT-334
subentities:
- local_id: US1
  title: As a planner, I want the full surface list confirmed complete
  status: Todo
- local_id: US2
  title: As a planner, I want each surface's audience/altitude/vocab captured
  status: Todo
- local_id: US3
  title: As a planner, I want a recommended fix per surface
  status: Todo
created_at: '2026-07-08T15:09:51Z'
updated_at: '2026-07-08T15:11:01Z'
---
<!-- sq:body -->
## What this delivers

A single audit pass over every agent- and user-facing doc/generated surface
this project ships, cataloguing which ones carry the three defects found in
`workflow.md.j2` (FEAT-334): hardcoded type/status/role vocabulary,
duplication of the same guidance across surfaces, and unclear/overlapping
altitude between a surface and whatever it duplicates or points at. The
output is a matrix (one row per surface) plus a recommended fix per row, not
code changes — this feature scopes the *survey*, not the fixes.

## Candidate surfaces (starting list — the audit must confirm/extend this,
not just this list)

- `src/squads/_rendering/templates/workflow.md.j2` (the trigger — already
  scoped as FEAT-334, included here for completeness of the matrix)
- The `squads` skill body (`agents/squads_skill.md.j2`) and the per-type
  `sq-<type>` skills (`agents/item_skill.md.j2`, playbook-generated)
- The CLAUDE.md managed section (`claude/claude_section.md.j2`) — confirmed
  during scoping to carry the *same* `authoring_owner('feature')` /
  `authoring_owner('task')` / `item_subentity_kind(...) == 'story'|'subtask'`
  hardcoded pattern as `workflow.md.j2`, almost verbatim
- The AGENTS.md equivalent (`agents_md/agents_section.md.j2`,
  `_backends/_agents_md/`)
- Shipped user docs under `docs/` — at minimum `internals.md`, `stability.md`,
  `workflow.md`, `roles.md`, `agents.md`, `adoption.md`, `backends.md`,
  `overrides.md`, `recipes.md`, `tutorial.md`, `faq.md`, `migration.md`,
  `README.md` (grep found direct type-name prose in several of these; the
  audit should check each, not assume)
- `sq workflow` terminal output (renders the same template as the cheatsheet
  — same defect, one command)
- `sq --help` / `sq <type> --help` text
- Role and skill pointer files under `squads/agents/roles/`,
  `squads/agents/skills/`, and the `.claude/` thin pointers generated from
  them

## Per-surface capture (the audit's output shape)

For every surface in the final list, record:

- **Audience** — who reads it (an agent mid-task, a human onboarding, an
  external adopter reading shipped docs, …)
- **Altitude / role** — what depth/scope it's supposed to cover, and how
  that's supposed to differ from neighboring surfaces
- **Hardcodes vocab?** — yes/no, with the specific hardcoded names/branches
  if yes
- **Duplicates another surface?** — which one, and whether the duplication is
  incidental (fixable by pointing one at the other) or load-bearing (the two
  genuinely need separate copies for different audiences)
- **Recommended fix** — one of: genericize (make it spec/playbook-driven),
  dedupe (point at another surface instead of re-narrating), redefine
  altitude (keep both but make the depth/scope difference explicit and
  enforced), or leave (no defect found)

## Non-goals

- Actually implementing any fix beyond FEAT-334 (the cheatsheet) — this
  feature's deliverable is the audit findings; each flagged surface that
  needs a genericize/dedupe/redefine fix gets its own future feature scoped
  off these findings, not built here.
- Re-litigating FEAT-334's own scope or acceptance criteria — this feature
  treats FEAT-334 as already-scoped and just includes it as one row in the
  matrix for completeness.

## Sequencing

Depends on FEAT-326 (remove the `ItemType`/`Status` enums) for the same
reason as FEAT-334 — auditing against a still-partially-hardcoded engine
means re-auditing once the engine is fully spec-driven. Parent: EPIC-335.

At dispatch, this is architect-shaped work (surveying the codebase's
generated surfaces and the docs tree end to end) with tech-writer input on
the docs/ half; this feature defines the what/why and the capture shape
only.
<!-- sq:body:end -->

## User Stories

_Add with `sq feature 336 add-story "As a <role>, I want … so that …"`; track with `sq feature 336 story <n> update --status <Status>`._

<!-- sq:summary -->
| Story | Status | Assignee | Title |
| --- | --- | --- | --- |
| US1 | Todo |  | As a planner, I want the full surface list confirmed complete |
| US2 | Todo |  | As a planner, I want each surface's audience/altitude/vocab captured |
| US3 | Todo |  | As a planner, I want a recommended fix per surface |
<!-- sq:summary:end -->

<!-- sq:stories -->

<!-- sq:story:US1 -->
### US1 — As a planner, I want the full surface list confirmed complete

<!-- sq:story:US1:head -->
**Status:** ⚪ Todo
<!-- sq:story:US1:head:end -->

<!-- sq:story:US1:body -->
Walk the repo (templates under _rendering/templates/, docs/, _backends/, squads/agents/roles + skills, .claude/ pointers, CLI --help text) and reconcile against the starting candidate list in the feature body.

Acceptance: the audit's output lists every surface actually found, not just the starting candidates — any surface added beyond the starting list is called out explicitly as a gap the initial scoping missed.

Acceptance: for each surface, the audit records the exact file(s)/command(s) that produce it, so a follow-up feature can be scoped without re-discovering the surface from scratch.
<!-- sq:story:US1:body:end -->

#### Discussion

<!-- sq:story:US1:discussion -->
<!-- sq:story:US1:discussion:end -->
<!-- sq:story:US1:end -->

<!-- sq:story:US2 -->
### US2 — As a planner, I want each surface's audience/altitude/vocab captured

<!-- sq:story:US2:head -->
**Status:** ⚪ Todo
<!-- sq:story:US2:head:end -->

<!-- sq:story:US2:body -->
For each confirmed surface, capture audience, altitude/role, whether it hardcodes vocab (with the specific hardcoded names/branches), and whether it duplicates another surface (naming which one).

Acceptance: every surface in the matrix has all four fields filled — no row left with an unresolved 'TBD'.

Acceptance: a hardcoding finding cites the specific code (e.g. a template's {% if type == '...' %} branch or a doc's literal type-name prose), not a vague 'probably hardcoded' guess — this mirrors the concrete finding already made against claude_section.md.j2 during FEAT-334/EPIC-335 scoping.

Acceptance: a duplication finding names the specific other surface and the specific guidance that's repeated, and states whether the duplication is incidental (fixable by pointing one at the other) or load-bearing (genuinely needs two copies for two audiences).
<!-- sq:story:US2:body:end -->

#### Discussion

<!-- sq:story:US2:discussion -->
<!-- sq:story:US2:discussion:end -->
<!-- sq:story:US2:end -->

<!-- sq:story:US3 -->
### US3 — As a planner, I want a recommended fix per surface

<!-- sq:story:US3:head -->
**Status:** ⚪ Todo
<!-- sq:story:US3:head:end -->

<!-- sq:story:US3:body -->
For each surface, assign exactly one recommended fix: genericize, dedupe, redefine altitude, or leave.

Acceptance: every 'genericize' or 'dedupe' or 'redefine altitude' recommendation is written specifically enough that a tech-lead could turn it into a feature/task without re-doing the analysis (what changes, roughly how, and why).

Acceptance: a 'leave' verdict states why the surface is fine as-is (e.g. it intentionally hardcodes the bundled default and that's documented as such) rather than being a default for anything not yet analyzed.

Acceptance: the audit does not itself create the follow-up fix features — it hands the matrix back so those get scoped deliberately, one at a time, against current priorities.
<!-- sq:story:US3:body:end -->

#### Discussion

<!-- sq:story:US3:discussion -->
<!-- sq:story:US3:discussion:end -->
<!-- sq:story:US3:end -->
<!-- sq:stories:end -->

## Discussion

<!-- sq:discussion -->
<!-- sq:discussion:end -->
