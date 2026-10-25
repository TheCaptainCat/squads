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
updated_at: '2026-10-25T21:36:40Z'
---
<!-- sq:body -->
## Context

`sq <type> <n> remove` takes an item off the books. Without it, the only way to do so is manual
file surgery plus hand-editing `.squads.json`, which goes wrong in practice (two manual surgeries,
one **reused** sequence number, no guard rails — BUG-22). Four design questions decide its shape:
delete semantics, the audit trace, ref behaviour, and ID reuse.

The decision is constrained by **Invariant 1**: `.squads.json` is a *rebuildable index* — `sq repair`
must reconstruct it from the `.md` corpus alone, so nothing durable may live in the index without an
on-disk source of truth. ADR-104 carves the only permitted exception: squad-wide format/allocation
parameters (counter, padding) carried as a corpus-derived **floor**. A removal trace stored *only*
in the index would be neither per-item frontmatter nor a format floor — it would break the invariant
outright (repair would erase it).

The operation reflog (FEAT-24, ADR-117) is an append-only `<squad>/.reflog.jsonl`, one JSONL line
per mutating operation (actor, op, target, before→after delta), written under the index
transaction's lock. It already promises that removals are explainable from the squad directory
alone, so removal and the reflog must not invent competing audit mechanisms.

## Decision

### 1. Delete semantics — **hard delete**

`sq remove` **hard-deletes**: it unlinks the `.md` file and deletes the index entry
(`del db.items[seq]`) in one `store.transaction()`. There is **no** `Archived` soft-state for work
items.

- **Cancel** = work that was genuinely considered and then dropped. It stays on the books with its
  type's cancelled status — it is part of the project's real history and should remain greppable,
  linkable, and visible in `tree`/`list`.
- **Remove** = an item that *should never have existed*: a mis-creation, a test artifact, a
  rolled-back decision. It leaves the corpus entirely.

An `Archived` soft-state would blur exactly this line — it would give "should-never-have-existed"
items a permanent home in the corpus, which is what cancelling already does for a *different*
intent. It would also add a state to every type's workflow, a filter rule to every read/check path,
and a "what does Archived mean for a decision vs. a task" question — cost with no payoff the
cancel/remove split doesn't already cover. Hard delete keeps the model honest: after a removal the
item is simply gone, and the only residue is a number gap (point 4) plus a history line (point 2).

### 2. Audit trace — **the reflog line is the trace; no index tombstone, no separate log**

The removal's audit trace is **one `remove` line in the reflog**, recording timestamp, actor,
op=`remove`, the removed ID, and a snapshot of the gone item: its type, title, status and the list of
severed refs. It is **not**:

- a tombstone entry in `.squads.json` — that would violate Invariant 1 (repair, which rebuilds from
  the `.md` corpus, has no removed `.md` to rebuild a tombstone from, so it would silently vanish);
- a tombstone `.md` file left behind — that re-pollutes the corpus the hard delete just cleaned, and
  raises its own "is a tombstone an item? does it have an ID? does `check` see it?" questions;
- a separate removal-only log — that duplicates the reflog and gives forensics two files to reconcile.

The reflog is the **right home by construction**: it lives on disk in the squad directory, is
append-only, is written under the same transaction lock as the mutation, and is **explicitly not a
source of truth** — a missing or truncated reflog is never an error and the index never consults it
for state. That is exactly the property a removal trace needs: it explains a number gap *without*
the index depending on it. `sq repair` rebuilds the index from `.md` files and neither reads nor
needs the reflog.

`remove` is one of the mutating ops the reflog records and has **no bespoke audit code of its own**:
no tombstone field on `SquadsDB`, no tombstone file, no removal log. Its sole audit obligation is to
run through the transaction seam carrying the op identity and the gone-item snapshot in its delta.

### 3. Ref behaviour — **forced removal severs incoming refs; default refuses**

- **Default**: `remove` **refuses** when the target has incoming refs (computed by inversion via
  `SquadsDB.backrefs` / `refs_in`) or children (items whose `parent == target.id`), listing every
  offender so the operator can act. No silent danglers, ever.
- **`--force`**: severs each incoming ref by removing the matching entry from the *referrer's*
  frontmatter — matching by (prefix, sequence number) through `ref_id_matches`, so refs written at an
  older padding width are found — inside the **same transaction** as the delete, so a crash leaves
  neither a half-severed referrer nor a dangling ref. After any removal (forced or not) **`sq check`
  is clean**: no dangling-ref warnings, no dangling-parent errors.
- **Children are not auto-reparented.** `--force` severs refs but refuses while children remain;
  the operator must re-parent (or remove) children first. Auto-reparenting guesses intent and can
  silently restructure the tree — out of character for a destructive verb.

`backrefs`/`refs_in` are computed by inversion and never stored (Invariant 4), so severing on the
referrer side is the *only* place ref state changes — there is no backref index to update.

### 4. ID reuse — **the counter high-water mark is preserved; a gap is sanctioned**

Removal deletes `db.items[seq]` but **never touches `db.counter`**, and the machinery composes:

- `allocate_id` only ever *bumps* `counter`; it never recomputes from the live items, so a deletion
  cannot lower it.
- `IndexStore.load` raises the counter to `max(item sequence_ids)` in memory but **never lowers it** —
  a removed (lower) seq simply isn't a max, so load leaves the high-water mark alone.
- `repair` sets `db.counter = max(previous_counter, max_n)` — the previously-stored counter is the
  floor (ADR-104), so even repairing a squad whose highest-numbered item was just removed keeps
  the counter at its old value. The freed number is **never reissued**.

Therefore a **number gap is a first-class, sanctioned state**, not corruption: it means "an item with
that sequence number existed and was removed." `check`/`repair` treat gaps as normal — nothing
asserts contiguity. The reflog `remove` line is what *explains* a given gap when someone audits
later (point 2); the gap itself is self-consistent without it.

## Consequences

- **One contract for removal:** hard delete in one transaction, refuse-then-`--force`-sever for
  refs, refuse on children, counter untouched, trace = reflog line (no tombstone). Confirmation is
  interactive unless `--yes`.
- **The reflog owns the durable, queryable removal trace**; `remove` only feeds it op identity and
  delta through the transaction seam. Neither duplicates the other.
- **The 1.0 contract states it.** The reflog `remove` line — the fields a removal records (type,
  title, status, severed refs) — and the guarantees that a sequence-number **gap is a sanctioned
  state a reader may rely on**, that numbers are never reissued, and that a removal is explained by
  the reflog rather than the index, are part of the stability contract's reflog promise.
- **Invariant 1 is preserved and re-affirmed**: nothing about removal stores un-rebuildable state in
  `.squads.json`. The deletion *removes* index state; the trace lives in the (non-authoritative)
  reflog on disk.
<!-- sq:body:end -->

## Discussion

<!-- sq:discussion -->
- [2026-10-25T21:36:40Z] `architect` Robert Architect:
  - 2026-10-25 audit: rewritten; decision unchanged. Deleted the `## Status` banner and the obsolete TASK-111/112 sequencing paragraph. The sever helper is `ref_id_matches`, and the snapshot fields match `_services/_items.py:1078` (type, title, status, severed_refs).
<!-- sq:discussion:end -->
