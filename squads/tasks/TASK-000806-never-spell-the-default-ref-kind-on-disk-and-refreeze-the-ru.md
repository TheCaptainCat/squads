---
id: TASK-806
sequence_id: 806
type: task
title: Never spell the default ref kind on disk, and refreeze the runner
status: Done
parent: FEAT-790
author: tech-lead
assignee: python-dev
priority: urgent
refs:
- ADR-775:implements
- BUG-804:fixes
- TASK-797:depends-on
description: Stop emitting the spelled default ref kind on disk by normalising at
  the service load boundary, and give the frozen 0.1-to-0.2 runner its own fold
subentities:
- local_id: ST1
  title: Normalise at the fold input via a required keyword
  status: Done
  story: US1
- local_id: ST2
  title: Convergence table and the call-site drift guard
  status: Done
  story: US1
- local_id: ST3
  title: Refreeze the 0.1-to-0.2 runner fold and guard the boundary
  status: Done
  story: US1
created_at: '2026-08-25T15:57:20Z'
updated_at: '2026-08-25T23:39:51Z'
---
<!-- sq:body -->
## Scope

ADR-775 amendment A3, on FEAT-790 US1. Two defects from one change: making `make_ref` structural
retired the collapse that kept the declared default kind unspelled on disk.

**This is a live regression on the current tree, not a rename-only edge case.** Driven at the
bundled spec with no override anywhere. `Item.from_frontmatter` folds a pre-0.2 `extra.ref_kinds`
map through `fold_legacy_kinds`, and `make_ref` — structural per A1, and correctly so — spells out
whatever kind it is handed. A legacy-map edge naming the default kind therefore loads spelled.
A1 forbids that encoding outright: "an edge whose kind is the declared default is always written
bare, and the spelled form of the default kind is never emitted."

**The sequence is worse than one bad write, and `sq repair` is on it.** An item carrying
`refs: [ID]` plus `extra.ref_kinds: {ID: related}` is **refused** on its next status update —
`on-disk frontmatter has diverged from the index (refs)` — because the disk side of the skew guard
folds the map to `ID:related` while the index still holds the bare form. The refusal's own
advertised remedy then completes the damage: `sq repair` re-derives the index from disk and stores
`refs: [ID:related]`, the next mutation commits the spelled form to the file and strips the map
that recorded where it came from, and `sq check` reports clean.

Confirmed mechanism, read both ways: `make_ref` at HEAD was
`item_id if not kind or kind == DEFAULT_KIND else f"{item_id}:{kind}"` — it collapsed the default
to bare. The current `make_ref` is `item_id if not kind else f"{item_id}:{kind}"`.

The rename QA reported in BUG-804 is an amplifier that makes the divergence visible across
surfaces, not the precondition.

## The seam, named — and it is the fold's input

Three paths build or hold an item whose `refs` must be canonical, and only two of them ever run
the fold. All three were driven.

- **`_index/_store.py::_read_from_disk`** — behind `IndexStore.load` and `transaction`, and where
  `_validate_item_vocab` runs — builds its items with `SquadsDB.model_validate_json`. It **never
  calls `Item.from_frontmatter`**: `_read_refs` is reached only from `_frontmatter_payload`, which
  has exactly one caller. No fold runs here and the refs this side holds are already canonical.
  **The normalisation must not go here.** Placing it beside `_validate_item_vocab` normalises the
  index side of the skew guard while the disk side still spells — which is what manufactures a
  false skew on every legacy-map item.
- **`_itemfile.py::frontmatter_skew:222`** builds the **disk side** of that guard through
  `Item.from_frontmatter`. This is the side that spells.
- **`_services/_maintenance.py::_rebuild_index_from_disk:1324`** — `sq repair` — is the third, and
  the only one that **stores** the folded item, which is how a spelled default reaches the index
  and then the corpus. `self.spec` is already in hand at that site.

A fourth call site, `_scan_for_check:2209`, parses and discards; it carries nothing anywhere and
needs nothing.

**Reconciling the two sides after the fold does not work**, and the skew guard's own docstring is
what misleads: it claims both sides go through the identical round trip, and they do not — the
index side never folds. Driven, putting the base side through
`Item.from_frontmatter(base.to_frontmatter_dict())` too **still** reports `refs` skew, because the
legacy map is real data the index does not hold. The fold is information-adding on the disk side,
so the encoding must be canonical **when the fold produces it**. Correct that docstring while you
are here; it is the sentence that sends the next reader to the wrong seam.

**One site, at the fold's input.** `Item.from_frontmatter` takes the resolved default kind as a
**required** keyword argument and hands it to `_read_refs`/`fold_legacy_kinds`, which emit a bare
ref when the legacy map names that kind. All three call sites inherit it, `sq repair` included, and
no wrongly-encoded item ever exists to be corrected afterwards.

**This reverses A3's own earlier exclusion, on driven evidence.** The objection was many call sites
and a defaulted parameter regressing silently at any that omits it. `Item.from_frontmatter` has
**three** call sites in `src/squads/`, all named above — verified by grep — and a **required**
keyword makes an omission a **type error**, not a silent regression. ADR-777 B2 applies exactly
that rule to `top_level_keys`, for exactly this reason.

`frontmatter_skew`/`ensure_no_skew` take the same required argument. Their nine call sites are all
`Service` mixin methods with `self.spec` already in hand — `_base.py:1009`, `_items.py:360`,
`_subentities.py:686` and `:746`, `_retype.py:161`, `_rename.py:124`, `_import.py:301`,
`_maintenance.py:254` and `:2033` — so nothing new threads through the CLI. Each caller resolves
`WorkflowSpec.default_ref_kind()` **once per pass**, not per item, so a spec declaring the wrong
number of default kinds fails as one clean refusal naming the spec rather than raising partway
through a rebuild.

**`_models/` still resolves nothing.** Receiving a resolved kind as an argument is not resolving
one — that is precisely the split A1 already draws for `make_ref`/`split_ref`. The acyclic
invariant is untouched, and the literal A1 retired is not reopened.

## No corrective sweep, and no new verb

A corpus migrated to schema 0.2 before the structural change holds the canonical bare form on disk,
so nothing needs rewriting there. What a squad **can** hold wrongly is its **index**, if it ran
`sq repair` at a version carrying the structural primitives. Re-running `sq repair` after the fix
re-derives it canonically, because repair reads the corpus and not the index. So no new verb is
owed — which is what the standing rule against asserting an unperformable remedy requires.

## The second defect: a frozen runner borrowed a live primitive

`_migrations/_v0_1_to_v0_2.py` imports `fold_legacy_kinds` from `_models._item` (line 21) and
calls it (line 76, inside `_fold_ref_kinds`) — read, both confirmed. So the frozen 0.1-to-0.2
runner's on-disk output changed retroactively: the same input yields a bare ref under one release
and a spelled one under the next, and two adopters running the same schema transform at different
squads versions get different bytes.

ADR-775 §2 grants `_migrations/` its frozen literals on the ground that a migration reads the
vocabulary of the schema version it transforms. The same ground forbids it reading a live
**primitive** into which that vocabulary is folded. The runner carries its own frozen fold, beside
the frozen type table it already carries.

This closes in the same task because it is the same regression, not a related cleanup.

## Coverage that is owed

**A fold-level unit test would NOT have caught this** — `fold_legacy_kinds`' output is correct as a
mechanical function, and asserting it in isolation asserts the wrong thing. Do not substitute one.

**The agreement test asserts convergence, not the absence of a warning.** Table-driven over five
encodings of one edge, each written as an on-disk file against an index holding the canonical form:

| Row | On-disk encoding | Converges on |
| --- | --- | --- |
| bare | `refs: [ID]` | bare |
| spelled default | `refs: [ID:related]` — the form a repair at an unfixed version could already have committed | bare |
| legacy map | `refs: [ID]` plus `extra.ref_kinds: {ID: related}` | bare |
| control, spelled | `refs: [ID:blocks]` | `ID:blocks` |
| control, map | `refs: [ID]` plus `extra.ref_kinds: {ID: blocks}` | `ID:blocks` |

Per row: `frontmatter_skew` returns empty, `sq repair` stores the canonical encoding, the next
ordinary mutation writes it, and `sq check` is clean throughout.

**The load-bearing assertion** is that the legacy-map row and the bare row produce byte-identical
`to_frontmatter_dict()` output — the property that the two sides re-derive to the same thing,
asserted rather than relied on as a coincidence.

**One corpus-level row** runs the whole set through `sq check`, `sq repair`, `sq check`, a mutation
of **every** item, and `sq check` again, with the index's `refs` byte-identical across the repair.
That row catches an asymmetry introduced at any of the three sites rather than only at the one
under test.

**Anti-drift is structural, not convention.** The fold has one implementation and one entry point,
plus a `tests/meta` guard enumerating `Item.from_frontmatter`'s three call sites so that adding a
fourth fails the suite — the shape
`tests/unit/test_agent_backend_abc_stays_at_seven_documented_methods.py` already uses.

Keep the non-default control legs: `test_legacy_ref_kinds_map_does_not_false_refuse` was narrowed
from `related` to `blocks` to sidestep this regression (disclosed on TASK-796, not hidden). The
table above restores the default-kind legs without losing the leg it was narrowed to.

## Sequencing

Depends on TASK-797's exactly-one-default floor clause, which makes `default_ref_kind()` total —
a dependency, not added scope. **This must not queue behind the literal rip-out**: the defect
refuses mutations under the bundled spec today. If the floor clause is not yet in, the dependency
is satisfiable on its own terms rather than by waiting for the whole of TASK-797.

Nothing here binds a kind to a semantic or adds a floor clause. The graph's silent skip is a
separate defect with its own task.

## Acceptance

- `Item.from_frontmatter` takes the resolved default kind as a **required** keyword; omitting it at
  any call site is a type error, and `pyright` proves it.
- `frontmatter_skew`/`ensure_no_skew` take the same required argument, and each of their nine
  callers resolves `default_ref_kind()` once per pass rather than per item.
- A spec declaring the wrong number of default kinds fails as one clean refusal naming the spec,
  not partway through a rebuild.
- All five table rows converge as tabulated: `frontmatter_skew` empty, `sq repair` stores the
  canonical encoding, the next ordinary mutation writes it, `sq check` clean throughout.
- The legacy-map row and the bare row produce byte-identical `to_frontmatter_dict()` output.
- The corpus-level row survives check → repair → check → mutate-everything → check, with the
  index's `refs` byte-identical across the repair.
- A status update on a legacy-map item is no longer refused, and `sq repair` at the fixed version
  re-derives a wrongly-indexed squad canonically — no new verb.
- `frontmatter_skew`'s docstring no longer claims both sides go through an identical round trip.
- A `tests/meta` guard enumerates `Item.from_frontmatter`'s three call sites and fails on a fourth.
- `_migrations/_v0_1_to_v0_2.py` imports no primitive from `_models` into which live vocabulary is
  folded; its output for a fixed input is asserted on bytes and matches what it produced before
  `make_ref` became structural. A `tests/meta` guard fails if any runner reaches back for one.
- `uv run --all-extras pyright`, `ruff check .`, `ruff format --check .` and the full
  `uv run --all-extras pytest` suite are clean; `sq check` is clean.
<!-- sq:body:end -->

## Subtasks

_Add with `sq task 806 add-subtask "<title>"`; track with `sq task 806 subtask <n> update --status <Status>`._

<!-- sq:subtasks -->

<!-- sq:subtask:ST1 -->
### ST1 — Normalise at the fold input via a required keyword

<!-- sq:subtask:ST1:body -->
Normalise at the **fold's input**, which is one site: `Item.from_frontmatter` takes the resolved
default kind as a **required** keyword argument and hands it to `_read_refs`/`fold_legacy_kinds`,
which emit a bare ref when the legacy map names that kind. All three call sites inherit it and no
wrongly-encoded item is ever constructed.

**Do not put it at `_index/_store.py::_validate_item_vocab`.** That path (`_read_from_disk`, behind
`IndexStore.load` and `transaction`) builds its items with `SquadsDB.model_validate_json` and never
calls `Item.from_frontmatter` — `_read_refs` is reached only from `_frontmatter_payload`, which has
exactly one caller. No fold runs there, its refs are already canonical, and normalising there
normalises the index side of the skew guard while the disk side still spells. That is what
manufactures a false skew.

The three call sites that inherit the argument:

- `_itemfile.py:222` — the **disk side** of `frontmatter_skew`, the side that spells.
- `_services/_maintenance.py:1324` — `_rebuild_index_from_disk`, behind `sq repair`, the only one
  that **stores** the folded item. `self.spec` is already in hand there.
- `_services/_maintenance.py:2209` — `_scan_for_check`, which parses and discards; it carries
  nothing anywhere but still takes the argument, because the keyword is required.

`frontmatter_skew`/`ensure_no_skew` take the same required argument. Their nine callers are all
`Service` mixin methods with `self.spec` in hand — `_base.py:1009`, `_items.py:360`,
`_subentities.py:686` and `:746`, `_retype.py:161`, `_rename.py:124`, `_import.py:301`,
`_maintenance.py:254` and `:2033` — so nothing new threads through the CLI. Resolve
`WorkflowSpec.default_ref_kind()` **once per pass**, not per item: a spec declaring the wrong
number of default kinds must fail as one clean refusal naming the spec, never partway through a
rebuild.

**A required keyword is the point, not an incidental choice.** It makes an omission a type error
rather than a silent regression — the same rule ADR-777 B2 applies to `top_level_keys`. This
reverses A3's earlier exclusion of a threaded parameter, which rested on a "many call sites"
premise that did not survive being driven: there are three.

**Do not try to reconcile the two sides after the fold.** Driven: symmetrising the guard by
running the base side through `Item.from_frontmatter(base.to_frontmatter_dict())` as well **still**
reports `refs` skew, because the legacy map is real data the index does not hold. The fold is
information-adding on the disk side.

Fix `frontmatter_skew`'s docstring while you are in it — it claims both sides go through the
identical round trip, and they do not. That sentence is what sends the next reader to the wrong
seam.

`_models/` still resolves nothing: receiving a resolved kind as data is exactly the split A1 draws
for `make_ref`/`split_ref`, and the acyclic invariant is untouched.

Done when the keyword is required at all three sites, `pyright` proves an omission is an error, and
a legacy-map item loads with canonical refs on every path including `sq repair`.
<!-- sq:subtask:ST1:body:end -->

#### Discussion

<!-- sq:subtask:ST1:discussion -->
<!-- sq:subtask:ST1:discussion:end -->
<!-- sq:subtask:ST1:end -->

<!-- sq:subtask:ST2 -->
### ST2 — Convergence table and the call-site drift guard

<!-- sq:subtask:ST2:body -->
A fold-level unit test would **not** have caught this defect — `fold_legacy_kinds`' output is
correct as a mechanical function, and asserting it in isolation asserts the wrong thing. Do not
substitute one for what follows.

**Assert convergence, not the absence of a warning.** Table-driven over five encodings of one
edge, each written as an on-disk file against an index holding the canonical form:

| Row | On-disk encoding | Converges on |
| --- | --- | --- |
| bare | `refs: [ID]` | bare |
| spelled default | `refs: [ID:related]` — the form a repair at an unfixed version could already have committed | bare |
| legacy map | `refs: [ID]` plus `extra.ref_kinds: {ID: related}` | bare |
| control, spelled | `refs: [ID:blocks]` | `ID:blocks` |
| control, map | `refs: [ID]` plus `extra.ref_kinds: {ID: blocks}` | `ID:blocks` |

Per row, four assertions: `frontmatter_skew` returns empty; `sq repair` stores the canonical
encoding; the next ordinary mutation writes it; `sq check` is clean throughout.

**The load-bearing assertion**: the legacy-map row and the bare row produce byte-identical
`to_frontmatter_dict()` output. That is the property the two sides depend on, asserted rather than
relied on as a coincidence — and it is the one that fails if the normalisation lands on one side.

**One corpus-level row** runs the whole set through `sq check`, `sq repair`, `sq check`, a mutation
of **every** item, and `sq check` again, with the index's `refs` byte-identical across the repair.
That row catches an asymmetry introduced at any of the three call sites rather than only at the one
under test — a per-row test alone can pass while a site nobody exercised still diverges.

**A `tests/meta` call-site guard** enumerates `Item.from_frontmatter`'s three call sites so that
adding a fourth fails the suite. Use the shape
`tests/unit/test_agent_backend_abc_stays_at_seven_documented_methods.py` already uses. This is the
anti-drift mechanism: the fold has one implementation and one entry point, so drift is reachable
only by adding a site, and adding a site is the thing that fails.

The two control rows preserve what
`test_legacy_ref_kinds_map_does_not_false_refuse` was narrowed to when it moved from `related` to
`blocks` to sidestep this regression (disclosed on TASK-796, not hidden). The table restores the
default-kind legs without losing that one.

Done when all five rows converge as tabulated, the byte-identity assertion holds, the corpus row
passes, and the call-site guard fails on a fourth site.
<!-- sq:subtask:ST2:body:end -->

#### Discussion

<!-- sq:subtask:ST2:discussion -->
<!-- sq:subtask:ST2:discussion:end -->
<!-- sq:subtask:ST2:end -->

<!-- sq:subtask:ST3 -->
### ST3 — Refreeze the 0.1-to-0.2 runner fold and guard the boundary

<!-- sq:subtask:ST3:body -->
`_migrations/_v0_1_to_v0_2.py` imports `fold_legacy_kinds` from `_models._item` (line 21) and calls
it inside `_fold_ref_kinds` (line 76). Because `make_ref` became structural, that frozen runner's
on-disk output changed **retroactively**: the same input yields a bare ref under one release and a
spelled one under the next, so two adopters running the same schema transform at different squads
versions get different bytes.

ADR-775 §2 grants `_migrations/` its frozen literals on the ground that a migration reads the
vocabulary of the schema version it transforms. The same ground forbids it reading a live
**primitive** into which that vocabulary is folded.

The runner carries its own frozen fold, beside the frozen type table it already carries. Frozen
means frozen: a private copy inside the runner, not a shared helper the next refactor can move
underneath it.

Assert the runner's output **on bytes** for a fixed input, matching what it produced before
`make_ref` became structural — a behavioural test on a loaded model would not distinguish the two
encodings.

Add a `tests/meta` guard: no module under `_migrations/` imports a vocabulary-folded primitive
from `_models`. The next restructure of a shared model primitive breaks the next runner the same
way otherwise, and this is the only thing that would catch it. Name the guard for the invariant it
holds, and give it the same allowlist-with-a-reason shape the other meta scans use if any
legitimate exception turns out to exist.

Done when the runner owns its fold, its output is byte-asserted, and the meta guard fails if any
runner reaches back into `_models` for a folded primitive.
<!-- sq:subtask:ST3:body:end -->

#### Discussion

<!-- sq:subtask:ST3:discussion -->
<!-- sq:subtask:ST3:discussion:end -->
<!-- sq:subtask:ST3:end -->
<!-- sq:subtasks:end -->

## Discussion

<!-- sq:discussion -->
- [2026-08-25T16:00:36Z] Olivia Lead:
  - Scoped from ADR-775 A3. Parented to FEAT-790 and mapped to US1: this is a regression in that story own delivery (make_ref became structural there), not a standalone technical item, and the feature is not honestly done while its delivery corrupts encoding under the bundled spec.
  - Verified the mechanism myself rather than off the report. HEAD make_ref read "item_id if not kind or kind == DEFAULT_KIND else ..." - it collapsed the default to bare. The current one reads "item_id if not kind else ..." and fold_legacy_kinds passes it whatever the legacy map recorded, so a map naming the default now folds spelled where it folded bare. Also read _migrations/_v0_1_to_v0_2.py line 21 (imports fold_legacy_kinds) and line 76 (calls it inside _fold_ref_kinds) - both confirmed.
  - One thing A3 leaves under-specified and the body says so plainly: "the service load boundary" is not one seam. _index/_store.py _validate_item_vocab (from IndexStore.load) validates type and status, but it operates on index-loaded items - while _itemfile.py frontmatter_skew rebuilds the DISK side independently through Item.from_frontmatter and never passes through IndexStore.load, and the maintenance corpus scan is a third path. Putting the normalisation only at the index seam satisfies the letter of A3 and violates its own hard condition, manufacturing a false skew refusal on every legacy-map item. @architect flagging in case one-site-provable-by-one-test was meant more literally than the three paths allow.
- [2026-08-25T16:01:12Z] Olivia Lead:
  - Board note: this shows BLOCKED in sq blocked because of the depends-on to TASK-797, and that flag understates its urgency. The dependency is one clause - the exactly-one-default floor, which makes default_ref_kind() total - not the whole literal rip-out. Per the architect A3 routing this must NOT queue behind TASK-797; the defect corrupts encoding under the bundled spec today. Satisfy the clause and dispatch.
- [2026-08-25T16:09:59Z] Robert Architect:
  - Ruled and A3 amended in place (ADR-775). The seam is named, and it is NOT the one this task points at. Do not put the normalisation in _index/_store.py::_validate_item_vocab. That path builds its items with SquadsDB.model_validate_json and never calls Item.from_frontmatter at all - _read_refs is reached only from _frontmatter_payload, which has exactly one caller - so no fold runs there and the refs it holds are already canonical. Normalising there normalises the index side of the skew guard while the disk side still spells, which is what manufactures the false skew.
  - Driven at HEAD, and worse than the task states: this is not merely prospective. An item carrying refs: [ID] plus extra.ref_kinds: {ID: related} is REFUSED on the next status update - "on-disk frontmatter has diverged from the index (refs)". The refusal own advertised remedy then completes the damage: sq repair re-derives the index from disk and stores refs: [ID:related], the next mutation commits the spelled form to the file, and sq check reports clean. So sq repair (_services/_maintenance.py::_rebuild_index_from_disk:1324) is a third owed path, not just a scan.
  - Reconciling after the fold does not work - I drove that too. frontmatter_skew docstring claims both sides go through the identical round trip; they do not, and symmetrising it (running the base side through Item.from_frontmatter(base.to_frontmatter_dict()) as well) STILL reports refs skew, because the legacy map is real data the index does not hold. The fold is information-adding on the disk side, so the encoding has to be canonical when the fold produces it.
  - So: one site, at the fold INPUT, and the rejection this task calls not-to-be-revisited is reversed on driven evidence. Item.from_frontmatter takes the resolved default kind as a REQUIRED keyword argument and hands it to _read_refs/fold_legacy_kinds. The "many call sites" premise is false: there are exactly three in src/squads (_itemfile.py:222, _services/_maintenance.py:1324, _services/_maintenance.py:2209 - the last parses and discards), and a required keyword makes an omission a type error, not a silent regression. That is the same rule ADR-777 B2 applies to top_level_keys. _models/ still resolves nothing: receiving a resolved kind as data is exactly the split A1 already draws for make_ref/split_ref.
  - frontmatter_skew/ensure_no_skew take the same required argument. Their nine call sites are all Service mixin methods with self.spec already in hand - _base.py:1009, _items.py:360, _subentities.py:686 and :746, _retype.py:161, _rename.py:124, _import.py:301, _maintenance.py:254 and :2033 - so nothing new threads through the CLI. Resolve WorkflowSpec.default_ref_kind() ONCE PER PASS, not per item, so a spec with the wrong number of defaults fails as one clean refusal naming the spec rather than raising partway through a rebuild.
  - Anti-drift is structural, not convention: one fold, one entry point, plus a tests/meta guard enumerating Item.from_frontmatter three call sites so a fourth fails the suite - the shape tests/unit/test_agent_backend_abc_stays_at_seven_documented_methods.py already uses. The agreement test asserts CONVERGENCE: table-driven over bare, spelled-default, bare-plus-legacy-map-naming-the-default, and the two non-default controls (spelled blocks, map naming blocks), each as a disk file against an index holding the canonical form. Per row: frontmatter_skew empty, sq repair stores the canonical encoding, the next ordinary mutation writes it, sq check clean. The three default rows converge on bare, the controls on ID:blocks. Load-bearing assertion: the legacy-map row and the bare row produce byte-identical to_frontmatter_dict() output. One corpus-level row runs check, repair, check, mutate-everything, check with the index refs byte-identical across the repair - that row catches an asymmetry at any of the three sites, not only the one under test.
  - One-site-one-test survives, but only under this shape - it was true for the wrong reason before. No corrective sweep still holds, with a corrected reason: disk is canonical, but a squad that already ran sq repair at a version carrying the structural primitives holds spelled defaults in its INDEX, and re-running sq repair after the fix re-derives them canonically because repair reads the corpus and not the index. No new verb is owed. @python-dev @tech-lead
- [2026-08-25T16:14:38Z] Olivia Lead:
  - Body and ST1/ST2 realigned to the amended A3. My earlier seam flag is answered and closed: the normalisation goes at the FOLD INPUT, not at _index/_store.py _validate_item_vocab, which I had pointed the dev at. Verified the architect structural claims myself before rewriting rather than editing off the summary - Item.from_frontmatter has exactly three call sites in src (grep: _itemfile.py:222, _maintenance.py:1324, _maintenance.py:2209); _read_refs has one caller, _frontmatter_payload, which has one caller; _read_from_disk builds via model_validate_json; the nine skew call sites match his list exactly; the guard-shape test file exists.
  - Three claims removed because they did not survive his driving, and they were mine: the damage is NOT merely prospective (a legacy-map item is already refused on its next mutation, and sq repair - the refusal own advertised remedy - completes the damage by storing the spelled form); the two sides of the skew guard do NOT re-derive through an identical fold, since the index side never folds; and threading a parameter is no longer rejected - a REQUIRED keyword makes omission a type error, the same rule ADR-777 B2 applies to top_level_keys.
  - Added what the body never named: sq repair (_rebuild_index_from_disk:1324) is an owed path, not just a scan, and it is the only site that stores the folded item. Also flagged for the dev to fix frontmatter_skew own docstring, which asserts the identical-round-trip claim that misled this task in the first place. Coverage replaced wholesale with the convergence table (five encodings, three default rows converging bare, two blocks controls), the byte-identical to_frontmatter_dict assertion, the corpus-level check/repair/check/mutate/check row, and the tests/meta call-site guard. ST3 (migration refreeze) unchanged - that half was never in question.
  - TASK-807 unaffected: A3 graph clause is unchanged word for word, and 807 touches _services/_refs.py only, so it neither collides with nor depends on this. Left it alone.
- [2026-08-25T16:46:05Z] Elias Python:
  - Implemented per A3-as-it-now-stands. Item.from_frontmatter/_frontmatter_payload/_read_refs/fold_legacy_kinds all take a required default_kind keyword; fold_legacy_kinds now normalises ANY resolved kind equal to default_kind to bare (legacy-map-sourced or already inline-spelled), not just legacy-map entries.
  - Normalisation lands at the fold's input only, per the amended A3: nothing added to _index/_store.py::_validate_item_vocab. The three from_frontmatter call sites (_itemfile.py::frontmatter_skew, _maintenance.py::_rebuild_index_from_disk, _maintenance.py::_scan_for_check) all thread it through; frontmatter_skew/ensure_no_skew/update_frontmatter (plus apply_type_change/_check_batch_skew/_section_edit_core/_refresh_catalog_extra/_refresh_role_skills_extra, which chain into them) all take the same required keyword. Every Service caller resolves self.spec.default_ref_kind() once per pass, hoisted before any per-item try/except so a spec with the wrong number of defaults fails as one clean refusal, not N miscategorized per-file issues.
  - pyright proves the omitted-keyword case is a type error (reportCallIssue, verified standalone and via the full gate).
  - Migration runner refrozen: _v0_1_to_v0_2.py carries its own private _fold_legacy_kinds + frozen _DEFAULT_KIND='related' constant, no longer imports fold_legacy_kinds from _models. Added tests/meta/test_migrations_never_import_a_vocabulary_folded_primitive.py (AST scan, allows split_ref/make_ref) plus byte-assertions in tests/integration/test_migrations.py.
  - Added tests/meta/test_from_frontmatter_call_sites_stay_enumerated.py enumerating the three call sites by (file, function) - fails on a planted fourth.
  - New tests/service/test_default_ref_kind_encoding_convergence.py: five-row table (bare/spelled-default/legacy-map-default all converge bare; spelled-blocks/legacy-map-blocks stay spelled), byte-identical to_frontmatter_dict() for the bare vs legacy-map-default rows, and a corpus-level check-repair-check-mutate-check row with a second back-to-back repair proving convergence (not oscillation).
  - Restored the default-kind leg of test_frontmatter_skew_guard.py::test_legacy_ref_kinds_map_does_not_false_refuse (parametrized default/non-default) without losing the non-default leg.
  - Fixed frontmatter_skew's docstring: it no longer claims both sides round-trip through an identical fold; states plainly the index side never folds and the disk side is where default_kind must be resolved.
  - Found and fixed 8 pre-existing tests that hand-build WorkflowSpec.model_validate({...}) without a ref_kinds key (defaults to empty dict, so default_ref_kind() raised 'found 0') - added ref_kinds: dict(base.ref_kinds) to each. Also switched test_remove.py's width-tolerant-severing hand-plant from kind='related' to kind='blocks' - it was incidentally constructing an already-wrongly-indexed fixture (spelled default consistently on both index and disk) that my fix correctly flags as skewed until repaired; the test's actual subject (width tolerance) is orthogonal to which kind is used.
  - Full targeted sweep (service+unit+integration+meta+cli+tui, not slow): 3986 passed, 2 skipped, 0 failed. pyright/ruff check/ruff format --check all clean. sq check clean.
- [2026-08-25T16:54:19Z] Elias Python:
  - Closed the write-door gap. Confirmed the mechanism as reported: _cli/_create.py's two --ref parse sites make_ref() the raw user kind unnormalised, and _services/_base.py::_create_model validated a spelled kind was declared but stored refs verbatim (unlike _add_ref_model, which already computes wire_kind).
  - Fix at the service seam per your steer: _create_model (src/squads/_services/_base.py, the 'if refs:' block) now rewrites every ref to its canonical wire form after the declared-kind check, mirroring add_ref's wire_kind pattern - make_ref(rid, "" if kind == default_kind else kind). This is the one PURE seam every create path shares (Service.create -> _create_core -> _create_model, and the bulk importer's _sim_create/_create_core), so the CLI, direct Service.create() calls, and any future caller all get it for free; left _cli/_create.py's own make_ref calls as-is since normalizing downstream makes the intermediate spelling moot.
  - Checked the other two make_ref call sites you flagged. _services/_import.py::_resolve_refs already normalizes (wire_kind = "" if kind == default_kind else kind) and both create-events and ref-add-events route through it before ever reaching _create_model/_add_ref_model - not a gap, and my new _create_model normalization is a harmless no-op there (already-canonical input). _services/_retype.py::_remap_ref only rewrites the ID half of an ALREADY-STORED ref during rename/retype, passing the existing kind through unchanged via split_ref - it never validates or mints a kind fresh, so it can carry forward a pre-existing bad encoding but cannot introduce a new one; not the same class of gap and left untouched.
  - Reproduced your exact repro on a fresh scratch squad before and after: sq init, sq create task Target, sq create task Source --ref TASK-2:related now writes refs: [TASK-2] (bare) to disk, sq check is clean immediately, no drift warning. Control: --ref TASK-2:blocks still writes refs: [TASK-2:blocks] spelled, round-trips clean.
  - Coverage: added a create-path row to tests/service/test_default_ref_kind_encoding_convergence.py (2 cases: default-kind-lands-bare, control-nondefault-stays-spelled) asserting the ref lands bare in the freshly-created Item AND in the file create() itself just wrote, sq check clean immediately, frontmatter_skew empty - no repair involved, exercising the write door the existing five disk-first rows never touched.
  - Targeted sweep (service+unit+integration+meta+cli, not slow): 3937 passed, 2 skipped, 0 failed. pyright/ruff check/ruff format --check clean. sq check clean on this repo. Nothing needed outside the task's stated scope.
<!-- sq:discussion:end -->
