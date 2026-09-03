---
id: TASK-666
sequence_id: 666
type: task
title: Task-local, store-scoped active transaction context
status: Done
author: tech-lead
refs:
- ADR-663:implements
- BUG-657:fixes
description: Publish the live transaction context in a ContextVar set inside the locks
  and scoped to its owning store; drop the pre-lock load.
subentities:
- local_id: ST1
  title: Bind the transaction context task-locally, inside the locks
  status: Todo
- local_id: ST2
  title: Scope the ambient context to its owning store
  status: Todo
- local_id: ST3
  title: Drop the pre-lock load and pin reflog attribution
  status: Todo
created_at: '2026-07-27T14:22:54Z'
updated_at: '2026-07-28T07:24:44Z'
---
<!-- sq:body -->
Implements ADR-663 §4, in `src/squads/_index/_store.py` only. Fixes the latent misattribution
in BUG-657 — and note the ADR chooses the *second* of that bug's two proposed fixes: moving the
assignment to just after Layer 1 only narrows the window (Layer 1 is per-event-loop, so two
loops or two threads in one process still share the attribute), and a shared instance attribute
stays wrong on its own terms once one process serves more than one squad.

## Problem

`IndexStore.transaction()` builds the transaction context from a pre-lock `load()` and
publishes it on the shared instance attribute `self._current_ctx` before any of the three locks
is held. `store._log()` — every mutation core's reflog buffer — reads that attribute to find
the active transaction. Two transactions in flight against the same instance would let the
second one's pre-lock assignment steal the first one's buffer. Item and index data are
unaffected (they flow through the local `ctx`); reflog attribution is not.

## Design

- Publish the live transaction context in a task-local binding — a `ContextVar` in
  `_index/_store.py` — set **after** all three locks are held and after the in-lock load has
  produced the context.
- Release it with the `set` token in the `finally`, so the previous value is *restored* rather
  than clobbered.
- The context carries its owning store's identity, and `_log()` ignores an ambient context
  belonging to a different store. This is required, not defensive: a task-local binding is
  process-wide where the instance attribute was per-instance, and one process may serve two
  squads — routine for a long-lived server or daemon, not hypothetical.
- Drop the pre-lock `load()`. It exists only to construct a context that is then discarded and
  rebuilt from the in-lock load; removing it closes the unlocked window that made
  misattribution possible and saves a full index read per transaction.

Derived rule to hold: this is the **only** ambient value the store may carry, its lifetime is
exactly the lock hold, and no per-transaction state may live on `IndexStore` instance
attributes.

## Why task-local rather than an explicit handle

Explicit threading below the CLI edge is the preferred shape and the eventual one — but it means
changing what `transaction()` yields, and with it ~20 logging sites, ~30 transaction sites and
the bulk importer's direct-core calls: churn concentrated in the one module where churn is
least welcome, for a defect that is currently unreachable. The task-local binding already
satisfies the binding content of the project's ambient-state decisions — task-local value, no
shared module name, no cross-request or cross-squad leakage, one long-lived process observably
identical to N fresh ones.

Record the promotion trigger in the docstring: the first time the transaction API is revised for
fan-out/batch mutation or for the server, the handle becomes an explicit parameter and the
ambient binding is deleted.

This is **not** a `RequestContext` field. That type is a frozen bag of ambient *inputs* bound
once at the CLI edge for the whole request; a transaction context is shorter-lived than a
request, engine-internal, and mutated by appending to its reflog buffer.

## Constraints

- `_index/_store.py` is the only source file this task changes (plus tests). Concurrent work on
  the same durability model touches the service layer and the item-file layer; stay out of both.
- Follow the existing `ContextVar` precedent in this codebase (`_context.py`,
  `_rendering/_engine.py`): one module-level `ContextVar`, read only through a small accessor,
  never a per-field variable and never a bare module global.
- Do not change the lock order (Layer 1 → 2 → 3), the acquire/release `try`/`finally` shape, or
  the reflog's post-commit never-raise contract.
- `tests/meta`'s module-level-mutable-state guard must stay green. A `ContextVar` call is not
  one of the constructs it flags, but run that directory and — if the new binding is flagged —
  add an allowlist entry with a one-line reason rather than restructuring the code.
- No CLI surface change, no schema bump.
- Full gate before handoff: `uv run --all-extras pyright`, `uv run --all-extras ruff check .`,
  `uv run --all-extras ruff format --check .`, and the suite.

## Acceptance

- Nothing reads or writes `self._current_ctx` any more, and no per-transaction state lives on an
  `IndexStore` instance attribute.
- The context is bound only while all three locks are held, and the previous binding is restored
  on exit — including when an exception escapes the body and on cancellation.
- Two concurrent transactions in one process each buffer their own reflog entries, with no
  cross-attribution.
- A second `IndexStore` for a different squad in the same process never sees the first's ambient
  context.
- `transaction()` performs one index load, not two.
- Reflog output for the ordinary single-transaction path is unchanged.
- `uv run sq check` clean; the suite green.
<!-- sq:body:end -->

## Subtasks

_Add with `sq task 666 add-subtask "<title>"`; track with `sq task 666 subtask <n> update --status <Status>`._

<!-- sq:subtasks -->

<!-- sq:subtask:ST1 -->
### ST1 — Bind the transaction context task-locally, inside the locks

<!-- sq:subtask:ST1:body -->
Replace the `self._current_ctx` instance attribute with a module-level `ContextVar` in
`_index/_store.py`, read only through a small accessor.

Set it *after* Layer 3 is acquired and after the in-lock load has produced the context — that is
the whole point: the binding must not exist while the store holds no lock. Keep the token
returned by `set()` and `reset()` it in the same `finally` that releases Layer 3, so a sibling or
nested binding is restored rather than cleared to `None` (today's code assigns `None` on exit,
which clobbers).

`_log()` reads the ambient context through the accessor and stays a no-op outside a transaction,
exactly as now. Its buffer-time snapshot of ts/actor/session must not change: a single
transaction can buffer several ops under different ambient actor/clock bindings, so each op keeps
its own snapshot.

Acceptance:
- The binding is absent outside a transaction, present inside, and *restored* (not cleared) after
  a nested bind unwinds.
- An exception escaping the transaction body still restores the previous binding.
- Cancellation of the transaction restores it too.
<!-- sq:subtask:ST1:body:end -->

#### Discussion

<!-- sq:subtask:ST1:discussion -->
<!-- sq:subtask:ST1:discussion:end -->
<!-- sq:subtask:ST1:end -->

<!-- sq:subtask:ST2 -->
### ST2 — Scope the ambient context to its owning store

<!-- sq:subtask:ST2:body -->
The transaction context carries the identity of the store that opened it, and `_log()` ignores an
ambient context whose owner is a different store.

This is required by the change, not defensive coding: a task-local binding is process-wide where
the instance attribute was per-instance, so without the check a `_log()` call on store B inside
store A's transaction would land in A's reflog buffer — a regression the old shape did not have.
One process may serve two squads, which a long-lived server or daemon makes routine.

Prefer the store *instance* as the identity: it is the faithful translation of the per-instance
semantics being replaced. The resolved index path is a weaker check, because two `IndexStore`
instances may point at the same squad dir and would then be treated as one. State the choice and
its reason in a comment.

Acceptance:
- With two `IndexStore`s on two squad dirs in one process, a `_log()` call on store B inside store
  A's open transaction is a no-op rather than landing in A's buffer.
- A `_log()` call on the store that actually owns the open transaction still buffers, unchanged.
<!-- sq:subtask:ST2:body:end -->

#### Discussion

<!-- sq:subtask:ST2:discussion -->
<!-- sq:subtask:ST2:discussion:end -->
<!-- sq:subtask:ST2:end -->

<!-- sq:subtask:ST3 -->
### ST3 — Drop the pre-lock load and pin reflog attribution

<!-- sq:subtask:ST3:body -->
Remove the pre-lock `load()`. It exists only to build a context that is immediately discarded and
rebuilt from the in-lock load, so deleting it both closes the unlocked window that made
misattribution possible and saves a full index read per transaction.

Then pin what the whole change is for:

- Two concurrent `store.transaction()` calls in one process (drive them through a task group)
  each buffer only their own reflog ops — no cross-attribution.
- The ordinary single-transaction path produces byte-identical reflog output to before: op order,
  buffer-time timestamps, actor and session lineage.
- `transaction()` loads the index exactly once. The saved read is part of the point, so assert
  the count rather than trusting it.

Name tests by the behaviour they pin, never by a ticket id — repo rule, and `tests/meta`
enforces it. Run `tests/meta` as well: it guards module-level mutable state, and a new
module-level binding is exactly what this task adds.

Acceptance:
- The fan-out test shows each transaction's buffer holding only its own ops.
- Reflog assertions for the normal path are unchanged.
- The load count per transaction is 1.
- Full suite green under `uv run --all-extras`; run it once, redirect to a file, and read the
  file rather than re-running to reslice output.
<!-- sq:subtask:ST3:body:end -->

#### Discussion

<!-- sq:subtask:ST3:discussion -->
<!-- sq:subtask:ST3:discussion:end -->
<!-- sq:subtask:ST3:end -->
<!-- sq:subtasks:end -->

## Discussion

<!-- sq:discussion -->
- [2026-07-27T15:55:40Z] Catherine Manager:
  - Implementation note from the build: with one ambient slot per task (a single ContextVar, required for the foreign-store guard to mean anything), a genuinely nested different-store transaction makes the outer store's _log() no-op while the inner is active, then restore on unwind. Verified by test and intentional — a real per-store binding would need more ambient state than ADR-663 §4 allows. No such call site exists today; revisit with Robert if one appears.
<!-- sq:discussion:end -->
