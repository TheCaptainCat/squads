---
id: ADR-73
sequence_id: 73
type: decision
title: Forward-only refs with computed backrefs
status: Accepted
author: architect
refs:
- GUIDE-79
description: Items store outgoing refs with kind inline; backrefs are computed by
  inversion, never persisted
created_at: '2026-06-12T14:23:00Z'
updated_at: '2026-06-12T14:29:31Z'
---
<!-- sq:body -->
## Context

Items cross-link: a task fixes a bug, a guide explains an ADR, a decision supersedes another. Each
such relationship has two ends, and a tracker has to decide where the edge is stored. The two
options are to persist both directions (write the edge on both items) or to persist only one
direction and compute the other on demand.

Storing both ends is redundant state that can drift: add a forward edge and forget the backref and
the two files disagree; the index and the files can fall out of sync; a rename has to fix the edge
in two places. Since the relationship is fully described by one directed edge, the inverse is pure
derivation — and deriving it removes a whole class of consistency bugs.

## Decision

**Forward edges only.** `item.refs` holds the item's **outgoing** refs as a list of strings, each
carrying its kind inline — `"ID"` for the default `related`, or `"ID:kind"` for a typed edge
(`fixes`, `addresses`, `implements`, `supersedes`, and the rest of the closed vocabulary). The
parse/format helpers `split_ref`/`make_ref` in `_models/_item.py` are the only sanctioned way to
read or build a ref string.

**Backrefs are never persisted.** `refs_in` / `SquadsDB.backrefs` compute the inverse by scanning
forward edges and matching on the ID part at query time. So a task that fixes a bug does
`sq ref add TASK BUG --kind fixes`; the bug surfaces the backref on demand, with no stored edge on
its side.

## Consequences

What this binds today:

- **A relationship is recorded once, on its source.** There is no "add the other side" step, and the
  two ends can never disagree, because only one end exists on disk.
- **Backref queries are O(n) scans.** Inverting forward edges means walking all items; one such call
  per command is fine, but calling it **per item** (e.g. a backref column on `sq list`/`tree`) is
  O(n²) and is the documented trap. Forward refs and `get(id)` stay cheap dict lookups.
- **Kinds live inline in the ref string**, not in a side map; `split_ref`/`make_ref` must be used
  rather than hand-splitting on the colon. (The pre-0.2 `extra["ref_kinds"]` side map is read
  transparently and folded inline on load, for migration only.)
- **Direction is a convention the kinds table must state** — e.g. `A blocks B` lives on A, while
  `depends-on` lives on the dependent — because the inverse is computed, the stored direction is the
  only direction, so its meaning has to be unambiguous.

## Status note

Recorded retroactively. This decision predates squads tracking itself and lived only in `CLAUDE.md`
(invariant 4) and `docs/internals.md` (§5, "Parent/child and refs"). It is documented here as a
decision already **in force**, not newly debated in-tool. Left **Proposed** for the manager to
accept with the set.
<!-- sq:body:end -->

## Discussion

<!-- sq:discussion -->
<!-- sq:discussion:end -->
