---
id: FEAT-166
sequence_id: 166
type: feature
title: Advisory warnings for over-long sub-entity titles
status: Done
author: product-owner
subentities:
- local_id: US1
  title: As an agent author, I want a warning when I give a sub-entity a long title
  status: Todo
- local_id: US2
  title: As a team lead, I want sq check to flag over-long sub-entity titles corpus-wide
  status: Todo
- local_id: US3
  title: As any agent, I want the sq-review / sq-task / sq-feature skills to tell
    me titles are handles
  status: Todo
created_at: '2026-06-23T07:48:38Z'
updated_at: '2026-06-23T10:06:55Z'
---
<!-- sq:body -->
## Problem

Agents routinely stuff a sub-entity's full description into its **title** and
leave the **body** as the untouched rendered placeholder. A corpus sweep found:

- 107 sub-entity bodies (findings / subtasks / stories) are empty or placeholder
  text; zero top-level item bodies are empty.
- 44 of those 107 have titles exceeding 120 chars; the worst case is a
  781-character finding title with an empty body.
- Review findings are the worst offenders: REV-165 findings F1 and F2 each
  carry a multi-sentence description in the title while the body is the default
  placeholder.

The root cause: there is no authoring-time signal that the title should be a
short *handle*, not the complete specification.

## Desired behaviour

All enforcement in this feature is **advisory / warn-and-proceed** — mirror the
existing `CreateResult.lane_warning` pattern from FEAT-122 (Slice B). A
warning is rendered by the CLI, the command exits 0, and the event is recorded
in the reflog. Empty bodies must NOT be gated — a one-line subtask with no body
is legitimately complete. The signal to act on is a **long title**, not an absent
body.

The exact character threshold and warning copy are open questions for the
architect / tech lead; this feature does not pre-decide them.

## In scope

1. **Authoring-time advisory** — `add-finding`, `add-subtask`, and `add-story`
   warn when the supplied title exceeds a threshold (approx. 80 chars is the
   working hypothesis; the architect / tech lead should settle the exact value
   and rationale). The warning points the author to set the body via
   `sq <type> <n> <kind> <k> body -m …`. The command proceeds regardless.

2. **`sq check` advisory rule** — a new check flags existing sub-entities with
   over-long titles so the corpus is auditable. This catches in-flight items
   (the 44 already in the backlog) without requiring a migration.

3. **Skill reinforcement** — the generated `sq-review`, `sq-task`, and
   `sq-feature` skills are updated to state explicitly that a sub-entity title
   is a short one-line handle and the spec / finding description belongs in the
   body.

## Out of scope

- Gating (hard-blocking) on long titles or empty bodies.
- Retroactive migration or auto-fill of existing bodies.
- Top-level item titles (the pattern there is already healthy per the corpus).

## Acceptance criteria

- Calling `add-finding` / `add-subtask` / `add-story` with a title that exceeds
  the threshold produces a visible advisory warning; the command still exits 0
  and creates the sub-entity.
- `sq check` reports over-long sub-entity titles as advisory findings (not
  errors); it exits 0 when no structural errors exist.
- `sq-review`, `sq-task`, and `sq-feature` skills each contain an explicit note
  that titles are handles and prose goes in the body.
- None of the above is a breaking change (no new mandatory arguments; no change
  to exit codes for previously-clean `sq check` runs).

## References

- FEAT-122 / REV-165 / ADR-163 — the advisory lane-warning pattern
  this feature mirrors.
- Corpus data: 107 empty sub-entity bodies, 44 with titles >120 chars.
<!-- sq:body:end -->

## User Stories

_Add with `sq feature 166 add-story "As a <role>, I want … so that …"`; track with `sq feature 166 story <n> update --status <Status>`._

<!-- sq:summary -->
| Story | Status | Assignee | Title |
| --- | --- | --- | --- |
| US1 | Todo |  | As an agent author, I want a warning when I give a sub-entity a long title |
| US2 | Todo |  | As a team lead, I want sq check to flag over-long sub-entity titles corpus-wide |
| US3 | Todo |  | As any agent, I want the sq-review / sq-task / sq-feature skills to tell me titles are handles |
<!-- sq:summary:end -->

<!-- sq:stories -->

<!-- sq:story:US1 -->
### US1 — As an agent author, I want a warning when I give a sub-entity a long title

<!-- sq:story:US1:head -->
**Status:** ⚪ Todo
<!-- sq:story:US1:head:end -->

<!-- sq:story:US1:body -->
## User story

As an agent author running `add-finding`, `add-subtask`, or `add-story`,
I want an advisory warning when my supplied title exceeds the configured
threshold, so that I am prompted to move the prose into the body instead.

## Acceptance criteria

- When the title supplied to `add-finding`, `add-subtask`, or `add-story`
  exceeds the threshold, the CLI prints an advisory warning (not an error).
- The warning message names the over-long title and points the author to the
  `sq <type> <n> <kind> <k> body -m …` command.
- The sub-entity is created regardless; the command exits 0.
- The advisory is recorded in the reflog alongside the create event.
- Titles at or below the threshold produce no warning.

## Open questions (for architect / tech lead)

- Exact threshold value (working hypothesis: ~80 chars).
- Whether the threshold is a hard-coded constant or a configurable value in
  `.squads.toml`.
- Warning copy and tone (must be actionable, not scolding).
<!-- sq:story:US1:body:end -->

#### Discussion

<!-- sq:story:US1:discussion -->
<!-- sq:story:US1:discussion:end -->
<!-- sq:story:US1:end -->

<!-- sq:story:US2 -->
### US2 — As a team lead, I want sq check to flag over-long sub-entity titles corpus-wide

<!-- sq:story:US2:head -->
**Status:** ⚪ Todo
<!-- sq:story:US2:head:end -->

<!-- sq:story:US2:body -->
## User story

As a team lead or product owner running `sq check`, I want over-long sub-entity
titles reported as advisory findings, so that I can audit and repair the corpus
without blocking normal `sq check` usage.

## Acceptance criteria

- `sq check` includes a pass that examines every sub-entity title across all
  item types (findings, subtasks, stories).
- Sub-entities whose title exceeds the threshold are reported as advisory
  warnings, not structural errors.
- The report lists item ID, sub-entity kind + index, the actual title length,
  and the threshold.
- `sq check` exits 0 when there are no structural errors, even when advisory
  title-length warnings are present (consistent with existing advisory-only
  checks).
- Running `sq check` on the current corpus surfaces the ~44 known offenders
  (titles >120 chars with empty bodies), confirming the rule fires correctly.

## Open questions (for architect / tech lead)

- Whether the `sq check` threshold is the same as the authoring-time threshold,
  or a separate (potentially looser) value.
- Output format: inline with existing `sq check` output, or a separate section.
<!-- sq:story:US2:body:end -->

#### Discussion

<!-- sq:story:US2:discussion -->
<!-- sq:story:US2:discussion:end -->
<!-- sq:story:US2:end -->

<!-- sq:story:US3 -->
### US3 — As any agent, I want the sq-review / sq-task / sq-feature skills to tell me titles are handles

<!-- sq:story:US3:head -->
**Status:** ⚪ Todo
<!-- sq:story:US3:head:end -->

<!-- sq:story:US3:body -->
## User story

As any agent using `sq-review`, `sq-task`, or `sq-feature`, I want the skill
to explicitly state that a sub-entity title is a short one-line handle and the
full description / spec / finding belongs in the body, so that I do not
misuse the title field even when no runtime warning fires.

## Acceptance criteria

- The `sq-review` skill's guidance for `add-finding` includes a note that the
  finding title is a short handle; the full description goes in the finding body.
- The `sq-task` skill's guidance for `add-subtask` includes a note that the
  subtask title is a short handle; implementation detail goes in the subtask body.
- The `sq-feature` skill's guidance for `add-story` includes a note that the
  story title is the short user-story phrase; acceptance criteria and detail go
  in the story body.
- The notes are concise (one or two sentences) and placed near the relevant
  command in the skill.
- The skills regenerate cleanly via `sq sync` with no manual edits required.

## Note

This story has no runtime code change — it is a template / content change in the
skill generation templates. It is the cheapest story in this feature and can
land independently.
<!-- sq:story:US3:body:end -->

#### Discussion

<!-- sq:story:US3:discussion -->
<!-- sq:story:US3:discussion:end -->
<!-- sq:story:US3:end -->
<!-- sq:stories:end -->

## Discussion

<!-- sq:discussion -->
- [2026-06-23T08:34:23Z] Robert Architect:
  - Settled the two open questions in ADR-167: title-length threshold = 120 chars (single constant in _interactions.py, not .squads.toml-configurable), advisory/warn-and-proceed, body presence never gated.
  - 120 chosen over the ~80 hypothesis to sit above the ambiguous 70–120 band — fires only on the 44 unambiguous-prose titles, stays silent through the borderline middle, so the advisory keeps its credibility.
  - Warning copy + scope (three add-* entry points, a sq check advisory rule, skill reinforcement) are pinned in the ADR. Ready for tech-lead breakdown when greenlit.
- [2026-06-23T08:39:27Z] Olivia Lead:
  - Breakdown complete against ADR-167 (threshold = 120, single constant in _interactions.py, advisory/warn-and-proceed mirroring CreateResult.lane_warning, body presence never gated). Three tasks, one per story — all parented to this feature and ref'd to ADR-167 (related). Left in Draft; nothing greenlit.
  - TASK-168 — Authoring-time advisory at add-finding/add-subtask/add-story (US1). Subtasks: ST1 add TITLE_ADVISORY_MAX=120 constant; ST2 carry advisory on the three service results (lane_warning pattern); ST3 render + reflog at the CLI edge. All ST → US1.
  - TASK-169 — sq check advisory rule (US2). Subtasks: ST1 pass walking every sub-entity title against the shared constant; ST2 emit advisory findings (ID/kind+index/length/threshold), still exit 0 when otherwise clean. All ST → US2.
  - TASK-170 — Skill reinforcement (US3). Subtasks: ST1 sq-review add-finding note; ST2 sq-task add-subtask note; ST3 sq-feature add-story note + sq sync idempotency check. All ST → US3.
  - Split rationale: US1 is the only runtime/CLI surface and owns the constant; US2 reuses that same constant for the audit; US3 is template-only and can land independently. sq check is clean.
<!-- sq:discussion:end -->
