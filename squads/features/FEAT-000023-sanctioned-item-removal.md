---
id: FEAT-000023
sequence_id: 23
type: feature
title: Sanctioned item removal
status: Done
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
  status: Done
- local_id: US2
  title: As a teammate whose items reference the removed one, I want removal to refuse
    or cleanly sever those refs, so that nothing dangles silently
  status: Done
- local_id: US3
  title: As someone auditing a squad later, I want number gaps to be explainable,
    so that a missing sequence number reads as a recorded removal, not corruption
  status: Done
created_at: '2026-06-10T13:52:25Z'
updated_at: '2026-06-15T09:21:50Z'
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
| US1 | Done |  | As an operator who created an item by mistake, I want sq remove to take it off the books safely, so that I never have to hand-edit files or the index |
| US2 | Done |  | As a teammate whose items reference the removed one, I want removal to refuse or cleanly sever those refs, so that nothing dangles silently |
| US3 | Done |  | As someone auditing a squad later, I want number gaps to be explainable, so that a missing sequence number reads as a recorded removal, not corruption |
<!-- sq:summary:end -->

<!-- sq:stories -->

<!-- sq:story:US1 -->
### US1 — As an operator who created an item by mistake, I want sq remove to take it off the books safely, so that I never have to hand-edit files or the index

<!-- sq:story:US1:head -->
**Status:** 🟢 Done
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
**Status:** 🟢 Done
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
**Status:** 🟢 Done
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
- [2026-06-15T08:21:25Z] Olivia Lead:
  - Breakdown: one implementation task, TASK-000111 (@python-dev), subtasks mapped ST1→US1 (atomic remove + counter survives repair + confirm/--yes), ST2→US2 (ref/child safety + --force sever, sq check clean), ST3→US3 (queryable trace + remove-vs-cancel docs).
  - Recon: remove_item already exists (_services/_items.py:180) but bare — index delete + backend remove_artifacts + optional --purge — and only wired as rm for roles/skills/operators. Work-item types have no remove verb (build_item_app, _cli/_items.py). BUG-000022 (Done) already makes the counter monotonic, so high-water-mark preservation is free once removal goes through a transaction; ST1 just has to prove it across a repair.
  - @architect DESIGN GATE before code: the FEAT-23 ADR questions must be settled first — hard-delete vs Archived soft-state, and the audit-trace mechanism (tombstone vs log vs git history). A tombstone in .squads.json must stay rebuildable from .md (Invariant 1) or it breaks sq repair. Implementation starts once the ADR is Accepted.
- [2026-06-15T08:27:03Z] Robert Architect:
  - DESIGN GATE SETTLED — ADR-000114 (Accepted). @python-dev can implement TASK-000111 against this contract; no ambiguity left on the four questions:
  - 1) SEMANTICS — hard delete. remove unlinks the .md and deletes the index entry (del db.items[seq]) in ONE store.transaction(). No Archived soft-state. Hold the line: Cancelled = work considered and dropped (stays on the books, terminal status); remove = should-never-have-existed (leaves the corpus entirely).
  - 2) AUDIT TRACE — the FEAT-000024 reflog line IS the trace. NO index tombstone (would break Invariant 1 — repair has no .md to rebuild it from), NO tombstone .md, NO separate removal log. TASK-111 adds zero bespoke audit code: it runs the removal through the transaction seam carrying op=remove + a gone-item snapshot (type/title/status/severed-ref list) in the delta, so the reflog writer (TASK-000112) emits one reconstructable line. If 111 lands before the reflog seam (112): ship with terminal-output trace + the op/delta capture stubbed at the call site (no-op writer until 112). Do NOT add a stopgap tombstone to bridge — git history of the deleted file covers the interim; the durable queryable trace is carried by FEAT-000024.
  - 3) REFS — default refuses on incoming refs (via SquadsDB.backrefs/refs_in) or children, listing offenders. --force severs each incoming ref from the REFERRER's frontmatter (reuse the width-tolerant _id_matches/rm_ref sever logic in _services/_refs.py, persist via update_frontmatter) inside the SAME transaction as the delete. sq check MUST be clean afterwards (no dangling ref/parent). Children are NOT auto-reparented — --force still refuses while children remain; operator re-parents or removes them first.
  - 4) ID REUSE — counter high-water mark is preserved; the freed number is NEVER reissued. remove touches db.items only, never db.counter. allocate_id only bumps; load() only raises the counter never lowers; repair() floors at max(previous_counter, max_n) (ADR-000104). A number GAP is a first-class sanctioned state meaning 'existed and was removed' — check/repair already treat gaps as normal; do not add any contiguity assertion.
  - CONTRACT OBLIGATION -> defer onto FEAT-000013 (1.0 contract): the reflog 'remove' line schema (its fields) AND the rule that a sequence-number gap is a sanctioned, documented state a reader may rely on (gaps normal, numbers never reissued, a removal is explained by the reflog not the index) must be stated in the 1.0 contract doc. This rides FEAT-000024 US3's reflog-schema-tier promise — flag it there; do not re-implement it in TASK-111.
- [2026-06-15T09:07:14Z] Mara Tester:
  - QA sign-off (Mara Tester) — all acceptance criteria verified against ADR-000114.
  - US1 (atomic remove + counter invariant): PASS. Hard delete confirmed atomic; counter high-water mark preserved through removal and repair; freed number never reissued.
  - US2 (ref/child safety + sq check clean): PASS. Default refusal with offender list; --force severs refs atomically; children block removal even with --force; sq check clean after every scenario.
  - US3 (traceable removal + remove-vs-cancel docs): PASS. Remove vs. Cancel section in sq workflow explains the semantic split, command forms, ref/child safety, sanctioned-gap invariant. Reflog stub (no-op until FEAT-000024/TASK-000112 lands) assembles correct op/delta per ADR-000114 §2 composition contract.
  - Feature is ready to close — implementation matches the ADR on all four design points.
<!-- sq:discussion:end -->
