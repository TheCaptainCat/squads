---
id: TASK-765
sequence_id: 765
type: task
title: Pin read-scope invalidation on the transaction raise path
status: Done
author: tech-lead
assignee: qa
priority: medium
refs:
- BUG-761:fixes
description: 'Test-only: the raise half of commit-or-raise, driven red against a broken
  pop and green against current code'
created_at: '2026-08-21T19:36:55Z'
updated_at: '2026-08-22T09:26:28Z'
---
<!-- sq:body -->
Test-only work on the integrity core. **The behaviour is already correct** — this closes a coverage
gap, so nothing in `src/` changes and the value of the work is entirely in the falsification.

`IndexStore.transaction()`'s docstring and ADR-753 both state read-scope invalidation is
unconditional — "commit or raise, no second clause". The mechanism is the `finally` inside
`transaction()` (`src/squads/_index/_store.py`): `scope.snapshots.pop(self, None)` runs whether or not
the body between the `yield` and the write raised.

`tests/unit/test_read_scope.py` covers the commit path
(`test_scope_is_invalidated_after_a_commit_so_a_later_read_sees_the_mutation`) and the `overwrite()`
path (`test_overwrite_also_invalidates_the_scope`). Nothing anywhere exercises the **raise** path.
Break the `pop` so it only runs on success — move it after the `_atomic_write` call, or wrap only the
happy path — and the whole suite stays green. That is the gap.

## The test to add

In `tests/unit/test_read_scope.py`, mirroring the shape of the commit-path test that already lives
there:

1. Inside one `read_scope()`, call `load()` on `store_a` to prime a snapshot.
2. Open `store_a.transaction()`, mutate `db`, and raise before the block ends. Catch it.
3. Commit an unrelated mutation through a second `IndexStore` (`store_b`) on the same directory.
4. Call `store_a.load()` again and assert it returns **the second store's committed value** — not the
   primed snapshot, and not the value the raising transaction attempted to write.

Asserting all three of those outcomes is the point: a test that only checks "not the primed snapshot"
would also pass if the failed transaction's attempted write had somehow landed.

## Also pin, while in the file

Nothing asserts the scope closes exactly once per CLI invocation and never survives into the next one.
That guarantee currently rests on Click's `call_on_close` contract rather than on anything this repo
owns, so a regression would be silent. Lower value than the raise path — it is not this repo's
invariant to defend directly — but cheap to add alongside, so add it: after an invocation completes,
including on an error-exit path, the scope ContextVar is back to empty, and a second invocation in the
same process starts with no inherited snapshot.

## Acceptance criteria

- **Both directions driven, and both reported.** The new raise-path test must:
  - **fail** against the mutation — break the `pop` so it only runs on the success path, run the test,
    watch it go red, and record the actual failure output;
  - **pass** against unmodified `src/`, with the mutation reverted.

  A test that only passes proves nothing here, because the behaviour already works. The handoff
  comment states both results explicitly. Restore `src/` fully afterwards — `git diff --stat` on
  `src/` must be empty when you hand back.
- The invocation-boundary test above is added and passing.
- **No production code changes.** This item touches `tests/unit/test_read_scope.py` only. If driving
  the falsification surfaces an actual defect in the `finally`, stop and report it rather than fixing
  it here — that would be a different item with a different risk profile.
- The new tests follow the file's existing fixtures and style, and are named for the behaviour they
  pin rather than for a ticket.
- The full `pytest` suite is green, `uv run --all-extras pyright` / `ruff check` /
  `ruff format --check` are clean, and `uv run sq check` is clean.

## Handoff

**Do not edit `CHANGELOG.md`.** Several items in this batch run concurrently and a shared file would
have them racing. This one likely warrants no adopter-facing entry at all — it changes no behaviour —
so say that in your handoff comment rather than inventing one, and the tech lead decides.
<!-- sq:body:end -->

## Subtasks

_Add with `sq task 765 add-subtask "<title>"`; track with `sq task 765 subtask <n> update --status <Status>`._

<!-- sq:summary -->
<!-- sq:summary:end -->

<!-- sq:subtasks -->
<!-- sq:subtasks:end -->

## Discussion

<!-- sq:discussion -->
- [2026-08-21T19:37:39Z] Olivia Lead:
  - Test-only, assigned qa. Acceptance is the falsification in both directions with both results reported — a passing test alone proves nothing when the behaviour already works — plus git diff --stat on src/ empty at handoff, and a stop-and-report rule if driving the mutation surfaces a real defect in the finally.
- [2026-08-21T19:43:42Z] Mara Tester:
  - Added two tests to tests/unit/test_read_scope.py: the raise-path falsification (test_scope_survives_a_raising_transaction_so_a_later_read_sees_a_concurrent_commit) and the invocation-boundary pin (test_scope_context_closes_after_every_invocation_success_or_error).
  - Falsification driven both directions. Mutation applied to src/squads/_index/_store.py: moved scope.snapshots.pop(self, None) out of the unconditional finally and re-added it only right after await self._atomic_write(ctx.db) succeeds -- success-path only, exactly the break this bug specified.
  - RED against the mutation: AssertionError: must not be the stale pre-transaction snapshot -- assert 0 != 0 (store_a.load() after the raise still returned the primed counter=0 snapshot instead of store_b's committed counter=99). 8 passed, 1 failed.
  - Reverted the mutation (git checkout -- src/squads/_index/_store.py); git diff --stat on src/_index/_store.py is empty. GREEN against unmodified src/: all 9 tests in the file pass.
  - Gates: ruff check / ruff format --check clean (fixed one SIM117 nested-with flag in my own new test), pyright clean on the file, pytest tests/meta 172 passed, sq check clean. No CHANGELOG entry -- test-only, no adopter-facing behaviour change.
  - Committed 3fadd44 on release/0.14, tests/unit/test_read_scope.py only, unpushed.
<!-- sq:discussion:end -->
