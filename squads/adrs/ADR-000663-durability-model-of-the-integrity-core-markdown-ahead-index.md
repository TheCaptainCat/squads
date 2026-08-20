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
- ADR-153
description: Markdown is always ahead or equal and the index commits last; every squad-data
  .md write is an atomic replace; sq check stays lock-free and confirms cross-source
  claims; the active transaction is task-local and store-scoped.
created_at: '2026-07-27T14:02:48Z'
updated_at: '2026-08-06T20:45:09Z'
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

Each is healed **losslessly** by `sq repair`: repair derives the index from the markdown, so a
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
  commit (as `update`'s pointer regen already does). Exempt from *ordering* only: nothing in the index
  mirrors them, so there is no skew to direct — §2 still governs how each one is written.
- **The reflog** — an append-only observability log, deliberately appended after `os.replace` under
  a never-raise contract. It is not source of truth and must stay where it is.
- **Re-derivable regions of an item `.md` the committing transaction did not mirror into the index** —
  the resolved-skill cache in a role's frontmatter and the generated `## Skills` region of its body,
  refreshed after the commit that changed a *skill*'s refs. This is the permitted skew, not the
  absence of one: the transaction never wrote these derived values to the index, so neither crash
  direction is index-ahead, and `sq sync` re-derives them from the ref graph, so the worst case is a
  stale cache. A post-commit item-`.md` write must meet both halves — a derived value the transaction
  did not mirror, and reproducible by `sq sync`. Both halves are a test of *ordering*: what a writer
  may put on disk after the commit. Which keys the guard then compares is the separate question
  settled under **What the guard compares** below — a comparison withheld there is governed by that
  clause, and is not this exemption being widened by a second writer.

**The healing has a condition, and the condition is enforced rather than assumed.** Repair must run
before anything next rewrites that item's frontmatter from index-derived state — a mutation core loads
the item from the index, applies its delta, and rewrites the whole frontmatter block, and `sq sync`'s
roster regen does the same. Unguarded, that silently replaces the surviving values and leaves nothing
on disk for repair to detect afterwards, so every such path is guarded. An interrupted mutation
therefore guarantees:

- **Unconditionally** — no truncated or partial file, and the item is never dropped from the board.
  Body content (prose, discussion, sub-entity bodies, markers) is never at risk here at all: a
  frontmatter rewrite preserves body bytes verbatim.
- **Until `sq repair` runs** — the interrupted mutation's frontmatter fields, sub-entity state
  included, since that lives in frontmatter. Nothing overwrites them silently: a path that would
  rewrite them from index-derived state refuses, or skips and reports. `sq check` names the item as
  confirmed drift (§3), and repair promotes the surviving values into the index for good.
- **At a stated cost** — that item is not mutable until repair runs. A drifted item blocks its own
  mutations, loudly, with a one-command remedy. The block is per-item; nothing spreads.

The obligation on the user is real and not a formality: `check`, then `repair`, then continue. The
guard that enforces it is part of this decision, and it is fail-closed detection rather than a merge:
merging on write would invent per-field precedence, and would apply values the workflow gate never
validated (a transition is checked against the index-loaded item).

**What the guard compares.** Not §3's drift predicate. That predicate is a board-wide advisory over
hundreds of items, deliberately narrow (`status`, `parent`) for cheap, high-signal reporting; a guard
built to it would miss description, assignee, labels, refs and sub-entity state, which is most of the
at-risk surface. The two are decoupled — §3's set is unchanged, and the guard's set follows from the
loss mechanism instead. Loss happens exactly where the pending write replaces an on-disk value the
mutation itself did not set, so the comparison is three-way, as in a version-control merge: the
frontmatter on disk against the frontmatter the index-loaded item would have serialized **before** the
delta was applied. Every key is in scope, and the mutation's own fields — including the `updated_at`
and session stamps every write sets — drop out structurally instead of being reasoned about. In the
normal case the two sides are identical, because the last successful mutation wrote both from one
item, so any inequality is evidence of a real skew rather than a heuristic.

Two consequences for whoever builds it. The base is captured in the pure half of a core, before the
delta is applied; deriving it from a reflog delta instead would tie the guard to a structure designed
for logging, not for describing a write. And the by-design divergences are a **category, not a list**,
spanning both sides of the comparison: the index side corrects at load (the legacy-severity
relocation, the counter and width fixups), and the file side corrects at parse (the pre-0.2
`extra.ref_kinds` map folded into inline `"ID:kind"` refs). Normalize rather than exclude — an excluded
field is a permanent blind spot, a normalized one still catches a real skew — and normalize once,
structurally, by putting both sides through the same serializer: compare
`Item.from_frontmatter(disk).to_frontmatter_dict()` against the base's `to_frontmatter_dict()`.
Measured against the model, that collapses all three named divergences — legacy `extra.severity`,
`extra.ref_kinds`, and a padded id, which is recomputed from prefix and sequence number — along with
key order and absent-versus-`None`. A future correction that does *not* collapse through the
round-trip is registered explicitly, on whichever side it lives, in the same change that introduces
it; otherwise it becomes a false refusal.

**A fabricated operand is not a value, and withholding its comparison is not a permitted skew.**
Registration under the clause above normally means normalizing. One shape cannot be normalized: a
field whose absent-value default is *invented* at load time rather than derived from the file — a
missing `created_at`/`updated_at` falls back to `clock.now()` so a legacy or hand-authored `.md`
loads at all. Putting both sides through the same serializer cannot collapse that, because the
invention is not a function of the file's bytes: the same file yields a different value on every
read, so the comparison reports a divergence on a key the file says *nothing* about, refuses that
item's every mutation for good, and points at a `sq repair` that structurally cannot clear it —
repair rebuilds the index from markdown and never writes markdown back. Registration therefore takes
the other form here: the key is dropped from the comparison, for that read. Four conditions bound
that form and all four are load-bearing. The disk operand must be **loader-fabricated** rather than
read from the file — there is no second value to disagree with, only an invention being compared
against a record, which is what makes this a withheld comparison rather than a permitted skew. The
fabrication must be **non-deterministic**, so the shared round trip genuinely cannot absorb it. The
drop must be conditioned on the **observed raw frontmatter, per read** — never on a key name, which
is what makes it strictly narrower than the ordering exemptions above rather than an extension of
them. And it must **self-extinguish**: every write seam persists the whole frontmatter, so the first
successful mutation writes the value in and restores the comparison permanently. It is not the blind
spot an exclusion would be — a timestamp the file *does* carry is compared like any other field, and
one it carries unparseably still fails at the load boundary. The key set is exhaustive by
construction, not by convention: any field that later gains an invented load-time default registers
here in the same change, under the rule above.

**What withholding obliges in return.** A field absent from an item `.md` is a defect in the source
of truth, not a legitimate state, so declining to compare it must not become declining to notice it,
and must not license inventing one. Two duties follow and neither is optional. Something must keep
reporting the gap where the gap actually is — `sq check` warns on the file (§3), and says the heal
will write what the index holds rather than promising the real value. And no path may commit a
fabricated value over a known one: a rebuild carries the previously-indexed value forward for a key
the scanned file has no value for, in the same posture it already takes for an unreadable file, and
fabricates nothing where it has nothing to carry. Both together are what keep invariant #1 intact
under a broken file. Skip the first and the defect is invisible; skip the second and the invented
instant is committed to the index, a later mutation heals the markdown from it, and the item's real
creation time is unrecoverable from either artifact with nothing having reported it at any step.

**The roster regen path** — `sq sync` rewriting a role's or skill's frontmatter from the index — shares
the loss but not the response: it leaves the drifted item's file untouched, names it in the output with
the `sq repair` pointer, and regenerates everything else. The invariant is identical (never silently
overwrite an ahead-of-index value); the response scales with the operation. Refusing is proportionate
when one item's mutation *is* the operation, whereas `sync` is bulk regeneration of derived state and
is itself what an operator reaches for when generated files are wrong — aborting the run would block
the remedy over a condition `sync` did not cause. Skipping leaves the surviving content in place and
defers only regeneration, which is stale-cache territory rather than loss. The exit status stays 0: the
sync did what it is for, and the drifted item already has a dedicated reporter in `sq check`, which
fails on it. A verify/strict mode is where a non-zero exit for stale generated state would belong.

**Batch mutation is a third shape**, and the answer is neither of the first two: the check runs
*before* the batch, never inside it. Bulk import applies every event inside one transaction, and §1's
own ordering rule means a raise part-way through leaves the markdown writes of everything already
applied standing — so a mid-flight refusal turns one drifted item into a partially applied import,
which is worse than the overwrite the guard exists to prevent. The importer is already validate-first
for exactly this reason: its pre-pass simulates every event against a throwaway copy of the index,
collects every issue instead of stopping at the first, and applies only on a clean plan, so an
apply-time failure can only be I/O. The guard belongs in that pre-pass as one more collected issue,
evaluated **once per targeted pre-existing item** rather than per event — after that item's first
event, divergence from disk is the import's own doing. Creates are out of scope: there is no prior
file to diverge from. The bulk retype and rename-status paths take the same shape: their affected set
is known up front, so they pre-flight it and refuse before the first write, and their file-rollback
path stays what it is — a crash safety net, not the guard's mechanism.

`repad` and `renumber` fall outside the guard, and not by exemption — their ordering-side compliance
is settled above by ending in a rebuild; whether the guard reaches them is the separate question. It
does not: the guard attaches to index-derived frontmatter substitution, not to file writes in general. `repad` renames files and
leaves their bytes untouched; `renumber` rewrites id strings inside the files' own content. Neither
sources a value from the index, so neither can revert a skew — and a guard placed there would
false-refuse on precisely the id-width divergence `repad` creates.

## 2. Per-file atomicity on the markdown side

Every write to squad **data** (item `.md` files, board notices, memory entries, `.squads.toml`) goes
through one
atomic-replace primitive: write a temp file in the same directory, flush, fsync, `os.replace`, all
in a single thread hop with no `await` between fsync and rename — the shape `_atomic_write` already
uses for the index. Consequences: a killed process can no longer truncate the source of truth, and
no reader can ever observe a partially written item file. Regenerable artifacts stay on the plain
write, but the exemption reaches only what sq can **wholly** reproduce, where losing the file costs a
`sq sync` and nothing else. A whole-file rewrite of a file sq only partly owns does not qualify — a
managed region injected into an adopter's `CLAUDE.md`, a provenance stamp refreshed inside a
hand-authored override — because the write truncates content sq cannot regenerate. Those take the
primitive; the plain write is for files sq owns end to end.

`.squads.toml` is squad data, not a regenerable artifact. `sq sync` only re-stamps its version
field; nothing reconstructs the rest — the active backends, the default role, the schema version the
CLI gates every invocation on, and the squad-dir pointer that resolution walks up to find. Truncating
it does not cost a `sq sync`, it makes the squad unresolvable. It is outside §1's ordering rule
though: nothing in the index mirrors it, so there is no skew to direct.

Migration runners are not exempt in principle — every write of squad data is subject to this rule, and
new migration code uses the primitive. The already-shipped runners are frozen historical code and are
not rewritten for it, but the reason is that a migration is one-shot and operator-driven and the
migration runbook puts a clean version-control rollback point immediately before it. It is *not* that
repair reconciles the surviving state: repair reconciles an ordering skew and can do nothing about a
truncated file, which is this decision's whole premise. A migration is also the widest write window in
the product, since it rewrites every item file in one pass.

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
error means a **real, durable** inconsistency — actionable, `sq repair` heals it, and the message says
to repair before mutating that item again, since until that happens the item's own mutations refuse
(§1). What it may *not* claim is quiescence: "clean" means "no confirmed inconsistency was observed", not "the board is
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

Identity here is the `IndexStore` **instance**, not the resolved index path. The two differ observably,
because one process does hold two stores over the same squad directory (`repair`, tests), and the
instance is the fail-closed choice: a log call against a store with no open transaction stays the
silent no-op it is today, instead of being routed into an unrelated store's buffer and committed by
that store.

One case is a genuine behaviour change rather than a translation of the attribute being replaced, and
should not be described as one. That attribute was per-store by construction, so with store A's
transaction open and store B's nested inside it, A's log call still found A's own buffer. A single
task-local slot cannot: while B's binding occupies it, A's log call is discarded silently. Identity is
not what costs that — path identity would misattribute A's entries into B's buffer and commit them
there, which is worse — the single slot is, and it fails closed by losing a reflog line rather than
open by committing a wrong one. No live call path opens one store's transaction inside another's, so
this is unreachable today; what would make it reachable is exactly what the promotion trigger below
names — a second store in flight on one task, through fan-out, batch, or the server — and a per-store
mapping is the answer on that day, not this one.

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

**Contract.** No frontmatter or index field is added, therefore no schema bump and no migration; no
new CLI flag. Three observable behaviour changes worth a changelog line: `sq check` no longer reports
phantom drift or reconciliation errors (and no longer exits 3) while another process is mutating the
board; an interrupted mutation leaves the repairable skew rather than, in the worst case, a truncated
item file, and the surviving values are then preserved until `sq repair` runs rather than being
overwritten by the next write; and — the cost of that, user-visible and therefore stated plainly — a
mutation over an unrepaired skew refuses with a `sq repair` pointer, while `sq sync` reports a skipped
roster item instead of overwriting it. The adopter-facing line claims exactly those and nothing wider.

**Audit obligation.** The ordering rule is worth what its weakest call site is, so every mutation core
is checked against it, not only the status path — including the cores that unlink rather than write,
where the removal belongs inside the transaction like any other markdown-side write, and goes through
the same async helpers as the rest of the layer. De-indexing an item while deliberately leaving its
`.md` on disk is a separate question and out of scope here: it produces an on-disk-but-not-indexed
file, which `check` reports as an error.

**Documentation the rule lives in.** The `_index/_store.py` and `_itemfile.py` module docstrings carry
the skew-direction rule and the atomic-write primitive's contract, because that is where an
implementer reads before adding a mutation. They also state the limit of transactional rollback: when
a body raises, nothing is written *to the index*, while markdown writes already made stand — by
design, per §1.

**Testable acceptance shapes.** The crash window is reachable without killing a process: raise from
inside a transaction body after the markdown write and assert the index is unchanged, the file is
ahead, and `repair` converges on the file's state. Non-atomic markdown writes become structurally
impossible only where every writer of an item file goes through the item-file layer and that layer
exposes only the atomic primitive; a backend or migration that writes an item file directly is outside
that guarantee and carries its own coverage. The read model is testable by
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
- [2026-07-27T15:12:51Z] Pierre Chat:
  - This round ships in 0.12.2.
- [2026-07-27T16:09:35Z] Robert Architect:
  - F4 ruling: a genuine gap in §1's stated guarantee, not in its choice of direction — acceptable to ship with the claim narrowed, and not a release blocker. §1 amended: healing is conditional on repair running before that item's next index-derived frontmatter write (mutation cores rewrite the whole block from the index-loaded item; sq sync's roster regen does the same), with the guarantee split into what holds unconditionally (no truncation, item never dropped, body bytes never at risk), what holds until that next write (the interrupted mutation's frontmatter fields, sub-entity state included), and what is not guaranteed at all.
  - Verified the mechanism directly: replace_frontmatter substitutes the whole frontmatter block from the index-derived item and preserves body bytes, so the loss surface is exactly frontmatter — per item, non-spreading.
  - Direction stays correct, so no reversal: index-ahead loses at repair time unconditionally, markdown-ahead only if the user keeps mutating without repairing. F4 is also not a regression — pre-fix behaviour was the same plus truncation — so holding 0.12.2 would leave a high-severity destruction defect open to fix a medium one.
  - The gap closes later, in a minor, not here: before rewriting frontmatter a mutation core compares §3's drift-predicate field set against the frontmatter it already reads and refuses with a pointer to sq repair. Fail-closed detection, NOT a merge — merging invents per-field precedence, applies values the workflow gate never validated, and breaks on divergences that exist by design (legacy severity backfill, id width after repad). It also changes when a mutation refuses, which is not patch-release behaviour.
  - Patch-safe now: the drift message tells the reader to repair before mutating that item again (§3), and the changelog line must claim the truncation is gone and the survivor repairable — not that an interrupted mutation is durable across continued use.
  - F5 folded: migration runners are not exempt in principle (new migration code uses the primitive); the shipped runners stay frozen because a migration is one-shot, operator-driven and preceded by the runbook's version-control rollback point — explicitly not because repair reconciles it, which covers ordering and can do nothing about a truncated file.
  - F6 folded as a third §1 exemption: re-derivable regions of an item .md the committing transaction did not mirror into the index (the role's resolved-skill cache and its generated Skills region). Named as the permitted skew rather than an absence of one, with both conditions pinned — derived value the transaction did not mirror, and reproducible by sq sync.
- [2026-07-27T16:17:32Z] Robert Architect:
  - Comparison-set ruling: none of the three as framed — the guard is DECOUPLED from §3's predicate, and its set follows from the loss mechanism. My earlier 'compare §3's drift-predicate field set' was wrong; verified _drift_issues covers only status and parent, so that guard would have missed F4's own description case. §3's set is unchanged (board-wide advisory over hundreds of items, narrow on purpose); widening it would multiply confirm candidates for no gain in the gate's actionable content.
  - The guard's comparison is three-way, as in a VCS merge: on-disk frontmatter vs the frontmatter the index-loaded item would have serialized BEFORE the delta. Every key in scope; the mutation's own fields (plus the updated_at/session stamps) drop out structurally rather than by judgement. In the normal case the two sides are byte-identical because the last successful mutation wrote both from one item — so any inequality is evidence, not a heuristic. This is option 3's shape with the exclusion defined by provenance instead of enumeration.
  - Two implementation constraints, both in the body: capture the base in the pure half of the core (not from a reflog delta — that structure describes logging, not a write); and treat the by-design divergences as a category — the corrections load() applies in memory and lets reach disk on the next write — normalizing the on-disk side where a normalization exists rather than excluding the field, since an exclusion is a permanent blind spot. Any future load-time in-memory correction must be registered there in the same change.
  - Roster regen ruling: skip and report, never refuse the run. Same invariant, response scaled to the operation — sync is bulk regeneration and is itself the operator's remedy for wrong generated files, so aborting it blocks the fix over a condition it did not cause; a skip preserves the surviving content and defers only regeneration (stale cache, not loss). Exit stays 0 — sq check is the dedicated reporter and already fails on that item; a verify/strict mode is where non-zero for stale generated state would belong.
  - Neither ruling changes what 0.12.2 can claim: both are 0.13 remedies and the claim stands where the F4 narrowing left it — truncation gone, survivor repairable, no durability claim across continued use without repair. F4 does not stay substantially open under this criterion: it covers description and sub-entity state, so option 1 was not the answer.
- [2026-07-27T20:36:26Z] Robert Architect:
  - Guard pulled into 0.12.2 (op-pierre's call, recorded on TASK-672): §1 amended for tense and scope. The 'closing it is a later change' sentence is gone; the bound now reads as enforced rather than described — surviving frontmatter is preserved UNTIL sq repair runs, with the cost stated plainly (a drifted item blocks its own mutations until repaired, per-item, one-command remedy).
  - Bulk-mutation ruling: the check runs BEFORE the batch, never inside it. A mid-flight raise is the worst of the three options — §1's own ordering rule means the markdown writes of everything already applied stand, so one drifted item yields a partially applied import. Verified against _import.py: the importer is already validate-first (the pre-pass simulates every event on a throwaway index copy, collects every issue rather than stopping at the first, and applies only on a clean plan — its docstring pins 'an apply-time failure can only be I/O'). The guard is one more collected pre-pass issue, evaluated ONCE PER TARGETED PRE-EXISTING ITEM, not per event: after that item's first event, divergence from disk is the import's own doing. Creates are out of scope. Bulk retype/rename-status: same shape, pre-flight the known affected set and refuse before the first write; _rollback_files stays a crash safety net, not the guard's mechanism.
  - repad/renumber are outside the guard, and not by exemption — the guard attaches to index-derived frontmatter substitution, not to file writes in general. repad renames files and leaves bytes untouched; renumber rewrites id strings inside the files' own content. Neither sources a value from the index, so neither can revert a skew, and a guard there would false-refuse on exactly the id-width divergence repad creates.
  - Correction accepted on the divergence category: it spans BOTH correction sites, not just load() — the index side corrects at load (legacy severity, counter/width fixups), the file side at parse (pre-0.2 extra.ref_kinds folded into inline refs). The registration rule now names both.
  - Round-trip default sanctioned, and measured rather than assumed: comparing Item.from_frontmatter(disk).to_frontmatter_dict() against the base's to_frontmatter_dict() collapses legacy extra.severity, extra.ref_kinds, key order, absent-vs-None AND a padded id (recomputed from prefix + sequence_id) — I ran all four through the real model. Olivia's caveat about id width does not bite. Note  is a from_frontmatter kwarg, so it collapses by construction if the guard passes the item's own path.
- [2026-07-27T20:36:42Z] Robert Architect:
  - Typo repair on the line above: the word dropped by a shell quoting slip is "path" — the path field is a from_frontmatter keyword argument, so it collapses by construction provided the guard passes the item own path.
- [2026-07-27T21:07:47Z] Robert Architect:
  - F13 accepted, and verified against both sides of 13888b8 rather than the summary. Old: _current_ctx was per-instance, so with store A's transaction open and B's nested inside, A._log() read A._current_ctx and buffered correctly. New: one task-local slot, so _transaction_ctx_for(A) sees active.store is B and returns None — A's entry is discarded. That is a behaviour change, not a translation; §4 corrected.
  - Precision worth keeping: identity is not what costs the nested case — path identity would misattribute A's entries into B's buffer and commit them there, which is worse. The single slot costs it, and it fails closed (a lost reflog line) rather than open. Instance identity remains the right choice; the wording 'faithful translation' was mine and over-generalized from the no-open-transaction case, which it does describe correctly. Unreachable today (no live path opens one store's transaction inside another's); the existing promotion trigger already names what would make it reachable, and a per-store mapping is the answer then, not now.
  - Same wrong phrase is in the code: _transaction_ctx_for's docstring in _index/_store.py carries 'instance identity is the faithful translation of the per-instance attribute this replaces'. I cannot touch src — worth folding into whoever fixes F13 so the record and the code agree.
- [2026-07-27T21:11:43Z] Robert Architect:
  - Coherence pass, no new decisions — five fixes plus one found while moving blocks.
  - Rule errors first. §2's exemption premise was falsified by F3 and would have contradicted the shipped fix: the exemption now reaches only what sq can WHOLLY reproduce, and a whole-file rewrite of a file sq partly owns (a managed region in an adopter's CLAUDE.md, a stamp inside a hand-authored override) takes the primitive. The acceptance claim F1 disproved is qualified: structural impossibility holds only where every writer of an item file goes through the item-file layer; a backend or migration writing one directly is outside that guarantee and carries its own coverage.
  - §1 reordered so the justification precedes the machinery: rule, permitted-state table, healing, why the inverse direction is forbidden, what compliance means, exemptions, then the guard. Pure block move, no wording changed.
  - Audit obligation and the documentation paragraph restated as standing rules rather than pending work — the obligation without the status, so the record stops reading as a to-do list. repad/renumber now say explicitly that their ordering-side compliance is settled in §1 and the guard question is separate.
  - Two more found in the pass: §3's drift message still explained itself by the pre-guard framing ('the healing window closes on that item's next write') — corrected to 'until then the item's own mutations refuse'; and §1's regenerable-artifacts bullet now says it exempts ordering only, so nobody reads it as blanket permission to use the plain writer that §2 forbids.
- [2026-08-06T20:45:09Z] Robert Architect:
  - Ruling on REV-736 F42 (the absent-timestamp exclusion added by TASK-737 ST1): it is **within** this decision as written, but under a different clause than the finding measured it against. §1's three-item exempt list is a test of *ordering* — what a writer may put on disk after the commit — and `PERMITTED_EXTRA_SKEW` is its guard-side consequence. `INVENTED_WHEN_ABSENT` meets neither half of that test and was never meant to. It belongs under **What the guard compares**, whose registration clause already required that a correction which does not collapse through the shared round trip be registered explicitly in the change that introduces it, "otherwise it becomes a false refusal" — it was not registered, and it became precisely that false refusal.
  - Paul's distinction is real and is now a rule rather than a one-off ruling: *permitting a skew* means both operands are real and legitimately differ; *withholding a comparison* means the disk operand was fabricated by the loader, so there is no second value to disagree with — only an invention being compared against a record. §1 amended in place today with that clause, bounded by four load-bearing conditions: loader-fabricated operand, non-deterministic (so the round trip genuinely cannot absorb it), conditioned on the observed raw frontmatter per read rather than on a key name, and self-extinguishing at the first successful write. That per-read condition is what makes it strictly narrower than the ordering exemptions beside it, not a widening of them. Standing obligation carried over: any field that later gains an invented load-time default registers here in the same change.
  - A second clause landed with it, because the withholding is only sound in company. It obliges two things: keep reporting the gap where the gap is (`sq check`'s warning on the file), and never commit a fabricated value over a known one (the rebuild's carry-forward of the previously-indexed timestamp). Skip the first and the defect is invisible; skip the second and the invented instant reaches the index, a later mutation heals the markdown from it, and the item's real creation time is unrecoverable from either artifact with nothing having reported it at any step. That, not the refusal, is the invariant #1 failure worth guarding.
  - No `supersedes` and no `related` edge: this narrows no other decision, it clarifies this one in place, so the record is the amended §1 plus this comment. **No code change** — the mechanism as it stands, together with `_carry_forward_indexed_timestamps` on the rebuild and the `sq check` warning, satisfies all four bounds and both obligations. F42 marked Fixed against the clarification.
<!-- sq:discussion:end -->
