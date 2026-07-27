---
id: TASK-672
sequence_id: 672
type: task
title: Refuse an index-derived frontmatter rewrite over an unrepaired skew
status: Draft
author: tech-lead
refs:
- ADR-663:implements
- REV-671:addresses
description: 'Fail-closed detection: compare on-disk frontmatter against the index-derived
  item before rewriting, and refuse with a sq repair pointer instead of silently reverting
  the skew.'
subentities:
- local_id: ST1
  title: Compare and refuse on the mutation path
  status: Todo
- local_id: ST2
  title: Skip and report a drifted roster item in sync
  status: Todo
- local_id: ST3
  title: Tests for both failure directions, and the changelog line
  status: Todo
created_at: '2026-07-27T16:13:19Z'
updated_at: '2026-07-27T20:29:57Z'
---
<!-- sq:body -->
Close the conditional half of ADR-663 §1's guarantee: an ordinary write refuses, loudly, rather
than silently overwriting an unrepaired markdown-ahead skew.

Addresses REV-671 F4. Read the finding and ADR-663 §1 (amended) before starting — §1's "What the
guard compares" and "The roster regen path" paragraphs are the specification this task implements,
and they are binding.

## What is broken

§1 mandates the markdown-ahead skew as the *safe* direction, and repair heals it losslessly — but
only if repair runs before anything next rewrites that item's frontmatter from index-derived state.
Nothing enforces that, and two ordinary operations violate it:

- **Any mutation.** A core loads the item from the index, applies its delta, and calls
  `update_frontmatter(path, item)` → `replace_frontmatter`, which substitutes the **whole**
  frontmatter block from the index-derived `Item`. The interrupted mutation's fields are replaced by
  index values plus the delta, with nothing left on disk for repair to find afterwards.
- **`sq sync`, for roster items.** The regen path rewrites frontmatter from the index the same way,
  so a drifted role or skill loses its surviving fields to a routine sync.

Reproduced in F4: crash the index commit during `update --desc`, then run one ordinary
`set_status`. The `description` key is gone from the file entirely. The mutation that destroyed it
succeeded normally and warned about nothing.

Body bytes are never at risk — a frontmatter rewrite preserves them verbatim — so the loss surface
is exactly frontmatter, sub-entity state included, per item, and it does not spread to other items.

## The mechanism: a three-way comparison, decoupled from `sq check`

**Not §3's drift predicate.** That predicate is a board-wide advisory over hundreds of items,
deliberately narrow (`status`, `parent`) so the scan stays cheap; a guard built to it would miss
description, assignee, labels, refs and sub-entity state — most of the at-risk surface, and F4's own
reproduction. The two are decoupled: §3's set is unchanged, and the guard's set is *derived* rather
than chosen.

Loss happens exactly where the pending write replaces an on-disk value the mutation itself did not
set. So the comparison is three-way, as in a version-control merge:

> the frontmatter **on disk**, against the frontmatter the index-loaded item would have serialized
> **before** the delta was applied.

**Every key is in scope.** The mutation's own fields — including the `updated_at` and session stamps
every write sets — drop out *structurally*, because they differ between the base and the post-delta
item, not between the base and the disk. No exclusion list, no per-field judgement.

In the normal case the two sides are identical, because the last successful mutation wrote both from
one item. That is what makes an inequality *evidence* rather than a heuristic — and it is also why a
false refusal is a serious defect rather than a tuning problem (see the release note below).

No new I/O: both frontmatter-rewriting seams already read the file's full text before writing —
`_itemfile.update_frontmatter` reads it to substitute the block, and the shared section-edit core
reads it to run its mutate closure. No schema change, no new stored field.

Creation is out of scope by construction: `write_new` has no prior file to diverge from.

## Three constraints that are the whole risk

**1. Capture the base in the pure half of a core, before the delta is applied.** The mutation cores
already split into a pure `_*_model` half and an I/O half; the base belongs to the pure half, taken
from the index-loaded item at entry. Explicitly **not** derived from a reflog delta — that structure
is designed to describe logging, not to describe a write, and tying the guard to it would couple two
things that change for different reasons.

**2. By-design divergences are a category, not a list: normalize, don't exclude.** The category is
*the corrections applied in memory when state is read, which only reach disk on the next write*.
Known members:

- the legacy-severity relocation (`extra.severity` → the top-level `severity` field);
- id width, which differs between file and index after a `repad` until the file is next rewritten;
- the pre-0.2 `extra.ref_kinds` map, folded into inline `"ID:kind"` refs on read.

An excluded field is a permanent blind spot; a normalized one still catches a real skew. Normalize
the on-disk side wherever a normalization exists.

**The cheap way to get most of this for free** — worth trying first, and measuring rather than
assuming: instead of comparing raw parsed YAML, round-trip the on-disk frontmatter through
`Item.from_frontmatter(...).to_frontmatter_dict()` and compare that against the base's
`to_frontmatter_dict()`. Both sides are then produced by the same serializer, so every read-time
normalization already implemented there applies to both — `_read_severity` folds legacy severity,
`_read_refs`/`_read_extra` fold `ref_kinds`, and absent-vs-`None`, key order and optional-field
omission stop being differences at all. Establish empirically which divergences actually survive
that round-trip (id width is the one to check first) and normalize only those by hand — comparing
ids by sequence number, for which `_check_items` is the precedent.

**Standing rule to carry into the code:** any future in-memory correction applied at read time must
be registered with this guard in the same change that introduces it, or it silently becomes a false
refusal. Note the correction sites are on *both* sides — `IndexStore.load()` corrects the
index-loaded item, `Item.from_frontmatter` corrects the file-loaded one — so the rule covers both,
not only `load()`.

**3. Merge-on-write is rejected, on correctness rather than cost.** Recorded so nobody re-proposes it
as the "obvious" better fix:

- it invents per-field precedence rules that nothing in the model justifies;
- it would apply values the workflow gate never validated — `can_transition` ran against the
  *index-loaded* item, so a status arriving from the file has passed no gate;
- it would have to treat the by-design divergences above as real conflicts.

Detection is fail-closed and needs none of that machinery.

## The roster regen path: skip and report, never refuse the run

`sq sync` shares the loss but not the response. It leaves the drifted item's file untouched, names it
in the output with the `sq repair` pointer, and regenerates everything else. **Exit status stays 0.**

The invariant is identical — never silently overwrite an ahead-of-index value — and only the response
scales with the operation. Refusing is proportionate when one item's mutation *is* the operation;
`sync` is bulk regeneration of derived state and is itself what an operator reaches for when
generated files are wrong, so aborting the run would block the remedy over a condition `sync` did not
cause. Skipping preserves the surviving content and defers only regeneration — stale cache, not loss.
The exit code stays 0 because `sq check` is the dedicated reporter and already fails on that item;
duplicating its exit semantics here would break scripted syncs. A verify/strict mode is where a
non-zero exit for stale generated state would belong, and that is not this task.

## Release scope

Ships in **0.12.2**, with this round. The refusal is user-visible behaviour that would ordinarily
wait for a minor; shipping it in a patch is a deliberate, accepted call, not an oversight.

What that costs is a higher bar on false refusals, and the acceptance criteria carry it. A guard that
wrongly refuses is far worse than the loss it prevents: the silent loss needs an interrupted write
first and then touches one item, whereas a false refusal hits every user on every mutation of a
perfectly healthy board. Under-detection degrades to today's behaviour; over-detection bricks the
tool. When the two trade off, err toward letting a write through.

Nothing else blocks this: the write path and the confirm pass it builds on are already in place.

## Acceptance

**It refuses a real skew.** An unrepaired markdown-ahead skew makes the next write of that item
refuse before writing anything, with a message naming the item, what diverged, and `sq repair`. The
guard must be shown to fire — a test that passes because the guard is inert proves nothing.

**It does not refuse a healthy board.** One "a normal mutation still succeeds" test per known
by-design divergence, each as a first-class case rather than an afterthought:

- an item whose severity lives in the legacy `extra.severity` location;
- a squad after `sq migrate repad`, where the file's id width and the index's disagree;
- an item whose refs are still carried by a pre-0.2 `extra.ref_kinds` map;
- an item with optional fields absent from the file (no `parent`, no `assignee`, no `extra`), where
  the serialized base omits them too — absent must not read as a divergence.

**End to end on the finding.** F4's reproduction refuses; after `sq repair` the same mutation
succeeds, and both the interrupted value and the new delta are present on disk.

**Everything else.** No new I/O on the write path; no schema change and no new frontmatter or index
field; `sq sync` skips a drifted roster item, names it, regenerates the rest and exits 0; a clean
roster syncs exactly as before with no new output. `uv run sq check` clean; the suite green under
`uv run --all-extras`.
<!-- sq:body:end -->

## Subtasks

_Add with `sq task 672 add-subtask "<title>"`; track with `sq task 672 subtask <n> update --status <Status>`._

<!-- sq:summary -->
| Subtask | Status | Assignee | Title | Story |
| --- | --- | --- | --- | --- |
| ST1 | Todo |  | Compare and refuse on the mutation path |  |
| ST2 | Todo |  | Skip and report a drifted roster item in sync |  |
| ST3 | Todo |  | Tests for both failure directions, and the changelog line |  |
<!-- sq:summary:end -->

<!-- sq:subtasks -->

<!-- sq:subtask:ST1 -->
### ST1 — Compare and refuse on the mutation path

<!-- sq:subtask:ST1:head -->
**Status:** ⚪ Todo
<!-- sq:subtask:ST1:head:end -->

<!-- sq:subtask:ST1:body -->
The three-way comparison and the refusal, on the write path.

**Capture the base in the pure half.** The mutation cores already split into a pure `_*_model` half
(no I/O) and an I/O half. The base — what the index-loaded item would serialize *before* the delta —
is taken in the pure half, at entry, from the item as loaded. Not derived from a reflog delta: that
structure describes logging, not a write, and coupling the guard to it ties two things that change
for different reasons.

**Compare at the write seam.** Two seams rewrite an item's frontmatter from an index-derived `Item`,
and both already read the file's full text first, so both have the on-disk side in hand at no extra
cost:

- `_itemfile.update_frontmatter(path, item)` — reads the text, substitutes the whole frontmatter
  block. Every metadata/status/ref/link core reaches the file through this.
- the shared section-edit core in `_services/_base.py` — reads the text, runs its mutate closure,
  then substitutes the frontmatter from the item.

Put the comparison in one place both reach. A second copy of the predicate is the outcome to avoid.

**Normalize rather than exclude.** Try the round-trip first — parse the on-disk frontmatter through
`Item.from_frontmatter(...)` and compare its `to_frontmatter_dict()` against the base's, so both
sides come out of the same serializer and every read-time normalization already implemented applies
to both. Then establish, by test rather than by reading, which by-design divergences still survive it
and normalize those explicitly (compare ids by sequence number; `_check_items` is the precedent).
Whatever is left unnormalized is a permanent blind spot, so keep that set as small as the code
allows and name each survivor in a comment.

**Refuse before any write.** No frontmatter write, no index commit, no reflog entry — the mutation
must not half-apply. Raise `SquadsError` so the CLI's error decorator renders it cleanly and exits 1.
The message names the item, the diverging field(s), and `sq repair`; "run repair" alone gives the
reader nothing to verify against.

`write_new` is untouched — a create has no prior file to diverge from.

Acceptance:
- The base is captured in the pure half of the core and nowhere else.
- Both rewrite seams are covered — a status/metadata mutation and a body/comment edit — with one
  copy of the comparison.
- An unrepaired skew refuses before writing anything; the message names the item, the field(s) and
  `sq repair`.
- After `sq repair`, the same mutation succeeds with both the surviving value and the new delta on
  disk.
- Every field the guard cannot normalize is named in a comment at the comparison.
<!-- sq:subtask:ST1:body:end -->

#### Discussion

<!-- sq:subtask:ST1:discussion -->
<!-- sq:subtask:ST1:discussion:end -->
<!-- sq:subtask:ST1:end -->

<!-- sq:subtask:ST2 -->
### ST2 — Skip and report a drifted roster item in sync

<!-- sq:subtask:ST2:head -->
**Status:** ⚪ Todo
<!-- sq:subtask:ST2:head:end -->

<!-- sq:subtask:ST2:body -->
The roster regen path, which loses the same fields through a different door — with the opposite
response.

`sq sync` regenerates a role's (and skill's) frontmatter from the index, so a drifted roster item
loses its surviving fields to a routine sync, with no mutation of that item involved.

**Ruled behaviour: skip and report, never refuse the run. Exit stays 0.** Leave the drifted item's
file untouched, name it in `sync`'s output alongside the `sq repair` pointer, and regenerate
everything else.

The reasoning belongs at the call site, because the asymmetry with the mutation path will otherwise
read as an inconsistency:

- `sync` is bulk regeneration of derived state and is itself what an operator reaches for when
  generated files are wrong. Aborting the run would block the remedy over a condition `sync` did not
  cause.
- Skipping preserves the surviving content and defers only regeneration — a stale cache, not loss.
- The exit code stays 0 because `sq check` is the dedicated reporter and already fails on that item.
  Duplicating its exit semantics here would break scripted syncs. A verify/strict mode is where a
  non-zero exit for stale generated state would belong; it is not this task.

The invariant is unchanged from the mutation path: never silently overwrite an ahead-of-index value,
and the skipped item must be visible in the command's output — not merely inferable from the absence
of a change.

Acceptance:
- A drifted roster item's frontmatter is not overwritten by `sq sync`.
- `sync` regenerates every other managed file in the same run and exits 0.
- The operator sees which item was skipped and is told to repair.
- A clean roster syncs exactly as before: no new output, no behaviour change, exit 0.
- The reason for skip-rather-than-refuse is recorded at the call site.
<!-- sq:subtask:ST2:body:end -->

#### Discussion

<!-- sq:subtask:ST2:discussion -->
<!-- sq:subtask:ST2:discussion:end -->
<!-- sq:subtask:ST2:end -->

<!-- sq:subtask:ST3 -->
### ST3 — Tests for both failure directions, and the changelog line

<!-- sq:subtask:ST3:head -->
**Status:** ⚪ Todo
<!-- sq:subtask:ST3:head:end -->

<!-- sq:subtask:ST3:body -->
Pin the guard against both ways it can be wrong. The false-refusal side carries more weight than the
missed-detection side, and the tests should reflect that ratio.

**It fires on a real skew.** Reproduce F4's shape end to end: fault the index commit during a
`--desc` update so the file is ahead, then attempt an ordinary `set_status` on that item and assert
it refuses without writing. Then `sq repair`, re-run the mutation, and assert both the interrupted
description and the new status are on disk. Fault the *index commit* rather than stubbing the write
helper — a test whose outcome is guaranteed by its own stub proves routing, not behaviour. Cover a
divergence outside `{status, parent}` deliberately, since that is the case the narrower design would
have missed.

**It does not fire on a healthy board.** One test each, all asserting a normal mutation still
succeeds:

- an item whose severity lives in the legacy `extra.severity` location;
- a squad after `sq migrate repad`, with the file's id width behind the index's;
- an item whose refs are still carried by a pre-0.2 `extra.ref_kinds` map;
- an item with optional fields absent from the file (no `parent`, no `assignee`, no `extra`) — absent
  must not read as a divergence against a base that omits them too;
- a plain round-trip: create an item, mutate it twice in a row with no interruption, and assert the
  second mutation is not refused. The guard's own premise is that the two sides are identical in the
  normal case; if that premise is wrong the tool is unusable, and this is the cheapest test that
  catches it.

If any of these fails, treat it as more urgent than a missed detection: under-detection degrades to
today's behaviour, over-detection refuses writes on healthy boards.

**Both write seams**, since the guard sits at two: a metadata/status mutation and a body or comment
edit, each in both directions (refuses a real skew, passes a clean item).

Name tests by the behaviour they pin, never by a ticket id.

**Changelog.** A write that used to succeed now refuses, so it needs an adopter-facing line under the
unreleased section: `sq` refuses to overwrite an item whose file and index disagree, and points at
`sq repair`; `sq sync` skips such an item and names it. Adopter wording only — no ticket ids, no
repo-process detail, nothing about the internal comparison. It must not contradict the same release's
durability line, which claims the truncation is gone and the survivor repairable; that stays true.

Acceptance:
- The F4 reproduction refuses, and succeeds after repair with both values intact.
- Every by-design divergence above mutates cleanly, each with its own test.
- Both write seams are covered in both directions.
- Full suite green under `uv run --all-extras`; run it once, redirect to a file, and read the file
  rather than re-running to reslice output.
- CHANGELOG updated in the unreleased section.
<!-- sq:subtask:ST3:body:end -->

#### Discussion

<!-- sq:subtask:ST3:discussion -->
<!-- sq:subtask:ST3:discussion:end -->
<!-- sq:subtask:ST3:end -->
<!-- sq:subtasks:end -->

## Discussion

<!-- sq:discussion -->
- [2026-07-27T16:14:03Z] Olivia Lead:
  - Cut from REV-671 F4 per @architect's ruling: fail-closed detection before an index-derived frontmatter rewrite, targeting 0.13 (the refusal is user-visible behaviour, not patch-release material). Body carries both risk constraints — the compared field set is never whole-dict equality (the legacy-severity backfill and post-repad id width diverge by design), and merge-on-write is recorded as rejected on correctness: invented per-field precedence, values the workflow gate never validated, and those same by-design divergences.
  - Scope note: the loss has a second trigger the ruling's wording covers only in passing — `sq sync`'s roster regen rewrites frontmatter from the index the same way, so a drifted role loses its fields without any mutation. Split into its own subtask (ST2) because refusing is not obviously right there: aborting a whole sync over one stale roster item blocks the operation an operator runs to repair generated state. Skip-and-report vs refuse-the-run is called out as a decision to make, not assumed.
  - @architect one question needs your answer before a dev starts, in the body's 'Open question' section: §3's drift predicate covers exactly status and parent, but §1's amendment states the at-risk surface as every frontmatter field including sub-entity state — so a guard on {status, parent} would not catch F4's own repro, which lost `description`. Three options laid out; the third (all fields minus a named exclusion list) is not the whole-dict equality you rejected, but it is not §3's set either, so it needs your sanction rather than my guess. @manager
- [2026-07-27T20:26:13Z] Pierre Chat:
  - Pulled into 0.12.2 — we're not going to do it if we defer. Ship the guard in this release rather than 0.13.
- [2026-07-27T20:29:57Z] Olivia Lead:
  - Body rewritten to @architect's final ruling; my three options are withdrawn — he rejected all of them. The guard is decoupled from §3's predicate (§3's set unchanged) and its comparison set is derived, not chosen: on-disk frontmatter vs what the index-loaded item would serialize BEFORE the delta, every key in scope, the mutation's own fields plus the updated_at/session stamps dropping out structurally. Base captured in the pure half of a core, never from a reflog delta. By-design divergences normalized rather than excluded, as a category. ST2 ruled: skip and report, exit 0, never refuse the run.
  - One addition to the divergence list he did not name: the pre-0.2 `extra.ref_kinds` map, folded into inline refs by `from_frontmatter`. It is the same category but lives on the *file* side, not in `load()` — so the standing registration rule in the body covers both correction sites, not only `load()`. Concrete way to collapse most of the category for free: compare `Item.from_frontmatter(disk).to_frontmatter_dict()` against the base's `to_frontmatter_dict()`, so both sides come out of one serializer; then normalize only what demonstrably survives that (id width first).
  - Release scope now 0.12.2 per op-pierre. Acceptance carries the resulting bar: five false-refusal tests (legacy severity, post-repad id width, legacy ref_kinds, absent optional fields, and a plain two-mutations-in-a-row round trip), plus a real-skew test outside {status, parent} so the guard cannot pass by being inert, plus both write seams in both directions. Stated tiebreak when detection and false refusals trade off: err toward letting the write through.
<!-- sq:discussion:end -->
