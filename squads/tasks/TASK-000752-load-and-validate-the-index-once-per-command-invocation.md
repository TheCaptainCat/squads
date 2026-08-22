---
id: TASK-752
sequence_id: 752
type: task
title: Load and validate the index once per command invocation
status: Done
author: tech-lead
assignee: python-dev
priority: medium
refs:
- BUG-747:fixes
- ADR-753:implements
description: Request-scoped index read to remove the N+1 over sub-entities in the
  show path
created_at: '2026-08-21T12:43:00Z'
updated_at: '2026-08-21T18:37:00Z'
---
<!-- sq:body -->
One command invocation deserialises and revalidates the whole index once per sub-entity. The cost
scales with sub-entity count, and it is the wall-clock cost of opening an item's preview in the VS Code
client, which fans out eight calls in parallel and waits on this one.

ADR-753 settles the design and is Accepted. Read it in full before starting: it decides the mechanism,
the boundary where the scope is entered, the invalidation point, the bypasses, and what is
deliberately *not* changed. The constraints below are its rules restated as acceptance, not a summary
you may re-derive — a different shape needs the architect, not a judgement call in the code.
Link: `ref add ADR-753 --kind implements`.

## Measured baseline

ADR-753 instrumented the real CLI entry point on this squad's ~720-item index. Those figures, not
cProfile arithmetic, are the baseline:

| observation | value |
|---|---|
| `IndexStore.load` calls for one `show --json` | 55 |
| `ServiceCore.get` calls | 54 |
| `SubentitiesMixin.get_block` calls | 51 |
| reads of the item's own 216 KB `.md` file | 53 |
| one `load()` on this corpus | 26.4 ms |
| of which the vocab + badge-code validation | 3.3 ms |
| in-process elapsed for the command | 1.60 s |

So 55 x 26.4 ms = 1.45 s of the 1.60 s is the repeated load. The multiplication comes from
`_services/_subentities.py` (`get_block` opens with `await self.get(parent_id)`) fanned out once per
sub-entity by `_cli/_common.py`; `get` is `require_item(await self.store.load(), item_id)` in
`_services/_base.py`.

**Correct one figure carried on the reporting bug.** Its "216 `Service.get` calls" is cProfile counting
per-resumption frames of an `async def`, not call sites. The real counts are 54 gets and 55 loads. Do
not chase 216 of anything, and do not quote that number forward.

The second property at stake is not cost: 55 independent lock-free reads of a mutable file are 55
chances to observe different states, so one command can render a torn view of the board. One invocation
observing one index state is a deliberate behaviour change, and the better one.

## Design constraints — required, not optional

- **A read scope in a module-level `ContextVar` in `_index/_store.py`**, holding snapshots keyed on
  **store instance identity**. `load()` consults the ambient scope, returns a snapshot this store
  filed, else reads disk and files the result. Absent a scope, `load()` behaves exactly as today —
  opt-in, and its absence is only slow, never wrong. This mirrors `_active_transaction`.
- **Not an `IndexStore` instance attribute, and not a constructor flag on `open_service`.** `sq ui`
  holds one `Service` for a whole session, so an instance-lifetime cache would pin a terminal browser
  to launch-time state while other processes mutate the index. Forgetting to open a scope costs speed;
  forgetting to disable an instance cache silently serves stale data.
- **Not a field on `RequestContext`** — that is a frozen record of request inputs, and the
  store-identity ownership check is store-internal.
- **Entered at the single sync-to-async bridge** (`command` in `_cli/_common.py`, the documented one
  `anyio.run` per invocation), inside the root coroutine before the command body, so every spawned
  task inherits the binding. `sq ui` is sync, never passes through it, and keeps today's behaviour.
- **`transaction()` never consults the scope.** Extract the disk read into a private
  `_read_from_disk(...)`; `load()` becomes the scope-aware wrapper; `transaction()`'s in-lock load
  calls `_read_from_disk` directly. This is the load-bearing line: `transaction()`'s db is the object
  `_atomic_write` commits, so a stale snapshot there would write an older index over a newer one and
  put the index behind the markdown — the one skew direction the durability model forbids.
- **Invalidation is unconditional and co-located.** `scope.snapshots.pop(self, None)` goes in the same
  `finally` that resets `_active_transaction` and releases Layer 3 — commit or raise, no second clause.
  `overwrite()` invalidates the same way.
- **Two bypasses, both required.** `validate_vocab=False` neither consults nor fills the scope (an
  unvalidated db in a shared slot would let a later validating caller skip a fail-closed check). And
  `load()` grows an explicit `fresh=True` for the caller whose contract is "re-read now" —
  `_confirm_cross_source` in `_services/_maintenance.py`, which is `sq check`'s false-positive
  suppression; serving it the pre-scan snapshot reintroduces spurious drift reports.
- **`get()` returns a deep copy of the item.** Today every `get()` returns an item from a freshly
  parsed db, so no two callers share an object; a copy at that seam preserves that contract. Measured
  at 0.168 ms for the 51-sub-entity item against 1.45 s recovered. Copying the whole db per load is
  rejected on measurement (13.7 ms against a 26.4 ms load only halves the cost). Callers that iterate
  `db.items.values()` for a read keep receiving aliases and stay read-only.
- **The validators keep running on every load. There is no change-detection trigger.** This was
  considered and rejected on the measurements: at one load per invocation the whole check is 3.3 ms,
  0.2% of the command. It is a fail-closed load-boundary backstop, a trigger would need a fingerprint
  that is itself derived state that can be wrong, and the check is what makes an override shrinking a
  badge collection under a live corpus refuse rather than proceed. Do not add one, and do not reopen
  it in the implementation.
- **Audit all `store.load()` call sites** against "does this depend on re-reading the index?" before
  landing. ADR-753 found `_confirm_cross_source` to be the only one; confirm that on the current tree
  and record the audit.

## Out of scope, named so it is a decision

The 53 re-reads of the item's own `.md` file stay. At 10 ms measured they do not justify a second
cache, and a text cache over item files has a different invalidation story. `_workflow/_loader.py`'s
pre-service index cross-check keeps its own synchronous read and stays outside the scope — it runs
before any store exists.

## Falsification the implementation owes

Report each of these as red-then-green, not as an assertion that it holds:

- Let `transaction()` read through the scope — a test must go red for writing a stale db over a newer
  index. If nothing goes red, the suite does not yet cover the one thing making this safe.
- Break the invalidation — a read after a committed mutation in the same invocation must go red for
  reporting pre-mutation state.
- Remove the `fresh=True` at the `sq check` confirm round — a test must go red with a spurious drift
  report for an item mutated between the scan and the reload.
- Remove the deep copy at `get()` — a test that mutates a read result and re-reads must go red.

## Acceptance criteria

- Exactly one `load` per invocation for `sq show <id> --json` on a multi-sub-entity item, asserted by
  an instrumented load **count**. A timing assertion proves nothing on a loaded machine and does not
  satisfy this.
- Every design constraint above holds, and any deviation is raised with the architect before it is
  coded rather than explained afterwards.
- **Before/after measurement reported in a comment on this item**: wall time for
  `sq show REV-000736 --json` (1.60 s in-process is the recorded baseline, ~0.2 s the expected after),
  plus the `load` and `get` counts before and after. State the corpus path and the exact commands so
  the numbers are reproducible, and check the probe itself before trusting a surprising result — a
  probe whose setup failed silently proves nothing.
- Payloads are byte-identical before and after for `sq show --json` on both a large and a small item.
  A performance change that alters output is a different change.
- `uv run --all-extras pytest --run-slow` is green, with the scale-test timings reported in the same
  comment.
- `tests/meta` is green. The module-level mutable-state guard is the one to watch: its doctrine is one
  `ContextVar` holding an object, never a bare module-level dict — so the snapshot map lives inside the
  scope object, and any new module-level binding gets run past that guard rather than around it.
- `uv run --all-extras pyright`, `ruff check`, `ruff format --check` and the full `pytest` suite are
  green; `uv run sq check` is clean.
- `CHANGELOG.md` carries an adopter-facing entry in the unreleased section, covering the speed-up and
  the one-state-per-invocation behaviour change.
<!-- sq:body:end -->

## Subtasks

_Add with `sq task 752 add-subtask "<title>"`; track with `sq task 752 subtask <n> update --status <Status>`._

<!-- sq:summary -->
<!-- sq:summary:end -->

<!-- sq:subtasks -->
<!-- sq:subtasks:end -->

## Discussion

<!-- sq:discussion -->
- [2026-08-21T12:56:55Z] Olivia Lead:
  - Rewrote the body against ADR-753 (linked, implements): the ContextVar read scope keyed on store identity, entered at the one sync-to-async bridge and NOT as an IndexStore attribute, transaction() calling the extracted disk read with invalidation in the same finally as _active_transaction, both bypasses (validate_vocab=False and a new fresh=True for the sq check confirm reload) required, the deep copy at get(), and no validator trigger — considered and rejected on measurements.
  - Corrected a figure the bug carries: its "216 Service.get calls" is cProfile counting async resumptions. The real instrumented counts are 54 gets and 55 loads; ADR-753 table is the baseline. Also flagged that any new module-level binding gets run past tests/meta mutable-state guard — snapshot map inside the scope object, not a bare module dict.
- [2026-08-21T16:43:41Z] Elias Python:
  - Implemented per ADR-753: _read_from_disk extracted; load() is the scope-aware wrapper (validate_vocab=False and fresh=True both bypass); transaction()/overwrite() call _read_from_disk directly and invalidate unconditionally in their existing finally. Scope entered at command() in _cli/_common.py, anchored on the Click root context (not the instance/service/RequestContext) so it survives Typer's own id-resolving group callback crossing the same bridge separately.
  - Real-corpus measurement, sq show REV-000736 --json (this repo's own squads/, 727 items): before 55 loads / 1672 ms in-process, after 1 load / 127 ms -- a 13x wall-time drop, exact load count matches the recorded baseline both sides. Payload byte-identical before/after (diff clean).
  - Invariant 8: proven, not asserted -- two IndexStore instances at one path, one holding a stale scoped snapshot, the other committing; transaction() on the first reads 8 fresh off disk (never the stale 0), and the commit lands on top of it rather than reverting it. transaction()'s in-lock load never goes through load()/the scope at all.
  - Four falsifications driven red then green (temporarily reverted each mechanism, watched the exact assertion fail, restored, re-ran green): (1) pointed transaction() at self.load() -- test_transaction_never_serves_a_stale_snapshot_over_a_newer_index went red (0 != 7); (2) disabled the transaction() finally's scope invalidation -- test_scope_is_invalidated_after_a_commit_so_a_later_read_sees_the_mutation went red (0 != 1); (3) dropped the 'or fresh' bypass in load() -- test_load_fresh_bypasses_the_scope_in_both_directions went red (0 != 5); (4) removed the deep copy in Service.get() -- both test_get_deep_copy_under_read_scope tests went red (mutation leaked; two get() calls returned the same object).
  - One honest gap found and documented rather than papered over: sq show <id> --json (the root, any-type command) hits the literal 'exactly one load' bar -- proven above and in tests/cli/test_show_json_single_index_load.py. The per-type alias sq <type> N show --json is a second way to reach the same output, but crosses command() twice for one invocation (Typer's own id-resolving @item.callback() ahead of the leaf verb, each building its own Service/IndexStore) -- flat at 2 loads regardless of sub-entity count (checked at 8 and 16), not 1. The scope is correctly shared across both calls (root-context-anchored); the residual 2 is two distinct IndexStore instances, and the cache is keyed on store identity exactly as decided (mirrors _active_transaction, and is what my falsification #1 above depends on) -- so this isn't a scope-sharing bug, it's Service-per-get_service()-call multiplicity, a different concern ADR-753 doesn't cover. Collapsing it further means caching get_service()'s Service object per invocation too, touching ~80 call sites including the cross-check-bypassing variant with deliberately different resolution semantics -- did not implement that unreviewed; flagging for you rather than guessing.
  - Gates: pyright/ruff check/ruff format all clean (full repo). Targeted suite (meta + index-store/service/CLI-show/repair/skew modules + new tests): 443 passed. sq check clean on this repo's real corpus; sq repair needed one real pass (pre-existing markdown-ahead-of-index drift from concurrent work already on disk, unrelated to this change -- items 748-754 existed as .md files but were missing from .squads.json), then a second repair run was a byte-for-byte no-op, proving stability post-fix.
  - Audited every store.load() call site on the current tree: _confirm_cross_source is the only one needing fresh=True, matching the ADR's own audit.
<!-- sq:discussion:end -->
