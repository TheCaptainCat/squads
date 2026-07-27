---
id: ADR-663
sequence_id: 663
type: decision
title: 'Durability model of the integrity core: markdown ahead, index last'
status: Accepted
author: architect
refs:
- BUG-655:addresses
- BUG-656:addresses
- BUG-657:addresses
- ADR-534
- ADR-249
description: Markdown is always ahead or equal and the index commits last; every squad-data
  .md write is an atomic replace; sq check stays lock-free and confirms cross-source
  claims; the active transaction is task-local and store-scoped.
created_at: '2026-07-27T14:02:48Z'
updated_at: '2026-07-27T14:45:25Z'
---
<!-- sq:body -->
# Context

Every squad mutation touches **two** durable artifacts: the item's `.md` (the source of truth,
invariant #1) and `.squads.json` (a rebuildable index, invariant #2's counter included). They are
written as two separate events inside one `IndexStore.transaction()`: the mutation cores in
`_services/` write the `.md` inside the transaction body; the store commits the index with
`_atomic_write` (tmp + fsync + `os.replace`) after the body returns. One lock (the three-layer
scheme in `_index/_store.py`) serialises *writers*. Readers take no lock at all.

Four consequences of that shape are unresolved, and they are one seam, not four:

- **Ordering.** Between the `.md` write and the index `os.replace` there is a window in which the
  two disagree. `remove_work_item` already states the correct rule in a local comment ("unlink
  BEFORE the index commit so the safe failure direction is preserved"), but the rule is written
  down at exactly one call site out of ~a dozen mutation cores, and one site contradicts it:
  `remove_item(purge=True)` unlinks the `.md` *after* the transaction closes.
- **Write atomicity.** Every `.md` write goes through `_aio.write_text` → `Path.write_text`, which
  truncates in place. There is no tmp-and-rename and no fsync anywhere on the markdown side. So the
  hazard in that window is not only "two files disagree" — a process killed inside `write_text`
  leaves a **truncated or empty `.md`**, and that loss is silent and terminal. `sq repair` rebuilds
  the index *from* the markdown, so a destroyed file leaves it nothing to rebuild from; repair does
  not fail loudly, it drops the item from the index as missing. The item is then unreachable by
  `show` and absent from `sq list -a`, with a corrupted orphan file on disk that no `sq` command can
  recover — data loss, not a drift warning. The same partial state is observable by a concurrent
  reader with no crash at all: a cut inside the frontmatter block leaves it with no closing
  delimiter, so `_scan_for_check` reports the file as having no `id` (error level); a cut inside the
  body leaves an sq marker straddling the cut unclosed. A cut cannot instead produce
  malformed-but-closed frontmatter: the block is serialized in full before any byte is written, and
  its closing `---` line cannot appear in a prefix that does not already contain the whole block.
- **Read atomicity.** `check()` loads the index and then walks every `.md` (0.5–2s on a few hundred
  items), and compares one against the other. Any mutation committing during the walk makes that
  comparison cross two different points in time. This is not a corner case produced by unusual
  timing: because the safe write order puts the `.md` first, an in-flight `create` is *guaranteed*
  to present a file the older index snapshot does not know, and an in-flight remove the reverse.
  Both are reported by `_index_reconciled` at **error** level, so `sq check` exits 3 — the same
  race that yields a cosmetic "status drift" warning also yields a false hard gate failure.
- **Active-transaction handle.** `transaction()` publishes the live transaction context on a shared
  instance attribute, assigned before any lock is held, so the only thing that keeps reflog entries
  attributed to the right transaction is the absence of concurrent transactions in one process.

## Crash model

The decisions below are made against a stated failure model, because "atomic" without a model is
unbounded:

- **In model: process death.** SIGKILL/SIGTERM, harness timeout, background-stop, OOM kill,
  container stop of the process, and — treated as the same event class — any exception escaping a
  transaction body. Writes already accepted by the kernel survive; program order is therefore
  sufficient to order durability events.
- **Out of model: host crash and power loss.** Ordering across those requires fsync of every file
  *and* its parent directory at each step, and even then the two-file skew can only be bounded, not
  removed, without a journal. `sq repair` remains the recovery path; no promise is made about which
  side is ahead.

Process death is the model that matters here: this project's own workflow routinely backgrounds and
stops agent processes mid-task.

# Decision

## 1. Skew direction: the markdown tree is ahead or equal; the index is never ahead

**Rule (binding at every mutation site).** Within a transaction, every write to squad data on the
markdown side — create, frontmatter update, marker-section edit, rename/move, unlink — happens
inside the transaction body, before it returns. The index `os.replace` is the transaction's last
write to squad data. Nothing that mutates an item `.md` may run after the commit.

The only post-crash state this permits is *markdown newer than index*, in every direction of
change:

| interrupted op | surviving state | `sq repair` outcome |
|---|---|---|
| create | file exists, not indexed | indexes it; counter high-water mark preserved, so the sequence number is never reissued |
| update | file has new value, index has old | adopts the file's value |
| remove | file gone, index still has entry | drops the orphan entry, reports it as missing |
| retype/rename | file at new path/id, index at old | re-indexes from the new path |

Each is healed **losslessly and by construction**: repair derives the index from the markdown, so a
markdown-ahead skew is not a special case it has to detect — it is simply the input. `load()`
raising the counter in memory when it trails the max sequence on disk closes the one remaining hole
(a lost counter bump cannot cause ID reuse even before repair runs).

The inverse skew is the lossy one, which is why it is forbidden rather than merely discouraged: an
index ahead of the markdown makes `sq repair` **silently revert** a committed mutation, or resurrect
a removed item. A loud, repairable inconsistency is strictly better than a quiet rollback.

Compliance is the skew direction, not the syntax. Doing the markdown work inside the transaction body
is how an ordinary mutation achieves it. Board-wide reshaping ops that own every file and finish by
rebuilding the index outright (`repad`, `renumber`) comply by ending in that rebuild, and must not be
restructured to nest hundreds of renames inside one transaction — that would hold the write lock for
the whole pass and cannot compose with a rebuild that replaces the index wholesale anyway.

**Exempt from the rule:**

- **Regenerable artifacts** — backend pointer files, managed regions in `CLAUDE.md`/`AGENTS.md`,
  `.claude/` output. They hold no state, are reproduced by `sq sync`, and may be written after the
  commit (as `update`'s pointer regen already does).
- **The reflog** — an append-only observability log, deliberately appended after `os.replace` under
  a never-raise contract. It is not source of truth and must stay where it is.

## 2. Per-file atomicity on the markdown side

Every write to squad **data** (item `.md` files, board notices, memory entries, `.squads.toml`) goes
through one
atomic-replace primitive: write a temp file in the same directory, flush, fsync, `os.replace`, all
in a single thread hop with no `await` between fsync and rename — the shape `_atomic_write` already
uses for the index. Consequences: a killed process can no longer truncate the source of truth, and
no reader can ever observe a partially written item file. Regenerable artifacts stay on the plain
write; their loss costs a `sq sync`, and routing them through the atomic primitive would be churn
for no invariant.

`.squads.toml` is squad data, not a regenerable artifact. `sq sync` only re-stamps its version
field; nothing reconstructs the rest — the active backends, the default role, the schema version the
CLI gates every invocation on, and the squad-dir pointer that resolution walks up to find. Truncating
it does not cost a `sq sync`, it makes the squad unresolvable. It is outside §1's ordering rule
though: nothing in the index mirrors it, so there is no skew to direct.

Sequencing note: fsync is not required by the process-death model, and is included only to keep one
primitive rather than two. If bulk import (hundreds of files in one transaction) measures a real
regression, the sanctioned relief is to skip the fsync on the markdown side — **not** to defer the
renames to the end of the transaction, and **not** to reorder against the index commit.

A transaction that writes N markdown files is still not atomic across those N files. The rule
generalizes without change: every file the transaction touched is durable before the index commits,
so the skew stays one-sided and repair-safe for N files exactly as for one.

## 3. `sq check` reads without a lock, and confirms cross-source claims before reporting them

**No reader lock.** `check` remains lock-free. A shared reader lock (or a brief exclusive one) would
hold up every writer for the duration of a 0.5–2s scan; mutations acquire with a 10s timeout, so the
most frequently run read on the board — every agent runs this gate before handoff — would become a
source of *hard* write failures, and `sq check` run during a bulk import (one transaction spanning
hundreds of items) would block for the whole import or time out. Trading a false warning for a real
`filelock.Timeout` is a bad trade. Converting Layer 3 to a read/write lock would also mean
rewriting the lock discipline of the integrity core, and its interaction with Layers 1 and 2, for a
report that is stale the moment it is released anyway.

**Confirm pass instead.** Issues are partitioned by their inputs:

- **Single-source** — derived from one file's own text (marker damage, missing id, unwritten
  sub-entity body, over-long titles, status-banner prose). Reported as-is: they are exactly as true
  as the one read that produced them.
- **Cross-source** — any claim that compares the on-disk scan against the index snapshot: status
  drift, parent drift, and both directions of index/disk reconciliation. These are **candidates**,
  not findings. After the scan, and only if the candidate set is non-empty, re-load the index (one
  small read) and re-observe only the candidate items — the file's content where it exists, its
  absence where it does not, each at the path the freshly loaded index gives for that item, since an
  in-flight retype moves the file and a stale path would manufacture the very claim being confirmed.
  Then re-evaluate those same predicates against the fresh pair; only claims that still hold are
  reported.

Because a mutation commits both sides while holding the lock, a candidate produced by an in-flight
transaction resolves on the recheck, while a durable inconsistency reproduces on every recheck.
A clean board pays nothing: no candidates, no second pass.

Exactly **one** confirm round. A retry loop would not terminate under continuous mutation, and the
residual false positive requires an unlucky mutation in both the scan window *and* the confirm
window for the same item.

This makes every cross-source claim per-item by construction, which is a requirement on future
validators: a cross-source predicate must be evaluable for a single item id, or it cannot be
confirmed and does not belong in `check`.

**What `sq check` may claim.** It reports the board as of a point in time; it takes no lock, never
blocks a mutation, is never blocked by one, and never writes. A reported drift or reconciliation
error means a **real, durable** inconsistency — actionable, `sq repair` heals it. What it may *not*
claim is quiescence: "clean" means "no confirmed inconsistency was observed", not "the board is
consistent now". Where the two `updated_at` values order the pair, a confirmed drift may name the
direction — markdown-ahead is the expected repairable skew, index-ahead means the ordering rule was
violated or the failure was out of model. The clock is second-resolution and a mutation stamps both
sides from one value, so the two frequently do not order the pair; say nothing about direction then,
and do not reach for a second input to force an answer. Either way the level stays `warn`: forged
clocks (`--at`) make direction an informative detail, not a gate signal.

## 4. The active transaction is task-local and store-scoped, never an instance attribute

The live transaction context is published in a task-local binding (a `ContextVar` in
`_index/_store.py`), set **after** all three locks are held and the in-lock load has produced the
context, and released with the `set` token in the `finally` so the previous value is restored rather
than clobbered. The context carries its owning store's identity, and the logging entry point ignores
an ambient context belonging to a different store — required because a task-local binding is
process-wide where the old instance attribute was per-instance, and one process may serve two squads
(the observable-equivalence rule of ADR-534 §3) — a scenario a long-lived server or daemon process
makes routine rather than hypothetical.

Identity here is the `IndexStore` **instance**, not the resolved index path. The two differ
observably, because one process does hold two stores over the same squad directory (`repair`, tests),
and the instance is the faithful translation of the per-instance attribute being replaced: a log call
against a store with no open transaction stays the silent no-op it is today, instead of being routed
into an unrelated store's buffer and committed by that store.

The context is built from the load taken **inside** the lock. The pre-lock load that exists only to
construct the context and is then discarded goes away, which removes both the unlocked window that
made misattribution possible and a full index read per transaction.

Derived rule: this is the **only** ambient value the store may carry, its lifetime is exactly the
lock hold, and no per-transaction state may live on `IndexStore` instance attributes.

**Why task-local rather than an explicitly yielded handle.** ADR-534 §1 prefers explicit threading
below the CLI edge and sanctions a `ContextVar` at the ambient boundary; both readings forbid what
exists today, a shared mutable attribute with no isolation at all. Explicit threading means changing
what `transaction()` yields, and with it ~20 logging sites, ~30 transaction sites and the bulk
importer's direct-core calls — churn concentrated in the one module where churn is least welcome,
for a defect that is currently unreachable. The task-local binding satisfies the binding content of
ADR-249 and ADR-534: task-local value, no shared module name, no cross-request or cross-squad
leakage, one long-lived process observably identical to N fresh ones. **Promotion trigger:** the
first time the transaction API is revised for fan-out/batch mutation or for the server, the handle
becomes an explicit parameter and the ambient binding is deleted.

This is also not a `RequestContext` field. That type is a frozen bag of ambient *inputs* bound once
at the CLI edge for the whole request; a transaction context is shorter-lived than a request,
engine-internal, and mutated by appending to its reflog buffer.

# Consequences

**Contract.** Entirely internal. No CLI surface, flag, or output-format change; no frontmatter or
index field added, therefore no schema bump and no migration. Two observable behaviour changes worth
a changelog line: `sq check` no longer reports phantom drift or reconciliation errors (and no longer
exits 3) while another process is mutating the board; and an interrupted mutation now always leaves
the repairable skew rather than, in the worst case, a truncated item file.

**Audit obligation.** The ordering rule is only worth what its weakest call site is. Every mutation
core is checked against it, not just the status path: `remove_item(purge=True)` unlinks after the
commit and must move inside the transaction, and the same sync `Path.unlink` there should go through
the async helper the rest of the layer uses. `remove_item`'s default of de-indexing while leaving
the `.md` on disk is a separate question — it deliberately produces an on-disk-but-not-indexed file,
which `check` reports as an error — and is out of scope here.

**Documentation the rule lives in.** The `_index/_store.py` and `_itemfile.py` module docstrings
carry the skew-direction rule and the atomic-write primitive's contract, because that is where an
implementer reads before adding a mutation. One correction belongs there too: `transaction()`
currently documents "If the body raises, nothing is written", which is true only of the index —
markdown writes already made do stand, and that is by design under this decision.

**Testable acceptance shapes.** The crash window is reachable without killing a process: raise from
inside a transaction body after the markdown write and assert the index is unchanged, the file is
ahead, and `repair` converges on the file's state. Non-atomic markdown writes become structurally
impossible if the item-file layer exposes only the atomic primitive. The read model is testable by
committing a mutation between a scan and its confirm pass and asserting no issue is reported, and by
leaving a real drift on disk and asserting it is.

**Costs accepted.** A transaction is still not a single durability event, and never will be without
a journal — rejected below. `check` may do a second, small read pass when candidates exist. And
`sq repair` remains a required part of the recovery story rather than something the store makes
unnecessary; the decision is that repair is *sufficient* precisely because the skew is one-sided.

# Alternatives rejected

**Rename the markdown into place only after the index commit succeeds.** This inverts the skew into
the lossy direction: repair would revert the mutation or resurrect a removed item. Rejected on
correctness, not cost.

**A write-ahead journal, or a two-phase commit across both artifacts.** It would make a transaction
a single durability event, at the price of a third durable artifact that duplicates the source of
truth and needs its own recovery, replay, and crash reasoning — plus a startup replay path on every
`sq` invocation. Disproportionate for a tool whose worst case is already a bounded, one-sided,
always-repairable skew.

**Document the crash window and change nothing.** Rejected because the window's worst outcome is not
a drift but a truncated source-of-truth file — and an item silently dropped off the board with it —
and because a rule stated at one call site out of a dozen is not a rule.

**A shared/reader lock around load + scan in `check`.** Rejected: see §3. It serialises the board's
writers behind its longest and most frequent read, and buys snapshot isolation for a claim whose
only actionable content the confirm pass establishes far more cheaply.

**A generation/version counter in `.squads.json` so `check` can detect "the index moved during my
scan".** Rejected: it cannot be reconstructed from the markdown files, so it cannot live in the
index (invariant #1). Using the index file's mtime instead is legal but redundant — the confirm pass
already runs only when candidates exist.

**Move the pre-lock context assignment to just after Layer 1.** Narrows the window rather than
closing it: Layer 1 is per-event-loop, so two loops or two threads in one process still share the
attribute, and a shared attribute stays wrong on its own terms once a process serves more than one
squad.
<!-- sq:body:end -->

## Discussion

<!-- sq:discussion -->
- [2026-07-27T14:06:03Z] Robert Architect:
  - Settles all three drift/atomicity bugs as one seam: markdown-ahead skew + atomic .md replace (§1-2), lock-free check with a confirm pass on cross-source claims (§3), task-local store-scoped transaction handle (§4).
  - Two corrections to the reported causes: renaming the .md after the index commit is the lossy direction (repair would revert/resurrect), and every .md write is a truncate-in-place Path.write_text — the worst case in the crash window is a destroyed source-of-truth file, not just drift.
  - Purely internal; no schema bump, no CLI surface change.
- [2026-07-27T14:12:00Z] Pierre Chat:
  - Read and approved — the design holds, including the pushback on BUG-656's own proposed fix. Accepted; proceed to implementation.
- [2026-07-27T14:26:30Z] Olivia Lead:
  - Broken into four tasks, all Draft: TASK-664 write side (§1+§2, fixes BUG-656) — 6 subtasks; TASK-665 read side (§3, fixes BUG-655) — 4 subtasks; TASK-666 transaction handle (§4, fixes BUG-657) — 3 subtasks; TASK-667 rule-of-record + one atomic primitive instead of two — 2 subtasks.
  - Order: 664 and 666 in parallel (disjoint files — services/item-file layer vs `_index/_store.py`); 665 after 664; 667 after 664 and 666. No parent feature — bug-fix tasks hanging off the bugs via `fixes` and off this ADR via `implements`.
  - The truncation hazard §2 surfaces (truncate-in-place .md writes destroying the source of truth) is in TASK-664's scope; @qa files it separately.
- [2026-07-27T14:30:43Z] Robert Architect:
  - Amended in place with two rulings Olivia raised as gaps — clarifications inside the accepted decisions, no decision reversed.
  - `.squads.toml` is squad data (§2), NOT exempt: it must go through the atomic-replace primitive. `sq sync` re-stamps only its version field; nothing reconstructs active_backends, default_role, the gated schema_version, or the squad_dir pointer resolution walks up to find — truncating it does not cost a sync, it makes the squad unresolvable. It is outside §1's ordering rule, since nothing in the index mirrors it. Olivia's provisional exemption in TASK-664 is overruled.
  - Owning-store identity for the foreign-ctx guard (§4) is the `IndexStore` **instance**, not the resolved index path — confirming TASK-666 ST2. Two stores over one squad dir do coexist in a process (repair, tests); the instance keeps a log call on a store with no open transaction the silent no-op it is today, where path identity would route it into an unrelated store's buffer.
  - Also folded: the confirm input is now a fresh *observation* (content or absence) at the path the freshly loaded index gives, because an in-flight retype moves the file and a stale path manufactures the claim being confirmed; direction-naming is downgraded to optional with an explicit 'say nothing, and do not reach for a second input' when the second-resolution timestamps do not order the pair; and §1 gains a compliance clause — repad/renumber comply by ending in a full rebuild and must not be restructured to nest their renames in a transaction.
- [2026-07-27T14:45:25Z] Robert Architect:
  - Factual correction inside the accepted decision, no design change: the Context bullet on write atomicity claimed a truncated write could raise a bare yaml.YAMLError out of sq check. Wrong — withdrawn. `_FRONTMATTER_RE` needs a literal closing `---` line, so a prefix of a fully-serialized block either has no closer (the missing-`id` bucket) or contains the whole block and parses; malformed-but-closed frontmatter is unreachable from a single truncated write. Confirmed independently against the regex, and the ADR now states why rather than just dropping the claim.
  - The reader-visible consequence the bullet was arguing for is unchanged — it now rests on the two reproduced errors (no `id`, unclosed marker) instead of an unreproducible third.
  - Strengthened in the same edit: the loss is silent and terminal, not just unhealable. repair rebuilds from the markdown, so a destroyed file makes it drop the item from the index as missing — unreachable by show, absent from `sq list -a`, a corrupted orphan left on disk that no sq command can recover. That is the strongest argument §2 has and it now says so.
<!-- sq:discussion:end -->
