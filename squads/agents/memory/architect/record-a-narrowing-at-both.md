---
summary: Record a narrowing at both ends, or it goes unrecorded
created_at: '2026-08-03T08:54:12Z'
---
Three decisions (ADR-322, ADR-323, ADR-696/604) did nearly every clause-level reversal in the ADR
set and none carried an edge back to what it overrode — so fifteen narrowings sat unrecorded and had
to be found by a full three-reader audit.

When a new decision reverses or narrows a clause of an older one:

- Add a **dated in-place narrowing to the older body.** A dated comment is the record of a *ruling*;
  it is not a guard against the next reader absorbing the retired clause. Both are owed.
- Add **reciprocal `related` refs**, so the pair is reachable from either end. Every unrecorded
  narrowing in the audit was unlinked at both ends.

Two corollaries the same audit produced:

- An ADR with an **empty ref set** is unreviewable for exactly these overlaps, because nothing leads
  a reader to it (ADR-314, ADR-646 both shipped with none).
- A decision that **adds a key to a frozen catalog** must say so in its own body and name the
  catalog it extends. The type catalog grew from four keys to seven with only one addition declared,
  which makes the freeze unauditable against the tree — legitimate under additive-superset, invisible
  to review.