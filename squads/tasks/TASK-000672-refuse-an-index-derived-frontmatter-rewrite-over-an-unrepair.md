---
id: TASK-672
sequence_id: 672
type: task
title: Refuse an index-derived frontmatter rewrite over an unrepaired skew
status: InReview
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
  status: Done
- local_id: ST2
  title: Skip and report a drifted roster item in sync
  status: Done
- local_id: ST3
  title: Tests for both failure directions across every path
  status: Done
- local_id: ST4
  title: 'Pre-flight the batch: import, bulk retype, rename-status'
  status: Done
created_at: '2026-07-27T16:13:19Z'
updated_at: '2026-07-27T21:47:29Z'
---
<!-- sq:body -->
Close the conditional half of ADR-663 §1's guarantee: a write refuses, loudly, rather than silently
overwriting an unrepaired markdown-ahead skew.

Addresses REV-671 F4. Read the finding and ADR-663 §1 (amended) before starting — §1's "What the
guard compares", "The roster regen path", "Batch mutation is a third shape" and the
`repad`/`renumber` paragraph are the specification this task implements, and they are binding.

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

The cost of closing it is stated and accepted: a drifted item is not mutable until repair runs. It
blocks its own mutations, loudly, with a one-command remedy, and the block is per-item.

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

No schema change, no new frontmatter or index field.

## Three constraints that are the whole risk

**1. Capture the base in the pure half of a core, before the delta is applied.** The mutation cores
already split into a pure `_*_model` half and an I/O half; the base belongs to the pure half, taken
from the index-loaded item at entry. Explicitly **not** derived from a reflog delta — that structure
is designed to describe logging, not to describe a write, and tying the guard to it would couple two
things that change for different reasons.

**2. Normalize structurally; the exclusion list is empty, and stays empty by default.** By-design
divergences are a *category, not a list*, and the category spans **both** sides of the comparison:
the index side corrects at load (the legacy-severity relocation, the counter and width fixups), and
the file side corrects at parse (the pre-0.2 `extra.ref_kinds` map folded into inline `"ID:kind"`
refs).

Normalize once, structurally, by putting both sides through the same serializer: compare
`Item.from_frontmatter(disk).to_frontmatter_dict()` against the base's `to_frontmatter_dict()`.
Measured against the real model, that collapses **all** the known divergences — legacy
`extra.severity`, `extra.ref_kinds`, and a padded id (recomputed from prefix and sequence number) —
along with key order and absent-versus-`None`. So there is nothing to exclude today, and no field
needs hand-normalizing.

Implementation detail that makes the last one work: `path` is a `from_frontmatter` keyword argument,
so it collapses by construction **provided the guard passes the item's own path**. Pass it.

**Standing rule:** a future correction that does *not* collapse through the round-trip is registered
explicitly, on whichever side it lives, in the same change that introduces it. Unregistered, it
becomes a false refusal. An excluded field would be a permanent blind spot; a normalized one still
catches a real skew — so registration means teaching the round-trip, not adding to a skip list.

**3. Merge-on-write is rejected, on correctness rather than cost.** Recorded so nobody re-proposes it
as the "obvious" better fix:

- it invents per-field precedence rules that nothing in the model justifies;
- it would apply values the workflow gate never validated — `can_transition` ran against the
  *index-loaded* item, so a status arriving from the file has passed no gate;
- it would have to treat the by-design divergences above as real conflicts.

Detection is fail-closed and needs none of that machinery.

## Where the guard attaches, and where it does not

**Single mutation — refuse.** One item's write *is* the operation, so refusing is proportionate. No
new I/O: both frontmatter-rewriting seams already read the file's full text before writing.

**`sq sync`'s roster regen — skip and report, exit 0.** The invariant is identical (never silently
overwrite an ahead-of-index value) and only the response scales. `sync` is bulk regeneration of
derived state and is itself what an operator reaches for when generated files are wrong, so aborting
the run would block the remedy over a condition `sync` did not cause. Skipping preserves the
surviving content and defers only regeneration — stale cache, not loss. Exit stays 0 because
`sq check` is the dedicated reporter and already fails on that item; duplicating its exit semantics
would break scripted syncs. A verify/strict mode is where a non-zero exit for stale generated state
would belong, and that is not this task.

**Batch mutation — check before the batch, never inside it.** A mid-flight raise is the one option
that must not ship: §1's own ordering rule means the markdown writes of everything already applied
stand, so one drifted item turns an import into a *partially applied* import — worse than the
overwrite the guard exists to prevent. See the dedicated subtask; this is where the precision is.

**`repad` and `renumber` — outside the guard, and not by exemption.** Worth stating as reasoning so
nobody later "fixes" the omission: the guard attaches to *index-derived frontmatter substitution*,
not to file writes in general. `repad` renames files and leaves their bytes untouched; `renumber`
rewrites id strings inside the files' own content. Neither sources a value from the index, so
neither can revert a skew — and a guard placed there would false-refuse on precisely the id-width
divergence `repad` creates. Do not add one.

## Release scope

Ships in **0.12.2**, with this round. The refusal is user-visible behaviour that would ordinarily
wait for a minor; shipping it in a patch is a deliberate, accepted call, not an oversight.

What that costs is a higher bar on false refusals, and the acceptance criteria carry it. A guard that
wrongly refuses is far worse than the loss it prevents: the silent loss needs an interrupted write
first and then touches one item, whereas a false refusal hits every user on every mutation of a
perfectly healthy board. Under-detection degrades to today's behaviour; over-detection bricks the
tool. When the two trade off, err toward letting the write through.

Nothing else blocks this: the write path and the confirm pass it builds on are already in place.

## Acceptance

**It refuses a real skew.** An unrepaired markdown-ahead skew makes the next write of that item
refuse before writing anything, with a message naming the item, what diverged, and `sq repair`. The
guard must be shown to fire — a test that passes because the guard is inert proves nothing.

**It does not refuse a healthy board.** The five false-refusal cases below are all expected to pass
**by construction**, because the round-trip collapses every known divergence — a dev who finds them
green on first run has the right result, not a broken test. They stay as tests anyway: they are the
regression net that catches the day someone adds a correction without registering it, and their
value is precisely that they are cheap and boring while the guard is correct.

- an item whose severity lives in the legacy `extra.severity` location;
- a squad after `sq migrate repad`, where the file's id width and the index's disagree;
- an item whose refs are still carried by a pre-0.2 `extra.ref_kinds` map;
- an item with optional fields absent from the file (no `parent`, no `assignee`, no `extra`);
- a plain round trip: create an item, mutate it twice in a row with no interruption, and assert the
  second mutation is not refused.

**End to end on the finding.** F4's reproduction refuses; after `sq repair` the same mutation
succeeds, and both the interrupted value and the new delta are present on disk.

**Per path.** `sq sync` skips a drifted roster item, names it, regenerates the rest and exits 0; a
clean roster syncs exactly as before with no new output. A bulk import naming a drifted item reports
it in the pre-pass and applies nothing. Bulk retype and rename-status refuse before their first
write. `repad` and `renumber` are unaffected, including on a board that has a real skew.

**Everything else.** No schema change and no new frontmatter or index field. `uv run sq check`
clean; the suite green under `uv run --all-extras`.
<!-- sq:body:end -->

## Subtasks

_Add with `sq task 672 add-subtask "<title>"`; track with `sq task 672 subtask <n> update --status <Status>`._

<!-- sq:summary -->
| Subtask | Status | Assignee | Title | Story |
| --- | --- | --- | --- | --- |
| ST1 | Done |  | Compare and refuse on the mutation path |  |
| ST2 | Done |  | Skip and report a drifted roster item in sync |  |
| ST3 | Done |  | Tests for both failure directions across every path |  |
| ST4 | Done |  | Pre-flight the batch: import, bulk retype, rename-status |  |
<!-- sq:summary:end -->

<!-- sq:subtasks -->

<!-- sq:subtask:ST1 -->
### ST1 — Compare and refuse on the mutation path

<!-- sq:subtask:ST1:head -->
**Status:** 🟢 Done
<!-- sq:subtask:ST1:head:end -->

<!-- sq:subtask:ST1:body -->
The three-way comparison and the refusal, on the single-mutation write path.

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

Put the comparison in one place both reach. A second copy of the predicate is the outcome to avoid —
and the batch pre-pass has to reach the same one, so give it a shape callable with
`(on-disk frontmatter, base item)` rather than one welded to the write path.

**Normalize structurally — there is nothing to hand-normalize.** Compare
`Item.from_frontmatter(disk, path=<the item's own path>).to_frontmatter_dict()` against the base's
`to_frontmatter_dict()`. Both sides then come out of one serializer, which collapses every known
divergence: legacy `extra.severity`, the pre-0.2 `extra.ref_kinds` map, a padded id (recomputed from
prefix and sequence number), key order, and absent-versus-`None`. That was measured against the real
model, so the exclusion list is empty and no field needs special-casing.

The `path` keyword argument is load-bearing: pass the item's own path, or the `path`-derived fields
will not collapse and the guard will false-refuse on every item.

**Refuse before any write.** No frontmatter write, no index commit, no reflog entry — the mutation
must not half-apply. Raise `SquadsError` so the CLI's error decorator renders it cleanly and exits 1.
The message names the item, the diverging field(s), and `sq repair`; "run repair" alone gives the
reader nothing to verify against.

`write_new` is untouched — a create has no prior file to diverge from.

Acceptance:
- The base is captured in the pure half of the core and nowhere else.
- Both rewrite seams are covered — a status/metadata mutation and a body/comment edit — with one
  copy of the comparison, reusable by the batch pre-pass.
- The comparison passes the item's own path into `from_frontmatter`.
- An unrepaired skew refuses before writing anything; the message names the item, the field(s) and
  `sq repair`.
- After `sq repair`, the same mutation succeeds with both the surviving value and the new delta on
  disk.
- If any divergence turns out not to collapse through the round-trip, it is registered explicitly
  (taught to the normalization) rather than added to a skip list — and named in a comment.
<!-- sq:subtask:ST1:body:end -->

#### Discussion

<!-- sq:subtask:ST1:discussion -->
<!-- sq:subtask:ST1:discussion:end -->
<!-- sq:subtask:ST1:end -->

<!-- sq:subtask:ST2 -->
### ST2 — Skip and report a drifted roster item in sync

<!-- sq:subtask:ST2:head -->
**Status:** 🟢 Done
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
### ST3 — Tests for both failure directions across every path

<!-- sq:subtask:ST3:head -->
**Status:** 🟢 Done
<!-- sq:subtask:ST3:head:end -->

<!-- sq:subtask:ST3:body -->
Pin the guard against both ways it can be wrong, across every path it attaches to. The
false-refusal side carries more weight than the missed-detection side, and the tests should reflect
that ratio.

**It fires on a real skew.** Reproduce F4's shape end to end: fault the index commit during a
`--desc` update so the file is ahead, then attempt an ordinary `set_status` on that item and assert
it refuses without writing. Then `sq repair`, re-run the mutation, and assert both the interrupted
description and the new status are on disk. Fault the *index commit* rather than stubbing the write
helper — a test whose outcome is guaranteed by its own stub proves routing, not behaviour. Diverge a
field **outside `{status, parent}`** deliberately, since that is the case the narrower design would
have missed.

**It does not fire on a healthy board.** One test each, all asserting a normal mutation still
succeeds:

- an item whose severity lives in the legacy `extra.severity` location;
- a squad after `sq migrate repad`, with the file's id width behind the index's;
- an item whose refs are still carried by a pre-0.2 `extra.ref_kinds` map;
- an item with optional fields absent from the file (no `parent`, no `assignee`, no `extra`);
- a plain round trip: create an item, mutate it twice in a row with no interruption, and assert the
  second mutation is not refused.

**These are all expected to pass on the first run**, because the round-trip through
`Item.from_frontmatter(...).to_frontmatter_dict()` collapses every one of these divergences
structurally — that was measured against the real model, not assumed. Green immediately is the
correct result, not a sign the test is inert. Their job is to be the regression net for the day a
new load-time or parse-time correction lands unregistered, so write them as real end-to-end
mutations rather than as assertions about the comparison helper: a test that only exercises the
helper stops protecting anything the moment a caller stops using it.

To keep the set honest against inertness, at least one of them should be shown to fail if the
round-trip normalization is removed — the same technique that caught the sabotage-proof gap in the
atomic-write tests.

**Every path, both directions.** Single mutation at both write seams (metadata/status, and a
body/comment edit); `sq sync` on a drifted roster item and on a clean roster; a bulk import against
a drifted target and against a clean board; bulk retype and rename-status; and `repad`/`renumber` on
a board carrying a real skew, asserting they are *unaffected* — that last one is what stops someone
later adding a guard where the decision says there must not be one.

Name tests by the behaviour they pin, never by a ticket id.

**Changelog.** A write that used to succeed now refuses, so it needs an adopter-facing line under the
unreleased section: `sq` refuses to overwrite an item whose file and index disagree and points at
`sq repair`; `sq sync` skips such an item and names it. Adopter wording only — no ticket ids, no
repo-process detail, nothing about the internal comparison. It must not contradict the same
release's durability line, which claims the truncation is gone and the survivor repairable; that
stays true, and this line completes it.

Acceptance:
- The F4 reproduction refuses, and succeeds after repair with both values intact.
- Every false-refusal case above mutates cleanly, and at least one is shown to fail without the
  normalization.
- Every attachment path is covered in both directions, including `repad`/`renumber` being unaffected.
- Full suite green under `uv run --all-extras`; run it once, redirect to a file, and read the file
  rather than re-running to reslice output.
- CHANGELOG updated in the unreleased section.
<!-- sq:subtask:ST3:body:end -->

#### Discussion

<!-- sq:subtask:ST3:discussion -->
<!-- sq:subtask:ST3:discussion:end -->
<!-- sq:subtask:ST3:end -->

<!-- sq:subtask:ST4 -->
### ST4 — Pre-flight the batch: import, bulk retype, rename-status

<!-- sq:subtask:ST4:head -->
**Status:** 🟢 Done
<!-- sq:subtask:ST4:head:end -->

<!-- sq:subtask:ST4:body -->
Batch mutation: the check runs **before** the batch, never inside it.

A mid-flight raise is the one option that must not ship. Bulk import applies every event inside one
transaction, and §1's ordering rule means the markdown writes of everything already applied stand
when the body raises — so one drifted item turns an import into a partially applied import, which is
worse than the overwrite the guard exists to prevent.

**Bulk import.** The importer is already validate-first for exactly this reason: `_plan_import`
simulates every event against a throwaway copy of the index, collects every issue instead of
stopping at the first, and `_apply_import` runs only on a clean plan — its docstring pins that an
apply-time failure "can therefore only be I/O". A guard raising inside the apply loop would break
that contract, not merely be unpleasant.

So the guard becomes one more collected `ImportIssue` in the pre-pass, with one precision that must
not be missed:

- **Once per targeted pre-existing item, not once per event.** After that item's first event,
  divergence from disk is the import's own doing, and a per-event check would false-refuse on event
  two.
- **Creates are out of scope** — no prior file to diverge from.
- `ImportIssue` is `(line, message)`, so a per-item issue has to choose a line: use the line of that
  item's *first* targeting event, which is where a reader will look.

Note the one real cost, and do not paper over it: the pre-pass is pure today — it simulates against
an in-memory copy and touches no files. Adding the guard means reading each targeted pre-existing
item's `.md` during the pre-pass. That is N reads for N distinct pre-existing targets, bounded by
the affected set rather than by the board, and it is the price of keeping the check out of the apply
loop. State it in the pre-pass's docstring rather than leaving the next reader to discover that
"validate-first" now touches disk.

**Bulk retype and rename-status.** Same shape: the affected set is known up front (both compute it
before touching anything), so pre-flight that set and refuse before the first write. Their
file-rollback path stays what it is — a crash safety net, not the guard's mechanism; do not
implement the guard as "let it fail and roll back". These two already read every item file for their
rollback snapshot, so the file content the comparison needs may already be in hand — check before
adding a second read.

Acceptance:
- A bulk import naming a drifted pre-existing item reports it as a pre-pass issue and applies
  nothing; the plan still collects every *other* issue in the same run rather than stopping there.
- An import that targets the same drifted item with several events reports it once, not once per
  event.
- An import that only creates items is never affected, however many events it carries.
- Bulk retype and rename-status refuse before their first write, leaving every file untouched.
- No guard check runs inside `_apply_import`; an apply-time failure can still only be I/O.
- The pre-pass's new disk reads are documented where the validate-first contract is described.
<!-- sq:subtask:ST4:body:end -->

#### Discussion

<!-- sq:subtask:ST4:discussion -->
<!-- sq:subtask:ST4:discussion:end -->
<!-- sq:subtask:ST4:end -->
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
- [2026-07-27T20:42:02Z] Olivia Lead:
  - Both rulings folded in; the ticket is dispatchable. New ST4 carries the batch shape (guard runs in the importer's pre-pass as one more collected ImportIssue, once per targeted pre-existing item rather than per event, creates out of scope; bulk retype and rename-status pre-flight their known affected set and refuse before the first write; _rollback_files stays a crash safety net, not the mechanism). repad/renumber stated as non-applicability with the reasoning — the guard attaches to index-derived frontmatter substitution, not to file writes — so nobody later adds one and false-refuses on the id-width divergence repad itself creates.
  - Round-trip is now the sanctioned default rather than a proposal, and my id-width caveat is withdrawn — @architect measured it against the real model and a padded id collapses too (recomputed from prefix + sequence_id). Exclusion list is empty; the standing rule is teach-the-normalization, not add-to-a-skip-list. The `path` kwarg is called out as load-bearing in ST1: pass the item's own path or every item false-refuses.
  - Acceptance updated: the five false-refusal cases now pass by construction, and the body says so explicitly so a dev seeing them green on first run knows that is the right result. Added a counterweight so the set cannot be inert — at least one must be shown to fail with the normalization removed, the same technique that caught the sabotage-proof gap in the atomic-write tests.
  - One cost I corrected in my own body while folding: the 'no new I/O' claim is true for the single-mutation path (both seams already read the file) but false for the import pre-pass, which is pure today and will now read each targeted pre-existing item's .md. Bounded by the affected set, not the board — the claim is scoped per path now, and ST4 asks for it in the validate-first docstring rather than left for the next reader to discover.
- [2026-07-27T20:42:45Z] Catherine Manager:
  - Dispatched. Guard ships in 0.12.2 per Pierre; ADR-663 is binding and now covers the bulk pre-pass ruling, the empty exclusion list, and repad/renumber non-applicability.
<!-- sq:discussion:end -->
