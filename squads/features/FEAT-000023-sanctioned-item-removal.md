---
id: FEAT-000023
sequence_id: 23
type: feature
title: Sanctioned item removal
status: Ready
parent: EPIC-000012
author: product-owner
priority: medium
refs:
- BUG-000022:depends-on
description: 'sq <type> <n> remove: a safe, first-class way to delete or retire an
  item — today the only option is manual file surgery plus hand-editing the index'
subentities:
- local_id: US1
  title: As an operator who created an item by mistake, I want sq remove to take it
    off the books safely, so that I never have to hand-edit files or the index
  status: Todo
- local_id: US2
  title: As a teammate whose items reference the removed one, I want removal to refuse
    or cleanly sever those refs, so that nothing dangles silently
  status: Todo
- local_id: US3
  title: As someone auditing a squad later, I want number gaps to be explainable,
    so that a missing sequence number reads as a recorded removal, not corruption
  status: Todo
created_at: '2026-06-10T13:52:25Z'
updated_at: '2026-06-11T07:54:55Z'
---
<!-- sq:body -->
## Problem

squads has no way to remove an item. Cancelling keeps it on the books (correct for work that was
considered and dropped), but a mistakenly-created item, a test artifact, or a rolled-back decision
has no exit: the operator's only option is deleting the `.md` by hand and repairing — or worse,
hand-editing `.squads.json`. We watched this live (2026-06-10): two manual surgeries, one reused
sequence number (BUG-000022), zero help or guard rails from the tool. If the tool doesn't offer a
sanctioned path, operators will keep improvising one, and the improvisations are exactly what
break the invariants.

## Value

A first-class `sq <type> <n> remove` makes the dangerous thing safe: refs are checked instead of
silently dangling, the counter's high-water mark survives (numbers are never re-issued), and the
removal leaves a trace instead of rewriting history. It also closes a durable-format question that
1.0 must answer: what does a *gap* in the sequence mean, and what may readers of a squad directory
assume about it?

## Scope

- `sq <type> <n> remove` — deletes the `.md` and the index entry **in one transaction**, while
  preserving the counter (depends on BUG-000022's fix; the high-water mark must be deletion-proof).
- **Ref safety**: refuse when other items reference the target (listing them), with `--force` to
  sever — severed refs are removed from the referrers' frontmatter, not left dangling. Children
  must be re-parented or the removal refused.
- **Audit trail**: the removal is recorded (at minimum in the operator's terminal + a check-able
  trace; design decides between a tombstone entry, a log, or relying on git history) so a number
  gap is explainable.
- **Confirmation UX**: destructive verb — interactive confirm unless `--yes`.
- Design question for the ADR: hard delete vs. an `Archived`-style soft state for work items; the
  team should hold the line that *cancel* is for dropped work and *remove* is for things that
  should never have existed.

## Acceptance

- `sq <type> <n> remove` removes file + index entry atomically; the next `create` never reuses the
  removed number (test proves it, including across a follow-up `repair`).
- Removal refuses on incoming refs/children unless forced, and forced removal leaves no dangling
  refs (`sq check` clean afterwards).
- The removal is traceable after the fact; docs explain remove-vs-cancel.
- No invariant requires hand-editing `.squads.json` for any removal scenario we document.
<!-- sq:body:end -->

## User Stories

_Add with `sq feature 23 add-story "As a <role>, I want … so that …"`; track with `sq feature 23 story <n> update --status <Status>`._

<!-- sq:summary -->
| Story | Status | Assignee | Title |
| --- | --- | --- | --- |
| US1 | Todo |  | As an operator who created an item by mistake, I want sq remove to take it off the books safely, so that I never have to hand-edit files or the index |
| US2 | Todo |  | As a teammate whose items reference the removed one, I want removal to refuse or cleanly sever those refs, so that nothing dangles silently |
| US3 | Todo |  | As someone auditing a squad later, I want number gaps to be explainable, so that a missing sequence number reads as a recorded removal, not corruption |
<!-- sq:summary:end -->

<!-- sq:stories -->

<!-- sq:story:US1 -->
### US1 — As an operator who created an item by mistake, I want sq remove to take it off the books safely, so that I never have to hand-edit files or the index

<!-- sq:story:US1:head -->
**Status:** ⚪ Todo
<!-- sq:story:US1:head:end -->

<!-- sq:story:US1:body -->
**Acceptance:** `sq <type> <n> remove` deletes the .md and index entry in one transaction with interactive confirmation (`--yes` to skip); the counter's high-water mark survives removal and a subsequent `sq repair` (never re-issues the number).
<!-- sq:story:US1:body:end -->

#### Discussion

<!-- sq:story:US1:discussion -->
<!-- sq:story:US1:discussion:end -->
<!-- sq:story:US1:end -->

<!-- sq:story:US2 -->
### US2 — As a teammate whose items reference the removed one, I want removal to refuse or cleanly sever those refs, so that nothing dangles silently

<!-- sq:story:US2:head -->
**Status:** ⚪ Todo
<!-- sq:story:US2:head:end -->

<!-- sq:story:US2:body -->
**Acceptance:** removal refuses when incoming refs or children exist, listing them; `--force` severs refs from referrers' frontmatter and requires children to be re-parented first; `sq check` is clean after any removal.
<!-- sq:story:US2:body:end -->

#### Discussion

<!-- sq:story:US2:discussion -->
<!-- sq:story:US2:discussion:end -->
<!-- sq:story:US2:end -->

<!-- sq:story:US3 -->
### US3 — As someone auditing a squad later, I want number gaps to be explainable, so that a missing sequence number reads as a recorded removal, not corruption

<!-- sq:story:US3:head -->
**Status:** ⚪ Todo
<!-- sq:story:US3:head:end -->

<!-- sq:story:US3:body -->
**Acceptance:** every removal leaves a queryable trace (tombstone/log per the design ADR); docs state the remove-vs-cancel rule (cancel = dropped work, remove = should never have existed).
<!-- sq:story:US3:body:end -->

#### Discussion

<!-- sq:story:US3:discussion -->
<!-- sq:story:US3:discussion:end -->
<!-- sq:story:US3:end -->
<!-- sq:stories:end -->

## Discussion

<!-- sq:discussion -->
<!-- sq:discussion:end -->
