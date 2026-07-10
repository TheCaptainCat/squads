---
id: TASK-376
sequence_id: 376
type: task
title: 'Test rebuild Phase 4: finalize conventions, ledger, QA acceptance'
status: Draft
parent: FEAT-231
author: tech-lead
created_at: '2026-07-10T04:48:21Z'
updated_at: '2026-07-10T04:49:54Z'
---
<!-- sq:body -->
## Phase 4 — Finalize conventions, ledger, QA acceptance

Final phase of the FEAT-231 rebuild. The battery is authored and the old suite is gone; this phase
turns the working artifacts into durable documentation and drives feature acceptance.

### Scope
- Finalize `tests/CONVENTIONS.md`: lock the layer structure, naming rules, per-layer fixture
  conventions, how to add a layer, and the golden-snapshot protocol as the standing contract for
  future test authors.
- Finalize the coverage ledger (proposed `tests/COVERAGE_LEDGER.md`) as the **durable
  characterization artifact** — the map a future developer reads before a schema/vocab change to
  see what each cluster protects and why. Reconcile it with the actual shipped test ids from
  Phase 3's parity report so it stays accurate.
- Update any project docs that reference the test layout (e.g. CLAUDE.md's Testing section if the
  layered structure / `-m 'not slow'` default changes the documented workflow).
- Hand to QA for **feature acceptance** against all of FEAT-231's acceptance criteria:
  1. default `uv run pytest` < 30s (scale excluded via `slow` + addopts);
  2. zero dev-archaeology vocab in any test name/file/dir;
  3. `CONVENTIONS.md` documents structure/naming/fixtures/golden protocol;
  4. coverage ledger maps every Principle-5 bug-class with no gaps;
  5. `uv run pytest -m slow` exercises scale paths and passes;
  6. `uv run sq check` clean.
  And the four user stories US1–US4.

### Dependencies
Depends on Phase 3 (swap complete). Last phase; on QA acceptance, FEAT-231 closes.

### Acceptance
- CONVENTIONS.md + COVERAGE_LEDGER.md finalized and committed alongside the new suite.
- QA verifies all six ACs + US1–US4 end-to-end and records the acceptance verdict on FEAT-231.
<!-- sq:body:end -->

## Subtasks

_Add with `sq task 376 add-subtask "<title>"`; track with `sq task 376 subtask <n> update --status <Status>`._

<!-- sq:summary -->
<!-- sq:summary:end -->

<!-- sq:subtasks -->
<!-- sq:subtasks:end -->

## Discussion

<!-- sq:discussion -->
<!-- sq:discussion:end -->
