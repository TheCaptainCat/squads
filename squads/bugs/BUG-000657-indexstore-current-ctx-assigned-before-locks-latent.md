---
id: BUG-657
sequence_id: 657
type: bug
title: IndexStore._current_ctx assigned before locks (latent)
status: Open
author: qa
created_at: '2026-07-24T14:38:38Z'
updated_at: '2026-07-27T14:26:23Z'
---
<!-- sq:body -->
## Symptom

None observed today — a latent structural risk found while root-causing the two status-
drift bugs (see the linked findings), not a reproduced failure.

## Root cause

`IndexStore.transaction()` assigns the shared instance attribute `self._current_ctx`
*before* any of the three transaction locks are acquired:

```
ctx = _TransactionCtx(db=await self.load())
self._current_ctx: _TransactionCtx | None = ctx   # src/squads/_index/_store.py:291
async with self._loop_lock():                     # Layer 1 acquired here
    ...
```

`self.store._log()` (used by every mutation core to buffer a reflog entry) reads
`self._current_ctx` to find the active transaction's buffer. If two `store.transaction()`
calls were ever in flight concurrently against the *same* `IndexStore` instance (same
process), the second call's pre-lock assignment at line 291 could overwrite
`self._current_ctx` before the first call's body finishes logging — misattributing that
transaction's reflog entries onto the second transaction's buffer. (Item/index data itself
is unaffected — that flows through the local `ctx` variable, not the shared attribute.)

## Repro

Not reproduced — this requires two concurrent `store.transaction()` calls within one
process, and a repo-wide grep (`asyncio.gather`, `anyio.create_task_group`, `TaskGroup(`)
found zero call sites outside tests that would create that fan-out. Filed as a latent
landmine for future code, not a live defect.

## Severity

Low/latent. Unreachable with the current codebase's call patterns; would only bite a
future concurrent-fan-out feature (e.g. a batch command that runs several mutations via
`asyncio.gather`).

## Proposed fix

- Move the `self._current_ctx = ctx` assignment to after Layer 1 (the per-loop lock) is
  acquired, so it's only ever set while a transaction actually holds exclusive access.
- Or make the active-transaction handle task/loop-local instead of a single instance
  attribute, so concurrent transactions (should they ever exist) each see only their own.
<!-- sq:body:end -->

## Discussion

<!-- sq:discussion -->
- [2026-07-24T14:40:22Z] Pierre Chat:
  - Investigated + fix proposed; parked — not scheduled for 0.12.1.
- [2026-07-27T13:53:03Z] Pierre Chat:
  - Unparked: fix all three. Architect settles the .md-vs-index ordering/atomicity model in an ADR first, then implement.
- [2026-07-27T14:06:14Z] Robert Architect:
  - ADR-663 §4 settles the handle: task-local, store-scoped, set inside the locks, token-reset; the discarded pre-lock load goes with it. Moving the assignment after Layer 1 only narrows the window (Layer 1 is per-loop).
- [2026-07-27T14:26:23Z] Olivia Lead:
  - Broken down: TASK-666 closes this (ADR-663 §4 — task-local, store-scoped transaction context set inside the locks, token-reset; the discarded pre-lock load goes with it). The ADR takes the second of the two proposed fixes; moving the assignment after Layer 1 only narrows the window.
<!-- sq:discussion:end -->
