---
id: TASK-000254
sequence_id: 254
type: task
title: 'Test rewrite: thread spec in singleton-touching tests, delete autouse reset
  fixture'
status: Done
parent: FEAT-000250
author: tech-lead
refs:
- TASK-000253:depends-on
created_at: '2026-06-30T09:53:05Z'
updated_at: '2026-06-30T10:30:15Z'
---
<!-- sq:body -->
**Part (d) of FEAT-000250 / ADR-000249 Option A. Last in sequence — after the production code
(a/b/c) compiles with the singleton deleted.**

Rewrite the singleton-touching test files to construct/pass a `WorkflowSpec` explicitly, and
**delete the `_reset_workflow_spec` autouse fixture** — there is no global left to reset, so
the deletion is a correctness win.

## Scope

- **`tests/conftest.py`** — delete the `_reset_workflow_spec` autouse fixture (`:78-90`) and
  its `reset_spec` import. If helpful, add a small fixture/helper that builds a `WorkflowSpec`
  (bundled or override) for tests to pass into `Service`/`IndexStore`.
- **Rewrite the singleton-touching test files** — per ADR-000249 "the 7 singleton-touching
  test files." Confirmed referencing the deleted API today (verify the exact set at
  implementation time — `grep -rl 'use_spec\|reset_spec\|_active_spec\|bundled_spec\|_terminal_ref\|WORKFLOWS\|SUBENTITY_WORKFLOWS\|ALLOWED_PARENTS' tests/`):
  - `tests/test_workflow_capability_flags.py`
  - `tests/test_workflow_spec.py`
  - `tests/test_workflow_override.py`
  - `tests/test_retype.py`
  - `tests/test_spine_characterization.py`
  - (plus any others the grep surfaces — the ADR's count is 7 incl./excl. conftest; reconcile
    and rewrite all that touch the deleted surface.)
  Replace `use_spec(...)`/`reset_spec()`/dict reach-ins with: constructing a `WorkflowSpec`
  and passing it through `Service`/`IndexStore`, or calling the new spec methods directly.
  `test_workflow_override.py` is the key one — it must now assert override behaviour via the
  threaded spec, not a global rebind.

## Constraints / gotchas

- **Behaviour byte-identical** — the FEAT-208 characterization, golden-lock, and spine tests
  are the safety net for the whole feature; they must stay green. Do NOT weaken assertions to
  make a rewrite pass — if a characterization test fails, that's a bug in a/b/c, not a test to
  loosen.
- Net test count likely drops (no more global-isolation scaffolding) — that's expected.
- This rides the EPIC-206 safety net that's slated for a clean rebuild later; keep changes
  minimal and faithful, don't pre-empt that rebuild.
- Run the full suite once to a file and read it (CLAUDE.md testing note); use `--lf`/`-x`
  while iterating.

## Acceptance

- No test references the deleted singleton surface; autouse reset fixture gone.
- Full suite green; `pyright` strict + `ruff` clean.
<!-- sq:body:end -->

## Subtasks

_Add with `sq task 254 add-subtask "<title>"`; track with `sq task 254 subtask <n> update --status <Status>`._

<!-- sq:summary -->
<!-- sq:summary:end -->

<!-- sq:subtasks -->
<!-- sq:subtasks:end -->

## Discussion

<!-- sq:discussion -->
<!-- sq:discussion:end -->
