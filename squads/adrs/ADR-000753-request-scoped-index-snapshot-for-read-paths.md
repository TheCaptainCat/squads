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
updated_at: '2026-08-21T17:21:07Z'
---
<!-- sq:body -->
## Context

`sq show <id> --json` on a 51-sub-entity item does one full index deserialise-and-revalidate
per sub-entity. Measured on this squad's 720-item index (driven; instrumented counters and
timers around the real CLI entry point, not cProfile arithmetic):

| observation | value |
|---|---|
| `IndexStore.load` calls for one `show --json` | 55 |
| `ServiceCore.get` calls | 54 |
| `SubentitiesMixin.get_block` calls | 51 |
| reads of the item's own 216 KB `.md` file | 53 |
| one `load()` on this corpus | 26.4 ms |
| of which the vocab + badge-code validation | 3.3 ms |
| in-process elapsed for the command | 1.60 s |

So 55 x 26.4 ms = 1.45 s of the 1.60 s is the repeated index load, and the 53 item-file
re-reads are 10 ms in total. The multiplication comes from
`_services/_subentities.py:716` (`get_block` opens with `await self.get(parent_id)`) fanned
out once per sub-entity by `_cli/_common.py:900`; `get` is
`return require_item(await self.store.load(), item_id)` (`_services/_base.py:758-759`).

One correction to the figures reported for this item: the "216 `Service.get` calls" number is
cProfile's per-resumption counting of an `async def` frame. The real call count is 54, and
the 55 loads are the real multiplication.

Two properties are at stake, not one. The cost is the visible half. The other half is that
55 independent lock-free reads of a mutable file are 55 chances to observe different states,
so one command can render a torn view of the board.

## Decision

**1. A read scope, entered explicitly, holding one snapshot per store instance.**

A `_ReadScope` object bound in a module-level `ContextVar` in `_index/_store.py`, holding
`snapshots: dict[IndexStore, SquadsDB]`. `IndexStore.load()` consults the ambient scope and,
finding a snapshot this store put there, returns it; otherwise it reads from disk and files
the result. **Absent a scope, `load()` behaves exactly as it does now** — the scope is opt-in
and its absence is never wrong, only slow.

This mirrors `_active_transaction` (`_index/_store.py:262-275`): one module-level ContextVar
for one engine-internal, task-local concern, keyed on **store instance identity** — not on the
resolved index path, for the reason already argued there (two `IndexStore`s can legitimately
address one squad directory, and one of them may be mid-rebuild).

Not a field on `RequestContext`. `RequestContext` is a frozen record of ambient request
*inputs* the edge supplies; a lazily-filled engine-internal cache is neither an input nor
frozen-friendly (every fill would be a rebind), and the store-identity ownership check is
store-internal knowledge. The same distinction `_active_transaction` already draws.

**2. The scope is entered at the one sync-to-async bridge, not at process start.**

`_cli/_common.py:955-972` (`command`) is documented as the single `anyio.run` per invocation;
that is the scope's boundary. Entering it inside the root coroutine, before the command body,
gives every task the command spawns an inherited binding.

Deliberately **not** an `IndexStore` instance attribute, and deliberately not a constructor
flag on `open_service`. `sq ui` builds one `Service` — and therefore one `IndexStore` — and
holds it for the whole session (`_cli/_ui.py:12,22`; `_tui/_app.py:18-23`), so an
instance-lifetime cache would pin a terminal browser to the state at launch while other
`sq` processes mutate the index underneath it. The failure modes decide this: forgetting to
open a scope costs speed, while forgetting to disable an instance cache silently serves stale
data. `sq ui` is a sync command and never passes through `command`, so it opts out for free
and keeps today's behaviour; if it later wants the win it opens a scope per user action,
which is a separate call.

**3. `transaction()` never consults the scope, and always invalidates on the way out.**

Extract the disk read into a private `_read_from_disk(...)`; `load()` becomes the scope-aware
wrapper over it; `transaction()`'s in-lock load calls `_read_from_disk` directly. This is the
load-bearing line of the whole change, because `transaction()`'s loaded db is the object
`_atomic_write` commits: serving it a stale snapshot would write an older index over a newer
one, reverting a committed mutation and putting the index *behind* the markdown — the one
skew direction the durability model forbids outright (`_index/_store.py` module docstring).
Invariant 8 therefore survives by construction, not by care: the only db that ever reaches
`_atomic_write` is one read from disk under the file lock.

Invalidation (`scope.snapshots.pop(self, None)`) goes in the same `finally` that resets
`_active_transaction` and releases Layer 3, **unconditionally** — commit or raise. On the
commit path it is required; on the raise path the index was not written so the snapshot is
still accurate, and dropping it anyway costs one 26 ms re-read in an error path in exchange
for a rule with no second clause. `overwrite()` (whole-index replacement) invalidates the
same way.

**4. Two reads bypass the scope, and one of them is a named call site.**

- `validate_vocab=False` never consults *or* fills the scope. It is the recovery read (a
  corpus whose vocabulary no longer resolves); filling a shared slot with an unvalidated db
  would let a later validating caller skip a fail-closed check, which is the wrong direction
  to fail.
- `load()` grows an explicit `fresh=True` opt-out for the caller whose contract is
  "re-read the index right now". `_services/_maintenance.py:1867` is that caller:
  `_confirm_cross_source` states in its own docstring that it "re-loads the index exactly
  once and re-observes exactly those candidates ... A candidate produced by a transaction
  that commits between the scan and this reload resolves here and is never reported."
  `sq check`'s false-positive suppression is that reload. Serving it the pre-scan snapshot
  would reintroduce spurious drift reports for any item mutated during the scan.

Every one of the 25 `store.load()` call sites is audited against that question before the
change lands. The one above is the only one found to depend on re-reading; the rest are
either pure reads or post-transaction reads that invalidation already covers.

**5. `get()` returns a deep copy of the item; the snapshot itself is never handed out
mutable.**

Today every `get()` returns an item out of a freshly parsed db, so no caller shares an
object with any other. A deep copy at that seam **preserves** that contract rather than
adding a new defence — and it is what keeps an accidental in-place mutation of a read result
from contaminating every later read in the same invocation. Measured: 0.168 ms for the
51-sub-entity item, 0.009 ms for an ordinary one, so 54 copies cost about 9 ms against the
1.45 s recovered. Copying the whole db per load is the alternative and is rejected on the
measurement: 13.7 ms against a 26.4 ms load only halves the cost.

Callers that iterate `db.items.values()` for a read (`list_items`, `roster_item`,
`_author_of`) keep receiving aliases and stay read-only, which is what they already are. All
in-place item mutation in the service layer today operates on a `transaction()` db, and
`_itemfile.ensure_no_skew` is the backstop at every single-mutation frontmatter write seam:
a stale base refuses loudly rather than overwriting disk.
**[Both of the first two sentences above are factually wrong — see Amendment A3, which
states the invariant that actually holds. They are left in place because they are what was
decided; do not read them as true.]**

**6. The vocabulary and badge-code validators keep running on every load, with no
change-detection trigger.**

Four reasons, in order of weight:

- The multiplication was the cost, not the pass. At one load per invocation the whole check
  is 3.3 ms — 0.2% of the measured command. There is nothing left to optimise.
- It is a fail-closed load-boundary backstop, and `_check_field_codes`'
  own docstring (`_index/_store.py:101-129`) is explicit that it exists to catch what the
  override-aware live-index cross-check cannot see, precisely *because* it runs on every
  load. A check that runs only when a condition says it should is a check that whatever
  makes the condition wrong can skip — the same fail-open shape that docstring records
  having already been paid for once.
- A trigger needs a "spec and corpus unchanged" fingerprint, which is stored data derivable
  from the spec and the corpus, and a new thing that can be wrong about them.
- The check is what makes an override that shrinks a badge collection out from under a live
  corpus refuse rather than proceed. Its cost is the price of that guarantee, and 3.3 ms is
  not a price worth negotiating.

## Consequences

- `sq show --json` on the worst item drops from about 1.60 s to about 0.2 s of in-process
  work; the eight-call fan-out the extension preview issues is no longer paced by its
  slowest member. Every multi-`get` read path (`sq tree`, `sq list` with per-item follow-ups,
  `sq check`'s first pass) gets the same reduction without being touched.
- One invocation observes one index state. That is a behaviour change, and the better one:
  the state a command reports can no longer shift mid-render.
- The 53 re-reads of the item's own file remain. At 10 ms measured they do not justify a
  second cache, and a text cache over item files is a different problem with a different
  invalidation story. Named here so it is a decision rather than an oversight.
- `load()` grows one keyword and one private sibling; no call site changes except the one
  that opts out.
- `_workflow/_loader.py`'s pre-service index cross-check keeps its own synchronous read and
  stays outside the scope, since it runs before any store exists.

## Falsification the implementation owes

- Break rule 3 — let `transaction()` read through the scope — and a test must go red for
  writing a stale db over a newer index. If nothing goes red, the test suite does not yet
  cover the one thing that makes this change safe.
- Break rule 3's invalidation and a read after a committed mutation in the same invocation
  must go red for reporting pre-mutation state.
- Remove the `fresh=True` at the `sq check` confirm round and a test must go red with a
  spurious drift report for an item mutated between the scan and the reload.
- Remove the deep copy at `get()` and a test that mutates a read result and re-reads must go
  red.
- Assert the load count directly, not the wall clock: one instrumented `show --json` on a
  multi-sub-entity item must show exactly one `load` per invocation. A timing assertion
  proves nothing on a loaded machine.

## Amendments

Recorded against the implementation this decision governs. Each amendment states what the
original text got wrong or left unsaid; the original text above is unedited except for one
inline pointer, because it is the record of what was decided.

### A1 (2026-08-21) — the scope's anchor is the Click root context, not the `anyio.run` boundary

§2's premise — that `command` is "the single `anyio.run` per invocation" — is true per *Click
command* and false per *user-facing invocation*. `sq <type> <n> <verb>` crosses that bridge
twice: once for the Typer group's id-resolving callback (`_resolve` in `_cli/_items.py`) and
again for the leaf verb, as two sequential `anyio.run` calls rather than one nested in the
other. A `with read_scope():` opened inside the first coroutine is therefore already closed
before the second begins, so the boundary §2 named cannot hold a scope across the invocation
the user actually issued.

The correct anchor is the one object Click builds exactly once per dispatch and tears down
exactly once at the end: the root `Context`. The first `command`-wrapped call in the tree opens
the scope and records the token on `root.meta`; `root.call_on_close` closes it after every
nested command has finished, success or error. This replaces §2's boundary. Everything §2
decided *about* the anchor is unchanged and still binding — opt-in, per invocation, and never
an `IndexStore` instance attribute or an `open_service` constructor flag, for the `sq ui`
reason §2 gives.

### A2 (2026-08-21) — "one invocation observes one index state" is kept as a guarantee, and is not yet met

The Consequences section states it and the implementation does not deliver it. Measured:

| form | index reads | whole-index parses (no workflow override) | with a workflow override |
|---|---|---|---|
| `sq list` | 1 | 1 | 3 |
| `sq show <id> --json` | 1 | 1 | — |
| `sq <type> <n> show --json` | 2 | 2 | 5 |

Two independent causes. The read count is 2 for the addressed-item form because that form
builds two `IndexStore` instances and the scope is keyed on store identity: `get_service()`
calls `open_service` unconditionally, so each of the two bridge crossings mints its own
`Service`. The parse count rises again with a workflow override, from the pre-service
cross-check in A4.

**The guarantee stands; it is the half of this decision that is about correctness rather than
speed, and withdrawing it to match a shortfall would be the wrong direction.** Two lock-free
reads in one invocation are two chances to observe different states — the callback resolves the
id from one snapshot, the verb renders from another. The N+1 is genuinely closed (12
sub-entities cost 2 reads, not 14), so what remains is a constant, not the original defect; but
a constant of 2 is not 1, and this decision claimed 1.

What closes it: memoize the `Service` for the invocation on the same Click root context the
scope already anchors to. The id-resolving callback builds a `Service`, keeps only the id, and
discards it; sharing that one instance takes the read count to 1 and, in the same stroke, makes
the cross-call scope sharing observable — until then the `ctx.meta`/`call_on_close` mechanism
is indistinguishable from a plain per-call scope, because the two crossings never share a
store, so no load-count assertion can tell the two implementations apart. Any test written for
this must assert the shared *store identity* across both crossings, not just the load count.

### A3 (2026-08-21) — §5's read-only-alias premise is false; this is the invariant that holds

§5 rests the safety of sharing one snapshot on two claims, and both are false at `sq sync`:

- `list_items` (`_services/_base.py:822`) returns the snapshot's own `Item` objects with no
  copy. Driven: under a scope, 9 of 9 roster items returned are identity-aliases into the
  snapshot, while `get()` correctly returns a copy.
- `_refresh_catalog_extra` (`_services/_maintenance.py:635-648`) mutates `item.extra[key]` in
  place *before* opening its transaction, then calls `db.add(item)` inside it — grafting a
  pre-transaction object into a db read fresh from disk. `_refresh_role_skills_extra`
  (`_services/_base.py:1319-1327`) mutates in place and writes frontmatter with no transaction
  at all. The `get()` deep copy does not cover either seam.

So the module docstring's "the only db that ever reaches `_atomic_write` is one read from disk
under this lock" is true of the db *container* and not of every item inside it.

**The safety is real, and it rests on this instead.** Two clauses, both structural:

1. `ensure_no_skew` runs inside that transaction, *before* `db.add`, and compares the whole
   round-tripped frontmatter key space minus `PERMITTED_EXTRA_SKEW` and minus any timestamp
   the file carries no value for. Any divergence on an index-authoritative key aborts the
   transaction before `db.add` is reached, so a stale alias can never be committed. Driven
   twice: a concurrent `set-default` is caught on `updated_at`, and a concurrent status change
   is caught directly on `status` with `updated_at` held equal by a frozen clock — the guard
   does not depend on the timestamp being a witness.
2. The excluded set is `frozenset({X.SKILLS, *RoleDef.extra_keys()})` (`_itemfile.py:70`) and
   the values the graft carries for those keys are `RoleDef.to_extra()`'s, written from the
   resolved definition moments earlier. The exclusion set and the reassert set are therefore
   the *same set*, by definition and not by coincidence: for every excluded key except one,
   the grafted value is authoritative rather than stale. Driven: with a concurrent writer
   flipping `is_default` under a frozen clock so the guard passes, the committed value is the
   catalog's, not the snapshot's.

The one key in the excluded set that clause 2 does not cover is `extra.skills`, which
`to_extra()` does not carry. The index is by design never current on it and
`_refresh_role_skills_extra` rewrites disk on the same pass, so a stale index value there is
the documented permanent disk-ahead skew, not a loss.

**None of this was introduced by the read scope.** `list_items` and the `db.add` graft are
byte-identical at `ea891a6`, before any of this work; the aliases were already
pre-transaction objects, materialised into a list by one `list_items` call before the loop, so
the stale window per item was already "that one load until this item's transaction". The scope
moves that load earlier by the operations between an invocation's first read and `list_items` —
in `sq sync` the two are adjacent. Driven: the whole sequence behaves identically with and
without a scope bound.

**What should change anyway.** The argument above is correct but spread across three files, and
a reader of `_refresh_catalog_extra` cannot see it. Hand that function an explicit copy — or
copy at the roster-regen `list_items` call — so the graft is local-by-construction rather than
safe-by-trace. The cost argument in §5 (13.7 ms to copy the whole db against 26.4 ms to load
it) argues against copying every read; it says nothing against copying one caller's list, and a
role item measures about 0.01 ms.

**The general rule §5 should have stated, and which now governs:** a read result may be mutated
in place only by a caller that also owns the write seam for it, and must never be grafted into
a transaction db it did not come from. Where a caller does both, it copies first.

### A4 (2026-08-21) — the pre-service index cross-check is reduced by count, not moved into the scope

The Consequences section rules `_workflow/_loader.py`'s cross-check out of the scope because it
runs before any store exists. That scoping call for the *cache* stands. What the section did not
say is what it costs: `validate_against_index_fail_closed` performs its own synchronous
whole-index `model_validate_json` once per `open_service`, and only when
`.overrides/workflow.toml` is present. Measured, same squad, the only difference being a
two-line workflow override: `sq list` 1 parse to 3, `sq <type> <n> show --json` 2 to 5. At this
decision's own 26.4 ms per parse on a 720-item index that is roughly 130 ms where the headline
number is ~26 ms, and it falls entirely on adopters who customise — first-class scope for this
tool, so "the bundled path is fast" is not an answer.

**The ruling: do not put it in the read scope.** The scope is keyed on `IndexStore` identity and
holds `SquadsDB` snapshots a store filed; admitting a storeless caller with a differently
shaped value turns it into a general-purpose per-invocation cache, which is a larger commitment
than this decision made. It is also a fail-closed validation gate, and memoizing a validation
is a stronger claim than memoizing a read — the memo asserts the corpus has not changed since
the check passed.

Reduce the count instead: run the cross-check **once per invocation** rather than once per
`open_service`, on the same Click-root anchor A2 already needs, or hoist it to the root callback
where the spec is bound. That is the same shape as A2's `Service` memo and should follow it, so
the second memo hangs off the first rather than inventing a second anchor. Both are engineering
work on a surface this decision scoped out, and belong to their own item.
<!-- sq:body:end -->

## Discussion

<!-- sq:discussion -->
- [2026-08-21T12:53:46Z] Catherine Manager:
  - Verified the two load-bearing claims before accepting: _cli/_common.py:966 is the only anyio.run in the tree, and sq ui is a sync command holding one Service for the session (_cli/_ui.py), so it never crosses the bridge and keeps current behaviour. The invariant-8 argument for transaction() bypassing the scope is sound: the transaction db is the object _atomic_write commits.
- [2026-08-21T17:20:56Z] Robert Architect:
  - Amended in place (A1-A4 in the body) after the implementation on 9bd3560; the original text is unedited apart from one inline pointer in section 5, since it records what was decided.
  - A1: the scope anchor is the Click root context, not the anyio.run boundary — section 2 premise was true per Click command, false per user-facing invocation (sq <type> <n> <verb> crosses the bridge twice). A2: "one invocation, one index state" is KEPT as a guarantee and is not yet met (2 index reads for the addressed-item form, 3-5 whole-index parses with a workflow override); memoizing the Service on the same Click-root anchor closes it and makes the cross-call sharing observable.
  - A3: section 5 was factually wrong — list_items returns snapshot aliases (driven: 9/9 identity-aliases) and _refresh_catalog_extra grafts a pre-transaction object via db.add. The implementation is nonetheless safe, for a different reason: ensure_no_skew gates the graft on the whole non-excluded key space (driven both via updated_at and directly on status with the clock frozen equal), and the excluded set IS RoleDef.extra_keys() plus skills, which is the same set the graft has just reasserted from the resolved definition. Not introduced here — byte-identical at ea891a6, and the sequence behaves identically with no scope bound.
  - A4: the pre-service cross-check stays out of the read scope (storeless caller, differently shaped value, and it is a fail-closed validation not a read) — reduce it to once per invocation on the same anchor instead. A2 and A4 are engineering work on a surface this decision scoped out; they need their own item.
<!-- sq:discussion:end -->
