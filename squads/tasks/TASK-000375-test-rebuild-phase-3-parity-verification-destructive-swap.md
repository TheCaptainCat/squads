---
id: TASK-375
sequence_id: 375
type: task
title: 'Test rebuild Phase 3: parity verification + destructive swap'
status: Draft
parent: FEAT-231
author: tech-lead
subentities:
- local_id: ST1
  title: Verify ledger parity before deleting the old suite
  status: Todo
  story: US4
created_at: '2026-07-10T04:48:20Z'
updated_at: '2026-07-10T04:50:03Z'
---
<!-- sq:body -->
## Phase 3 — Parity verification + destructive swap

Fourth phase of the FEAT-231 rebuild. **This is the one task that deletes the safety net.** It
verifies the new four-pillar battery has full coverage parity against the Phase-0 ledger, runs the
old and new suites together as the final cross-check, and ONLY THEN removes the old flat
`tests/test_*.py` files.

### REQUIRES OPERATOR SIGN-OFF
This task **requires operator sign-off on the Phase-0 coverage ledger before execution — do not
dispatch without it.** The deletion is irreversible relative to the working tree's safety net; the
operator must confirm the ledger is complete and every row is accounted for before the old suite is
torn down.

### Scope
- For every row in the Phase-0 coverage ledger, confirm a **green** test exists in the new suite at
  its planned home. No row may be unmapped or red. Produce a parity report (ledger row → new test
  id → pass).
- Run old + new suites **together** one last time (full sweep incl. `-m slow`) and confirm green.
- Only after parity is confirmed and the operator has signed off on the ledger: delete the old flat
  `tests/test_*.py` files (the ~80 files) and any now-orphaned helpers (`tests/_helpers.py` if fully
  superseded). Keep `tests/fixtures/corpus/*` (frozen), `tests/goldens/*` still in use, and the new
  layered tree.
- Confirm no dev-archaeology names or ticket-ID filenames remain anywhere under `tests/`.

### Dependencies
Depends on Phase 2 (the new battery must be complete + green) AND on operator sign-off on the
Phase-0 ledger. Blocks Phase 4. This is the destructive step — sequence strictly after Phase 2; do
not run concurrently with any authoring.

### Acceptance
- Parity report shows every ledger row mapped to a green new-suite test.
- Operator has signed off on the coverage ledger (record the sign-off as a comment on FEAT-231).
- Old flat suite deleted; `uv run pytest` (default, `-m 'not slow'`) green and < 30s; `-m slow`
  green; `uv run sq check` clean.
<!-- sq:body:end -->

## Subtasks

_Add with `sq task 375 add-subtask "<title>"`; track with `sq task 375 subtask <n> update --status <Status>`._

<!-- sq:summary -->
| Subtask | Status | Assignee | Title | Story |
| --- | --- | --- | --- | --- |
| ST1 | Todo |  | Verify ledger parity before deleting the old suite | US4 |
<!-- sq:summary:end -->

<!-- sq:subtasks -->

<!-- sq:subtask:ST1 -->
### ST1 — Verify ledger parity before deleting the old suite

<!-- sq:subtask:ST1:head -->
**Status:** ⚪ Todo
**Implements:** US4 — Coverage ledger preserves previously-caught bugs
<!-- sq:subtask:ST1:head:end -->

<!-- sq:subtask:ST1:body -->
_Describe this subtask here — free-form paragraphs or bullet lists._
<!-- sq:subtask:ST1:body:end -->

#### Discussion

<!-- sq:subtask:ST1:discussion -->
<!-- sq:subtask:ST1:discussion:end -->
<!-- sq:subtask:ST1:end -->
<!-- sq:subtasks:end -->

## Discussion

<!-- sq:discussion -->
<!-- sq:discussion:end -->
