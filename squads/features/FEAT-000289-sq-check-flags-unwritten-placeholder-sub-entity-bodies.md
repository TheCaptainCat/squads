---
id: FEAT-289
sequence_id: 289
type: feature
title: sq check flags unwritten placeholder sub-entity bodies
status: Draft
author: product-owner
subentities:
- local_id: US1
  title: As a tech lead, I want sq check to flag unwritten sub-entity bodies
  status: Todo
- local_id: US2
  title: As an architect, I want the check's severity left as an open decision
  status: Todo
- local_id: US3
  title: As a PO, I want the skill to state the body-write step as a done-criterion
  status: Todo
created_at: '2026-07-04T20:16:38Z'
updated_at: '2026-07-04T20:17:36Z'
---
<!-- sq:body -->
## Problem

`sq feature <n> add-story` (and the subtask/finding equivalents) seed a brand-new sub-entity body
with a known placeholder stub from `_discussion.py::_PLACEHOLDER` (per kind — story/subtask/
finding), e.g. for a story: `_Write the user story (e.g. "As an <role>, I want … so that …") and
its acceptance criteria here…_`. In `sq stories` / `sq tree` a story with a real title and this
stub *looks* populated, so agents move on without ever writing the acceptance criteria. Nothing
downstream catches it:

- `sq check` lints markers, dangling links, status validity, and index drift — it never inspects
  sub-entity body content.
- The `sq-feature` skill mentions the story body only as a subordinate clause, not as an ordered
  step or a definition-of-done.

The result: features/tasks routinely go Draft → Ready (and beyond) carrying stories whose
acceptance criteria were never written, and the board stays green throughout. FEAT-283 shipped
exactly this way until caught by hand.

The placeholder text is a known constant per kind, so detecting an unwritten body is a trivial
equality/prefix check against `_discussion.py::_PLACEHOLDER[kind]` — no heuristics needed.

## Scope

1. **`sq check` gains a new check: flag any sub-entity (story/subtask/finding) whose body still
   equals its kind's placeholder.** One `CheckIssue` per unwritten sub-entity, naming the item and
   local id, e.g. `FEAT-123 US3 body is unwritten (still the placeholder stub)`. Mirrors the
   existing per-item `_check_*` helpers in `_services/_maintenance.py` (alongside
   `_check_subtask_stories` / `_check_subentity_status` / `_check_subentity_title_lengths`).
   - **Open point for the architect:** should this be a `warning` (always surfaced, never blocks)
     or an `error` gated specifically at the Draft→Ready transition (blocking promotion), or both
     (warning in general `sq check`, promoted to error only when the parent item is leaving
     Draft)? This feature does not decide that — it's a design call for whoever picks this up,
     informed by how `sq check`'s error/warning severities are already used elsewhere (e.g. the
     override checks' version-drift-warn / missing-marker-error split).
2. **Sharpen the `sq-feature` skill** (and, if applicable, the equivalent guidance for
   subtask-bearing types) so that filling in the story body is an explicit ordered step in the
   product-owner's "Do" list — not folded into a parenthetical — and add to "Watch for": *"a story
   is not done until its body carries acceptance criteria — an unwritten placeholder body is a
   defect even if the title reads fine."* This is a managed-skill change: it lives wherever the
   skill body is generated/sourced and regenerates into the on-disk skill via `sq sync`; it is not
   a hand-edit of the `.md` file under `squads/agents/skills/`.

## Acceptance criteria

- `sq check` reports an issue for every sub-entity whose body is exactly its kind's placeholder
  constant (story/subtask/finding), naming the parent item and local id.
- A sub-entity with any real body content (including a body that merely starts to diverge from
  the placeholder) is not flagged — no false positives on legitimately short bodies.
- The severity question (warning vs. Draft→Ready-gating error, or both) is resolved by the
  architect/tech-lead at design/implementation time, not preemptively decided here.
- The `sq-feature` skill's product-owner section lists writing the story body as its own ordered
  "Do" step, and "Watch for" states the definition-of-done: a story isn't done until its body
  carries acceptance criteria. Change flows through the skill's managed source and `sq sync`, not
  a direct edit to the generated file.
- Test coverage: a service-level test seeds a story with `add-story` (leaving the placeholder),
  asserts `sq check` flags it, then writes a real body and asserts the flag clears.

## Out of scope

- No change to what `add-story`/`add-subtask`/`add-finding` seed — the placeholder stub itself
  stays; this only detects when it's left unwritten.
- No enforcement mechanism beyond `sq check` in this feature (e.g. no CLI hard-block on
  transitions) — that's exactly the open severity question left to the architect.
- No content-quality judgment of a *written* body (e.g. "too short", "no bullet list") — only
  exact-placeholder detection.
- No retroactive sweep/fix of existing items with unwritten bodies — this feature only adds the
  detector; cleaning up existing debt is a separate follow-up if needed.
<!-- sq:body:end -->

## User Stories

_Add with `sq feature 289 add-story "As a <role>, I want … so that …"`; track with `sq feature 289 story <n> update --status <Status>`._

<!-- sq:summary -->
| Story | Status | Assignee | Title |
| --- | --- | --- | --- |
| US1 | Todo |  | As a tech lead, I want sq check to flag unwritten sub-entity bodies |
| US2 | Todo |  | As an architect, I want the check's severity left as an open decision |
| US3 | Todo |  | As a PO, I want the skill to state the body-write step as a done-criterion |
<!-- sq:summary:end -->

<!-- sq:stories -->

<!-- sq:story:US1 -->
### US1 — As a tech lead, I want sq check to flag unwritten sub-entity bodies

<!-- sq:story:US1:head -->
**Status:** ⚪ Todo
<!-- sq:story:US1:head:end -->

<!-- sq:story:US1:body -->
As a tech lead reviewing a feature, I want `sq check` to flag any story/subtask/finding whose body
is still exactly its placeholder stub (`_discussion.py::_PLACEHOLDER[kind]`), so that unwritten
acceptance criteria surface before the item is promoted instead of hiding behind a plausible title.

**Acceptance criteria**

- New `_check_*` helper in `_services/_maintenance.py`, wired into `check()` alongside
  `_check_subtask_stories` / `_check_subentity_status` / `_check_subentity_title_lengths`.
- For every sub-entity (story, subtask, finding) whose stored body equals its kind's placeholder
  constant exactly, emit one `CheckIssue` naming the parent item id and local id, e.g.
  `FEAT-123 US3 body is unwritten (still the placeholder stub)`.
- A sub-entity with any real content — including a body that has started to diverge from the
  placeholder text — is never flagged. No false positives.
- Service-level test: `add-story` a fresh story (leave the seeded placeholder), assert `sq check`
  reports it; then set a real body and assert the issue clears.
- CLI smoke test: `sq check` output includes the new issue line for a fixture with an unwritten
  story.
<!-- sq:story:US1:body:end -->

#### Discussion

<!-- sq:story:US1:discussion -->
<!-- sq:story:US1:discussion:end -->
<!-- sq:story:US1:end -->

<!-- sq:story:US2 -->
### US2 — As an architect, I want the check's severity left as an open decision

<!-- sq:story:US2:head -->
**Status:** ⚪ Todo
<!-- sq:story:US2:head:end -->

<!-- sq:story:US2:body -->
As an architect, I want the warning-vs-error severity of the new placeholder-body check left as an
explicit open decision for design time, so that we don't accidentally hard-block Draft→Ready (or
any transition) before agreeing on the right gate.

**Acceptance criteria**

- The feature body and this story both state the open question plainly: should an unwritten
  sub-entity body be (a) a `warning` always surfaced in `sq check` but never blocking, (b) an
  `error` specifically at the Draft→Ready transition of the *parent* item (blocking promotion),
  or (c) both — warning in general `sq check`, escalated to error only when the parent is leaving
  Draft?
- Whoever picks up implementation (architect/tech-lead) resolves this explicitly — e.g. via an ADR
  or a design comment on the implementing task — citing precedent from `sq check`'s existing
  severity split (the override checks: version-drift is a warning, a missing marker is an error).
- This story does not ship code; it exists so the decision isn't silently defaulted to whichever
  is easiest to implement.
<!-- sq:story:US2:body:end -->

#### Discussion

<!-- sq:story:US2:discussion -->
<!-- sq:story:US2:discussion:end -->
<!-- sq:story:US2:end -->

<!-- sq:story:US3 -->
### US3 — As a PO, I want the skill to state the body-write step as a done-criterion

<!-- sq:story:US3:head -->
**Status:** ⚪ Todo
<!-- sq:story:US3:head:end -->

<!-- sq:story:US3:body -->
As a product owner following the `sq-feature` skill, I want filling in a story's body to be its
own explicit ordered step (not a parenthetical) and stated as a definition-of-done, so that I stop
mistaking a titled-but-stub story for a finished one.

**Acceptance criteria**

- In the product-owner section's "Do" list, writing the story body is its own bullet/step,
  distinct from "add persona-worded user stories" — currently the body-writing guidance is folded
  into a parenthetical on the add-story bullet.
- "Watch for" gains: *"a story is not done until its body carries acceptance criteria — an
  unwritten placeholder body is a defect even if the title reads fine."*
- This is a managed-skill change: edit wherever `sq-feature`'s body is generated/sourced (per
  CLAUDE.md, skills regenerate via `sq sync`), not a hand-edit of the on-disk
  `squads/agents/skills/SKILL-000196-sq-feature.md`.
- If other subtask-bearing item-type skills (e.g. `sq-task`) share the same soft-guidance gap for
  subtask bodies, note it — but this story's acceptance is scoped to `sq-feature`; extending to
  siblings can be a fast-follow.
<!-- sq:story:US3:body:end -->

#### Discussion

<!-- sq:story:US3:discussion -->
<!-- sq:story:US3:discussion:end -->
<!-- sq:story:US3:end -->
<!-- sq:stories:end -->

## Discussion

<!-- sq:discussion -->
- [2026-07-04T20:16:47Z] Nina Product:
  - Left parentless (no EPIC-12 parent): this is a board-honesty / authoring-quality fix — sq check catching unwritten sub-entity bodies and sharpening sq-feature guidance — not part of the 1.0 stability promise, which EPIC-12 scopes to the durable .md format, CLI grammar, and --json shapes. Sibling context: this fix's root cause is exactly what let FEAT-283's stories ship as stub bodies until caught by hand.
<!-- sq:discussion:end -->
