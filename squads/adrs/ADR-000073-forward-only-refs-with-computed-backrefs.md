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
updated_at: '2026-10-25T21:37:03Z'
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
carrying its kind inline — a bare `"ID"` for the spec's declared default kind, or `"ID:kind"` for any
other kind declared in the active spec's `[ref_kinds]` (ADR-775). The parse/format helpers
`split_ref`/`make_ref` in `_models/_item.py` are the only sanctioned way to read or build a ref
string; whether a kind is written bare is decided by the caller against the spec's default kind.

**Backrefs are never persisted.** `refs_in` / `SquadsDB.backrefs` compute the inverse at query time
by scanning forward edges and matching each ref's ID on its (prefix, sequence number), so refs
written at an older padding width still resolve. So a task that fixes a bug carries the edge
(`sq task <n> ref add BUG-<m> --kind fixes`); the bug surfaces the backref on demand, with no stored
edge on its side.

## Consequences

- **A relationship is recorded once, on its source.** There is no "add the other side" step, and the
  two ends can never disagree, because only one end exists on disk.
- **Backref queries are O(n) scans.** Inverting forward edges means walking all items; one such call
  per command is fine, but calling it **per item** (e.g. a backref column on `sq list`/`tree`) is
  O(n²) and is the documented trap. Forward refs and `get(id)` stay cheap dict lookups.
- **Kinds live inline in the ref string**, not in a side map; `split_ref`/`make_ref` must be used
  rather than hand-splitting on the colon. The pre-0.2 `extra.ref_kinds` side map is folded inline
  by the schema migrations, not on load.
- **Direction is a convention the kinds table must state** — e.g. `A blocks B` lives on A, while
  `depends-on` lives on the dependent — because the inverse is computed, the stored direction is the
  only direction, so its meaning has to be unambiguous.

## Provenance

Recorded retroactively. This decision predates squads tracking itself and lived only in `CLAUDE.md`
(invariant 4) and `docs/internals.md` (§5, "Parent/child and refs"). It is documented here as a
decision already **in force**, not newly debated in-tool.
<!-- sq:body:end -->

## Discussion

<!-- sq:discussion -->
- [2026-08-03T08:41:15Z] `architect` Robert Architect:
  - Dropped the "Left **Proposed** for the manager to accept with the set" closer and retitled the section from "Status note" to "Provenance". Status prose in a body is forbidden here and this one had been false since the day the set was accepted. The provenance itself is kept and is worth keeping — this decision predates squads tracking itself and lived only in CLAUDE.md and docs/internals.md, which is why the body reads retroactively. Part of one sweep across the ten retroactive decisions (49, 71-78, 85), not ten tickets.
  - Verified in force while in there, nothing else owed: `split_ref`/`make_ref` at `_models/_item.py:96,102`, `SquadsDB.backrefs` computing by inversion and storing nothing, the pre-0.2 `extra.ref_kinds` side map still folded on load. Both sides are width-tolerant via `ref_id_matches`, which is additive.
- [2026-10-25T21:37:03Z] `architect` Robert Architect:
  - 2026-10-25 audit: rewritten; decision unchanged. Fixed three false claims. Ref kinds are spec-declared (ADR-775), not a closed vocabulary. Backrefs match on (prefix, sequence number). The legacy `extra.ref_kinds` map is folded only by migrations: `_read_refs` passes an empty legacy map on load. Also fixed the ref CLI form, which is now `sq <type> <n> ref add`.
<!-- sq:discussion:end -->
