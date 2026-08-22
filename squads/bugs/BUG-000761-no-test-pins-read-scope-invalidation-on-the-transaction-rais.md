---
id: BUG-761
sequence_id: 761
type: bug
title: No test pins read-scope invalidation on the transaction raise path
status: Verified
author: qa
refs:
- REV-757
created_at: '2026-08-21T17:52:58Z'
updated_at: '2026-08-21T20:48:00Z'
---
<!-- sq:body -->
Test-coverage gap on the integrity core, not a behaviour defect: the behaviour this asks for
is already correct today, and was driven (with two `IndexStore`s on one directory, mirroring
the pattern below) before filing this.

`IndexStore.transaction()`'s docstring and the request-scoped-snapshot decision both state
invalidation is unconditional — "commit or raise". The mechanism is the `finally` inside
`transaction()` (`src/squads/_index/_store.py`, the block right after the in-lock
`_read_from_disk` / `yield ctx.db` / `_atomic_write` sequence): `scope.snapshots.pop(self,
None)` runs there regardless of whether the body between the `yield` and the write raised.

`tests/unit/test_read_scope.py` covers the commit path
(`test_scope_is_invalidated_after_a_commit_so_a_later_read_sees_the_mutation`) and the
`overwrite()` path (`test_overwrite_also_invalidates_the_scope`). Nothing in that file — or
elsewhere — exercises the raise path: a caller's body inside `async with store.transaction()
as db:` raising before `_atomic_write` is ever reached. Break the `pop` so it only runs on the
success path (e.g. move it after the `_atomic_write` call, or wrap only the happy path in the
`finally`) and the full suite stays green, because nothing asserts that a read taken after a
transaction that raised sees a concurrent committer's write rather than the stale pre-raise
snapshot.

The raise path a new test must cover, mirroring the existing commit-path test's shape: inside
one `read_scope()`, `load()` to prime a snapshot on `store_a`, open `store_a.transaction()`,
mutate `db`, then raise before the block ends; catch it; commit an unrelated mutation through
a second `IndexStore` (`store_b`) on the same directory; then call `store_a.load()` again and
assert it returns the *second* store's committed value, not the primed snapshot and not the
value the raising transaction attempted to write. This pins both halves of "commit or raise, no
second clause" in the same file the commit half already lives in.

This gap tracks the request-scoped-snapshot decision's own "falsification the implementation
owes" list, which names the commit-path falsification and never mentions the raise path — worth
adding to both the code comment and the test suite together.

Secondary, smaller gap noted in the same pass, worth picking up in the same test but not the
reason for filing: nothing in `test_read_scope.py` asserts the scope closes exactly once per
CLI invocation and never survives into the next one. That guarantee currently rests on Click's
`call_on_close` contract rather than anything this repo owns, so a regression there would be
silent; low priority since it is not this repo's invariant to defend directly, but cheap to pin
alongside the raise-path test while in the file.
<!-- sq:body:end -->

## Discussion

<!-- sq:discussion -->
- [2026-08-21T19:44:26Z] Catherine Manager:
  - Fix landed in 3fadd44 on release/0.14 (TASK-765). Two tests added, 9 pass in the file, and the commit touches tests/unit/test_read_scope.py only. QA drove the falsification named in this bug: moving the snapshot pop out of the unconditional finally and onto the success path only makes the new test fail with the stale pre-transaction snapshot still being served, and reverting restores green. The raise path is now pinned.
- [2026-08-21T20:47:59Z] Mara Tester:
  - Verified as a reviewer, not by re-running my own test. git show --stat 3fadd44 confirms src/ is untouched by that commit (test-only, tests/unit/test_read_scope.py alone).
  - Independently re-applied the mutation this bug specifies (moved scope.snapshots.pop(self, None) off the unconditional finally onto the success-only path right after _atomic_write): the new raise-path test goes red with the same AssertionError (assert 0 != 0, must not be the stale pre-transaction snapshot), and it is the only test in the file that fails -- 8 passed, 1 failed. Reverted the mutation; git diff --stat on src/ is empty again; all 9 pass.
<!-- sq:discussion:end -->
