---
id: TASK-303
sequence_id: 303
type: task
title: Add sq check for unwritten placeholder sub-entity bodies
status: Done
parent: FEAT-289
author: tech-lead
assignee: python-dev
description: New warn-level _check_* helper flagging any sub-entity body still equal
  to its kind placeholder
subentities:
- local_id: ST1
  title: Add _check_unwritten_subentity_bodies helper + wire into check()
  status: Done
  story: US1
- local_id: ST2
  title: Emit the check at warn severity per the recorded decision
  status: Done
  story: US2
- local_id: ST3
  title: 'Tests: add-story stub is flagged, real body clears; CLI smoke'
  status: Done
  story: US1
created_at: '2026-07-06T11:37:22Z'
updated_at: '2026-07-06T12:10:01Z'
---
<!-- sq:body -->
Add a new per-item check to `_services/_maintenance.py` that flags any sub-entity (story/subtask/finding) whose stored body is still exactly its kind's placeholder stub, so unwritten acceptance criteria surface in `sq check` instead of hiding behind a plausible title. Covers FEAT-289 US1 (the detector) and US2 (the severity decision, resolved below).

Mechanics: bodies live in the item file's `:body` marker region (NOT in frontmatter/index), so unlike the sibling index-only `_check_*` helpers this one must read each sub-entity-bearing item's file text. Pull the region with `sections.get_section(text, discussion.body_tag(kind, local_id))` and compare (stripped) against `discussion.body_placeholder(kind)`. Exact-equality only — any divergence, even a single edited char, is treated as written (no heuristics, no false positives). Mirror the existing `_check_subentity_status`/`_check_subentity_title_lengths` shape and wire the call into `check()`.

SEVERITY DECISION (US2), made here by the tech lead — no architect ADR needed: emit at 'warn' (advisory, non-blocking), NOT a Draft->Ready-gating error. Precedent: the closest sibling `_check_subentity_title_lengths` (ADR-000167) is an advisory warn, and the override split (ADR-000085 §3) reserves 'error' for structural breakage (missing marker) while soft-quality signals stay warn. Rationale: an unwritten body is an authoring-quality defect, not index corruption; a warn surfaces it on every `sq check` without hard-blocking legacy squads that carry existing stub debt (retroactive cleanup is explicitly out of scope for FEAT-289). Record this rationale as a design comment on this task at implementation time so US2's 'resolved explicitly, citing precedent' acceptance is satisfied on the record.

Done when: `sq check` emits one warn-level CheckIssue per sub-entity whose body equals its kind placeholder, naming the parent item id + local id (e.g. 'FEAT-123 US3 body is unwritten (still the placeholder stub)'); a sub-entity with any real/divergent body is never flagged; the helper is wired into `check()`; service + CLI smoke tests are green (see subtasks); pyright/ruff clean.

Constraint: no sq/FEAT/TASK IDs may appear in the shipped source or test names — name tests by behavior. Referencing FEAT-289/US1/US2 here in this task body is fine (squad item files are the sanctioned place); the code carries none.
<!-- sq:body:end -->

## Subtasks

_Add with `sq task 303 add-subtask "<title>"`; track with `sq task 303 subtask <n> update --status <Status>`._

<!-- sq:summary -->
| Subtask | Status | Assignee | Title | Story |
| --- | --- | --- | --- | --- |
| ST1 | Done |  | Add _check_unwritten_subentity_bodies helper + wire into check() | US1 |
| ST2 | Done |  | Emit the check at warn severity per the recorded decision | US2 |
| ST3 | Done |  | Tests: add-story stub is flagged, real body clears; CLI smoke | US1 |
<!-- sq:summary:end -->

<!-- sq:subtasks -->

<!-- sq:subtask:ST1 -->
### ST1 — Add _check_unwritten_subentity_bodies helper + wire into check()

<!-- sq:subtask:ST1:head -->
**Status:** 🟢 Done
**Implements:** US1 — As a tech lead, I want sq check to flag unwritten sub-entity bodies
<!-- sq:subtask:ST1:head:end -->

<!-- sq:subtask:ST1:body -->
Done when: a new `_check_unwritten_subentity_bodies(index)` (async or with file access) exists in `_services/_maintenance.py`, iterates every sub-entity-bearing item, reads each item file's `:body` region via `sections.get_section(text, discussion.body_tag(kind, local_id))`, and appends one CheckIssue for each whose stripped body equals `discussion.body_placeholder(kind)` exactly. The helper is called from `check()` alongside the other `_check_*` calls. Issue text names parent id + local id, e.g. 'FEAT-123 US3 body is unwritten (still the placeholder stub)'. Note the file-read wrinkle: siblings take the in-memory index, but body prose is not indexed, so this helper reads files (reuse the `_scan_for_check`/on_disk pattern or read per item).
<!-- sq:subtask:ST1:body:end -->

#### Discussion

<!-- sq:subtask:ST1:discussion -->
<!-- sq:subtask:ST1:discussion:end -->
<!-- sq:subtask:ST1:end -->

<!-- sq:subtask:ST2 -->
### ST2 — Emit the check at warn severity per the recorded decision

<!-- sq:subtask:ST2:head -->
**Status:** 🟢 Done
**Implements:** US2 — As an architect, I want the check's severity left as an open decision
<!-- sq:subtask:ST2:head:end -->

<!-- sq:subtask:ST2:body -->
Done when: each emitted CheckIssue uses the 'warn' level (advisory, non-blocking exit code), matching `_check_subentity_title_lengths`; no Draft->Ready transition gate is added (that enforcement is explicitly out of scope for FEAT-289). Post a short design comment on TASK-303 recording the warn choice + precedent (ADR-000167 advisory title-length check; ADR-000085 §3 warn/error split) so US2's 'resolved explicitly, citing precedent' acceptance is on the record.
<!-- sq:subtask:ST2:body:end -->

#### Discussion

<!-- sq:subtask:ST2:discussion -->
<!-- sq:subtask:ST2:discussion:end -->
<!-- sq:subtask:ST2:end -->

<!-- sq:subtask:ST3 -->
### ST3 — Tests: add-story stub is flagged, real body clears; CLI smoke

<!-- sq:subtask:ST3:head -->
**Status:** 🟢 Done
**Implements:** US1 — As a tech lead, I want sq check to flag unwritten sub-entity bodies
<!-- sq:subtask:ST3:head:end -->

<!-- sq:subtask:ST3:body -->
Done when: a service-level test seeds a story via add-story (leaving the placeholder), asserts `check()` reports a warn issue for it, then sets a real body and asserts the issue clears; plus a CLI smoke test asserting `sq check` output includes the new line for an unwritten-story fixture. Cover a divergent-but-short body to prove no false positive. Name tests by behavior only — no sq/FEAT/TASK IDs in test names or source.
<!-- sq:subtask:ST3:body:end -->

#### Discussion

<!-- sq:subtask:ST3:discussion -->
<!-- sq:subtask:ST3:discussion:end -->
<!-- sq:subtask:ST3:end -->
<!-- sq:subtasks:end -->

## Discussion

<!-- sq:discussion -->
- [2026-07-06T11:44:29Z] Operator:
  - ST2 severity decision recorded: emitting at warn (advisory, non-blocking) — precedent: the sibling title-length check (ADR-000167) is an advisory warn, and the override warn/error split (ADR-000085 §3) reserves error for structural breakage (missing marker); an unwritten body is an authoring-quality defect, not index corruption, so no Draft->Ready gate is added.
- [2026-07-06T11:44:43Z] Elias Python:
  - Recording as Elias Python (python-dev): severity decision above stands — warn/advisory, matching ADR-000167 precedent; not gating Draft→Ready.
- [2026-07-06T11:44:49Z] Elias Python:
  - Done: added _check_unwritten_subentity_bodies in src/squads/_services/_maintenance.py (warn-level, reads the sub-entity's :body region via sections.get_section + discussion.body_tag, compares stripped text to discussion.body_placeholder(kind)).
  - Service test + CLI smoke test added in tests/test_unwritten_subentity_body_check.py: stub flagged, real body clears, divergent-but-short body not a false positive, subtask/finding kinds covered.
  - pyright/ruff/ruff-format clean; targeted test file green (16/16).
- [2026-07-06T12:00:01Z] Elias Python:
  - Coordinator caught a premature Done: I'd marked ST1-ST3+TASK-303 Done before the full suite finished. Reverted; suite run surfaced 3 real regressions from the new check (Class B) plus goldens needing regen from TASK-304's skill text (Class A). Re-running the full suite before touching status again.
<!-- sq:discussion:end -->
