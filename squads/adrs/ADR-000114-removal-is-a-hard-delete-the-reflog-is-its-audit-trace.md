---
id: ADR-114
sequence_id: 114
type: decision
title: Removal is a hard delete; the reflog is its audit trace
status: Accepted
author: architect
refs:
- FEAT-23
- TASK-111
- FEAT-24
- ADR-104
description: sq remove hard-deletes (file + index entry) in one transaction, preserving
  the counter high-water mark so the freed number is never reissued; forced removal
  severs incoming refs so sq check stays clean; the removal's audit trace is a single
  reflog line (FEAT-000024), not an index tombstone.
created_at: '2026-06-15T08:24:46Z'
updated_at: '2026-06-15T08:25:54Z'
---
<!-- sq:body -->
## Context

FEAT-23 introduces a first-class `sq <type> <n> remove`. Today the only way to take an item off
the books is manual file surgery plus hand-editing `.squads.json` — we watched that go wrong live
(2026-06-10: two manual surgeries, one **reused** sequence number, no guard rails — BUG-22).
Four design questions block implementation (TASK-111) and must be settled here before any code.

The decision is constrained by **Invariant 1**: `.squads.json` is a *rebuildable index* — `sq repair`
must reconstruct it from the `.md` corpus alone, so nothing durable may live in the index without an
on-disk source of truth. ADR-104 already carved the only permitted exception: squad-wide
format/allocation parameters (counter, padding) carried as a corpus-derived **floor**. A removal
trace stored *only* in the index would be neither per-item frontmatter nor a format floor — it would
break the invariant outright (repair would erase it).

Concurrently, FEAT-24 (TASK-112) adds an **append-only reflog** at `<squad>/.reflog.jsonl`,
written *inside* `IndexStore.transaction()`, one JSONL line per mutating operation (actor, op,
target, before→after delta). Its US2 explicitly names "removals ... explainable from the squad
directory alone" and states the reflog "is the trace mechanism FEAT-23's audit question asks for,
generalized." The two features must not invent competing audit mechanisms. This ADR reconciles them.

## Decision

### 1. Delete semantics — **hard delete**

`sq remove` **hard-deletes**: it unlinks the `.md` file and deletes the index entry
(`del db.items[seq]`) in one `store.transaction()`. There is **no** `Archived` soft-state.

We hold the line the feature and tech lead asked for:

- **Cancel** = work that was genuinely considered and then dropped. It stays on the books with a
  terminal `Cancelled` status — it is part of the project's real history and should remain
  greppable, linkable, and visible in `tree`/`list`.
- **Remove** = an item that *should never have existed*: a mis-creation, a test artifact, a
  rolled-back decision. It leaves the corpus entirely.

An `Archived` soft-state would blur exactly this line — it would give "should-never-have-existed"
items a permanent home in the corpus, which is what `Cancelled` already does for a *different*
intent. It would also add a state to every type's workflow, a filter rule to every read/check path,
and a "what does Archived mean for a decision vs. a task" question — cost with no payoff the
`Cancelled`/`remove` split doesn't already cover. Hard delete keeps the model honest: after a
removal the item is simply gone, and the only residue is a number gap (point 4) plus a history line
(point 2).

### 2. Audit trace — **the reflog line is the trace; no index tombstone, no separate log**

The removal's audit trace is **one `remove` line in the FEAT-24 reflog** (`<squad>/.reflog.jsonl`),
recording timestamp, actor, op=`remove`, the removed ID, and a compact snapshot of the gone item
(at least: type, title, status, and the count/list of severed refs). It is **not**:

- a tombstone entry in `.squads.json` — that would violate Invariant 1 (repair, which rebuilds from
  the `.md` corpus, has no removed `.md` to rebuild a tombstone from, so it would silently vanish);
- a tombstone `.md` file left behind — that re-pollutes the corpus the hard delete just cleaned, and
  raises its own "is a tombstone an item? does it have an ID? does `check` see it?" questions;
- a separate removal-only log — that duplicates the reflog and gives forensics two files to reconcile.

The reflog is the **right home by construction**: it already lives on disk in the squad directory, is
already append-only, is already written inside the same transaction as the mutation, and is
**explicitly declared NOT a source of truth** (FEAT-24 scope) — a missing/truncated reflog is
never an error and the index never consults it for state. That is exactly the property a removal
trace needs: it explains a number gap *without* the index depending on it. Invariant 1 is untouched —
`sq repair` rebuilds the index from `.md` files and neither reads nor needs the reflog.

**Composition contract with FEAT-24 (binding on both tasks):**

- `remove` is one of the mutating ops the reflog records; it gets **no bespoke audit code of its
  own**. TASK-111 must *not* add a tombstone field to `SquadsDB`, a tombstone file, or a removal
  log. Its sole audit obligation is to ensure the removal runs through the transaction seam carrying
  the op identity (`op=remove`) and the gone-item snapshot in its delta, so the reflog writer
  (TASK-112) emits a reconstructable line.
- **Sequencing.** If TASK-111 lands before the reflog seam (TASK-112) exists, removal ships
  with its terminal-output trace (the confirm + printed summary) and the in-transaction op/delta
  capture **stubbed at the call site** (the data is assembled; the writer is a no-op until 112 wires
  it). Removal must **not** grow a stopgap tombstone to bridge the gap — a stopgap would become a
  second mechanism we then have to remove. The acceptance bar "removal is traceable after the fact"
  is satisfied by the reflog; until the reflog seam lands, US3's *durable* trace is provisionally met
  by git history of the deleted file (the squad is version-controlled), and the queryable-trace
  acceptance is **carried by FEAT-24**, not re-implemented here.

### 3. Ref behaviour — **forced removal severs incoming refs; default refuses**

Confirmed and specified:

- **Default**: `remove` **refuses** when the target has incoming refs (computed by inversion via
  `SquadsDB.backrefs` / `RefsMixin.refs_in`) or children (items whose `parent == target.id`),
  listing every offender so the operator can act. No silent danglers, ever.
- **`--force`**: severs each incoming ref by removing the matching entry from the *referrer's*
  frontmatter — reusing the width-tolerant `_id_matches` sever logic already in
  `_services/_refs.py::rm_ref` (match by `(prefix, seq)`, persist via `update_frontmatter`),
  performed inside the **same transaction** as the delete so a crash leaves neither a half-severed
  referrer nor a dangling ref. After any removal (forced or not) **`sq check` is clean**: no
  "dangling ref" warnings, no "dangling parent" errors.
- **Children are NOT auto-reparented.** `--force` severs refs but refuses while children remain;
  the operator must re-parent (or remove) children first. Auto-reparenting guesses intent and can
  silently restructure the tree — out of scope and out of character for a destructive verb.

`backrefs`/`refs_in` are computed by inversion and never stored (Invariant 4), so severing on the
referrer side is the *only* place ref state changes — there is no backref index to update.

### 4. ID reuse — **the counter high-water mark is preserved; a gap is sanctioned**

Confirmed. Removal deletes `db.items[seq]` but **never touches `db.counter`**. BUG-22 already
made the counter monotonic, and the machinery composes for free:

- `allocate_id` only ever *bumps* `counter`; it never recomputes from the live items, so a deletion
  cannot lower it.
- `IndexStore.load` raises the counter to `max(item sequence_ids)` in memory but **never lowers it** —
  a removed (lower) seq simply isn't a max, so load leaves the high-water mark alone.
- `repair` sets `db.counter = max(previous_counter, max_n)` — the previously-stored counter is the
  floor (ADR-104), so even repairing a squad whose highest-numbered item was just removed keeps
  the counter at its old value. The freed number is **never reissued**.

Therefore a **number gap is a first-class, sanctioned state**, not corruption: it means "an item with
that sequence number existed and was removed." `check`/`repair` must treat gaps as normal (they
already do — nothing asserts contiguity). The reflog `remove` line is what *explains* a given gap
when someone audits later (point 2); the gap itself is self-consistent without it.

## Consequences

- TASK-111 (`sq remove` for work items) is **unblocked** with a settled contract: hard delete in
  one transaction, refuse-then-`--force`-sever for refs, refuse on children, counter untouched,
  trace = reflog line (no tombstone). Confirmation UX (interactive confirm unless `--yes`) is a UX
  detail, not a design gate, and proceeds as scoped.
- FEAT-24 owns the durable, queryable removal trace; `remove` only feeds it op identity + delta
  through the transaction seam. The two features **compose**; neither duplicates the other.
- **Deferred onto FEAT-13 (the 1.0 contract).** The reflog `remove` line — the fields a removal
  records (type, title, status, severed-ref list) and that a sequence-number **gap is a sanctioned,
  documented state a reader may rely on** — is a public, machine-readable surface. Its schema and
  stability tier must be stated in the 1.0 contract doc *as part of FEAT-13's reflog-schema
  promise* (FEAT-24 US3 already routes the reflog schema there). The contract must state: gaps
  are normal; numbers are never reissued; a removal is explained by the reflog, not by the index.
- Invariant 1 is preserved and re-affirmed: nothing about removal stores un-rebuildable state in
  `.squads.json`. The deletion *removes* index state; the trace lives in the (non-authoritative)
  reflog on disk.

## Status

Accepted.
<!-- sq:body:end -->

## Discussion

<!-- sq:discussion -->
<!-- sq:discussion:end -->
