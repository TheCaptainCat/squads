---
id: ADR-753
sequence_id: 753
type: decision
title: Request-scoped index snapshot for read paths
status: Accepted
author: architect
refs:
- BUG-747:addresses
- ADR-249
- TASK-752
- REV-757
description: One index load per invocation, held in an explicitly entered read scope
  that transactions never consult
created_at: '2026-08-21T12:47:47Z'
updated_at: '2026-10-25T21:47:46Z'
---
<!-- sq:body -->
## Context

Without a request-scoped snapshot, every read in one invocation deserialises and revalidates the
whole index again. `sq show <id> --json` on a 51-sub-entity item fans out one `get` per sub-entity,
and each `get` is `require_item(await self.store.load(), item_id)`. Measured on this squad's
720-item index, through the real CLI entry point:

| observation | value |
|---|---|
| `IndexStore.load` calls for one `show --json` | 55 |
| one `load()` on this corpus | 26.4 ms |
| of which the vocabulary and badge-code validation | 3.3 ms |
| in-process elapsed for the command | 1.60 s |

So 1.45 s of the 1.60 s was the repeated index load; the 53 re-reads of the item's own file were
10 ms in total.

Two properties are at stake, not one. Cost is the visible half. The other is that 55 independent
lock-free reads of a mutable file are 55 chances to observe different states, so one command can
render a torn view of the board.

## Decision

**1. A read scope, entered explicitly, holding one snapshot per store instance.**

A `_ReadScope` bound in a module-level `ContextVar` in `_index/_store.py` holds
`snapshots: dict[IndexStore, SquadsDB]`. `IndexStore.load()` consults the ambient scope and,
finding a snapshot this store filed, returns it; otherwise it reads from disk and files the
result. **Absent a scope, `load()` reads from disk** — the scope is opt-in and its absence is
never wrong, only slow.

This mirrors `_active_transaction` (ADR-663 §4): one module-level `ContextVar` for one
engine-internal, task-local concern, keyed on **store instance identity**, not the resolved index
path, because two `IndexStore`s can legitimately address one squad directory and one may be
mid-rebuild.

It is not a `RequestContext` field. `RequestContext` is a frozen record of ambient request
*inputs* the edge supplies (ADR-534); a lazily filled engine-internal cache is neither an input
nor frozen-friendly, and the store-identity ownership check is store-internal knowledge.

**2. The scope is anchored on the Click root context, with one `Service` per invocation.**

One user-facing invocation can cross the sync-to-async bridge more than once:
`sq <type> <n> <verb>` runs the Typer group's id-resolving callback and the leaf verb as two
sequential `anyio.run` calls. The scope therefore lives on the one object Click builds once per
dispatch and tears down once: the root `Context`. The first `command`-wrapped call opens the scope
and records its token on `root.meta`; `root.call_on_close` closes it after every nested command
has finished, success or error.

`get_service()` memoizes the invocation's `Service` on the same root context, gated on the same
condition that opens the scope, so both crossings share one `Service` and one `IndexStore`, and
the per-store snapshot is shared across them. One invocation observes one index state.

The scope and the memo are never an `IndexStore` instance attribute or an `open_service` flag.
`sq ui` builds one `Service` and holds it for the whole session, so an instance-lifetime cache
would pin a terminal browser to the state at launch while other processes mutate the index. The
failure modes decide this: forgetting to open a scope costs speed, while forgetting to disable an
instance cache silently serves stale data. `sq ui` is a sync command that never passes through
`command`, so it opens no scope and gets no memoized `Service`; if it wants the win it opens a
scope per user action.

**3. `transaction()` never consults the scope, and always invalidates on the way out.**

The disk read is a private `_read_from_disk(...)`; `load()` is the scope-aware wrapper over it;
`transaction()`'s in-lock load calls `_read_from_disk` directly. This is the load-bearing line:
`transaction()`'s db is what `_atomic_write` commits, and serving it a stale snapshot would write an
older index over a newer one, putting the index *behind* the markdown, the one skew direction the
durability model forbids (ADR-663). So invariant 8 holds by construction: the only db that reaches
`_atomic_write` is one read from disk under the file lock.

Invalidation (`scope.snapshots.pop(self, None)`) is in the same `finally` that resets
`_active_transaction` and releases the lock, **unconditionally**, commit or raise: one rule with no
second clause, at the cost of one re-read on an error path. `overwrite()` (whole-index replacement)
invalidates the same way.

**4. Two reads bypass the scope.**

- `validate_vocab=False` neither consults nor fills the scope. It is the recovery read (a corpus
  whose vocabulary no longer resolves); filling a shared slot with an unvalidated db would let a
  later validating caller skip a fail-closed check.
- `load(fresh=True)` is the explicit opt-out for a caller whose contract is "re-read the index
  right now": `sq check`'s confirm round (ADR-663 §3), whose false-positive suppression *is* that
  reload. Serving it the pre-scan snapshot would reintroduce spurious drift reports for any item
  mutated during the scan.

**5. `get()` returns a deep copy; a read result is never grafted into a transaction.**

`get()` returns a deep copy of the item, so an in-place mutation of a read result cannot
contaminate later reads in the same invocation (0.168 ms for the 51-sub-entity item, 0.009 ms for an
ordinary one). Copying the whole db per load is rejected on the measurement: 13.7 ms against a
26.4 ms load only halves the cost. Bulk read paths that iterate `db.items.values()` (`list_items`,
for one) return aliases into the snapshot.

The rule that governs every caller: **a read result may be mutated in place only by a caller that
also owns the write seam for it, and must never be grafted into a transaction db it did not come
from; a caller that does both copies first.** The backstop at every single-mutation frontmatter
write seam is `_itemfile.ensure_no_skew` (ADR-663 §1): a stale base refuses loudly rather than
overwriting disk.

**6. The vocabulary and badge-code validators run on every load, with no change-detection
trigger.**

- The multiplication was the cost, not the pass: at one load per invocation the check is 3.3 ms.
- It is a fail-closed load-boundary backstop that exists to catch what the override-aware
  live-index cross-check cannot see, precisely because it runs on every load. A check that runs
  only when a condition says so is one whatever makes the condition wrong can skip.
- A trigger needs a "spec and corpus unchanged" fingerprint: stored data derivable from the spec
  and the corpus, and a new thing that can be wrong about them.
- The check is what makes an override that shrinks a badge collection out from under a live corpus
  refuse rather than proceed.

**7. The pre-service index cross-check stays outside the scope.**

`validate_against_index_fail_closed` (`_workflow/_loader.py`) does its own synchronous
whole-index parse, and only when `.overrides/workflow.toml` is present. It is not put in the read
scope: the scope is keyed on `IndexStore` identity and holds snapshots a store filed, so admitting
a storeless caller would turn it into a general per-invocation cache, and memoizing a fail-closed
validation asserts more than memoizing a read (that the corpus has not changed since the check
passed). Its cost is bounded by count instead: it runs once per invocation, where the root
callback binds the active spec, and the `Service` composed afterwards reuses that checked spec.

## Consequences

- `sq show --json` on the worst item drops from about 1.60 s to about 0.2 s of in-process work,
  and every multi-`get` read path (`sq tree`, `sq list`, `sq check`'s first pass) gets the same
  reduction.
- One invocation observes one index state; what a command reports cannot shift mid-render.
- The re-reads of an item's own file remain: at 10 ms they do not justify a second cache, and a
  text cache over item files has a different invalidation story.
- `load()` has one keyword (`fresh`) and one private sibling (`_read_from_disk`).

## Falsification the tests owe

- `transaction()` reading through the scope must go red for writing a stale db over a newer index.
- Skipping the invalidation must go red for a read after a committed mutation reporting
  pre-mutation state.
- Removing `fresh=True` from `sq check`'s confirm round must go red with a spurious drift report.
- Removing the deep copy at `get()` must go red for a test that mutates a read result and re-reads.
- The load count, not the wall clock: one instrumented multi-sub-entity `show --json`, in both the
  `sq show <id>` and the `sq <type> <n> show` forms, does exactly one `load`, and the two bridge
  crossings share one store identity.
<!-- sq:body:end -->

## Discussion

<!-- sq:discussion -->
- [2026-08-21T12:53:46Z] `manager` Catherine Manager:
  - Verified the two load-bearing claims before accepting: _cli/_common.py:966 is the only anyio.run in the tree, and sq ui is a sync command holding one Service for the session (_cli/_ui.py), so it never crosses the bridge and keeps current behaviour. The invariant-8 argument for transaction() bypassing the scope is sound: the transaction db is the object _atomic_write commits.
- [2026-08-21T17:20:56Z] `architect` Robert Architect:
  - Amended in place (A1-A4 in the body) after the implementation on 9bd3560; the original text is unedited apart from one inline pointer in section 5, since it records what was decided.
  - A1: the scope anchor is the Click root context, not the anyio.run boundary — section 2 premise was true per Click command, false per user-facing invocation (sq <type> <n> <verb> crosses the bridge twice). A2: "one invocation, one index state" is KEPT as a guarantee and is not yet met (2 index reads for the addressed-item form, 3-5 whole-index parses with a workflow override); memoizing the Service on the same Click-root anchor closes it and makes the cross-call sharing observable.
  - A3: section 5 was factually wrong — list_items returns snapshot aliases (driven: 9/9 identity-aliases) and _refresh_catalog_extra grafts a pre-transaction object via db.add. The implementation is nonetheless safe, for a different reason: ensure_no_skew gates the graft on the whole non-excluded key space (driven both via updated_at and directly on status with the clock frozen equal), and the excluded set IS RoleDef.extra_keys() plus skills, which is the same set the graft has just reasserted from the resolved definition. Not introduced here — byte-identical at ea891a6, and the sequence behaves identically with no scope bound.
  - A4: the pre-service cross-check stays out of the read scope (storeless caller, differently shaped value, and it is a fail-closed validation not a read) — reduce it to once per invocation on the same anchor instead. A2 and A4 are engineering work on a surface this decision scoped out; they need their own item.
- [2026-10-25T21:47:46Z] `architect` Robert Architect:
  - 2026-10-25 audit: partly stale, body rewritten in the present tense; the decision is unchanged. Folded the four 2026-08-21 amendments: §2 anchors the scope on the Click root context (A1) and states the per-invocation Service memo that get_service() implements, so the one-index-state guarantee A2 reported unmet now holds; §5 replaces the false read-only-alias premise with A3's rule (no graft of a read result into a transaction; copy first), dropping the _refresh_*_extra and extra.skills sites that no longer exist; new §7 records A4's ruling, with the cross-check running once per invocation at the root spec bind. Removed line-number citations and the cProfile correction.
<!-- sq:discussion:end -->
