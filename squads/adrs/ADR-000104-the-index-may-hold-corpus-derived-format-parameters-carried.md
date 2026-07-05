---
id: ADR-104
sequence_id: 104
type: decision
title: The index may hold corpus-derived format parameters carried as a floor (padding,
  counter)
status: Accepted
author: architect
refs:
- ADR-71
- ADR-72
- FEAT-27
description: 'Refines invariant 1: squad-wide format/allocation parameters (counter,
  ID padding) are reconstructed from the file corpus with the stored value as a floor;
  this is permitted and is not per-item state in the index.'
created_at: '2026-06-14T20:59:27Z'
updated_at: '2026-07-04T20:28:15Z'
---
<!-- sq:body -->
## Context

ADR-71 fixed invariant 1: frontmatter is the source of truth, and `.squads.json` stores
**nothing that cannot be reconstructed from the files** (`sq repair` is the proof). It was written
about per-item *durable state* — status, parent, refs, sub-entity state — which must live in each
item's own frontmatter, not the index.

FEAT-27 (explicit ID padding) surfaces a parameter that doesn't fit that frame cleanly. It
stores an ID-width `padding` (default 6) in the index and derives all ID formatting from it. The
raise-padding migration (`sq migrate repad <width>`) renames every item file to the new width but
leaves file **contents byte-untouched** — frontmatter `id`/`sequence_id` keep their old width, and
reads are width-tolerant. So `padding` is authoritative squad-wide state that is **not** present in
any single item's frontmatter, and deriving it from frontmatter `id` width would be actively wrong
(it would re-shrink padding after every repad).

The tech lead (Olivia) flagged this as a possible bend of invariant 1 and asked for a ruling before
implementation. The question generalises beyond padding: the global counter (ADR-72) is the
**same category** of state — squad-wide, not held in any one item's frontmatter, reconstructed by
`repair` as `max(ID numbers across the corpus)` with the previously-stored value carried forward as
a floor (`db.counter = max(previous_counter, max_n)`).

## Decision

**Invariant 1 admits a second, narrow class of index state: squad-wide format/allocation parameters
that are reconstructed from the file corpus as a whole, with the stored value carried as a floor.**

This is distinct from — and does not weaken — the per-item rule. Item durable state still lives in
frontmatter, full stop. What this ADR names is a category that was already in force for the counter
and is now extended to padding:

- The parameter is **squad-wide**, not per-item; no single `.md` file owns it.
- It is **reconstructable from the corpus**: from the set of ID numbers (counter) or the set of
  item-filename widths (padding), read across all files.
- `repair` computes it as **`max(stored_floor, corpus_recompute)`** — the stored value is the floor,
  the corpus scan is the recompute, and repair takes the higher. This keeps `repair` monotonic in
  the parameter (it never regresses), idempotent, and re-runnable.
- The stored floor exists precisely to survive the degenerate corpora where the recompute is
  unreliable: an **empty squad** (no files to derive from) and a **mid-rename / partial corpus**
  (some files at the new width, some not).

For padding specifically, the corpus signal is the **item filename width** (the digit-run width of
`PREFIX-<digits>-<slug>.md`), *not* the frontmatter `id` width — because repad rewrites filenames
but never file contents, the filename is the only in-corpus record that a repad occurred.

The boundary, restated for future features: index state is permitted only if it is either (a) a
cache of per-item frontmatter, or (b) a squad-wide parameter reconstructable from the corpus with
the stored value as a floor. Anything that is neither must land in frontmatter first.

## Consequences

- **`sq repair` is still the enforcement of invariant 1**, now proving two things: per-item caches
  reconstruct from frontmatter, and corpus parameters reconstruct as `max(floor, corpus)`. Both the
  counter and padding go through this path; a `.squads.json` merge conflict stays a non-event.
- **Padding follows the counter's exact pattern.** TASK-101's "repair must preserve the stored
  padding" is correct in spirit but is implemented as `max(stored_floor, max_filename_width)`, not a
  blind carry-forward: the floor is the carry-forward, the filename max is the recompute.
- **The category is deliberately narrow.** It is not a licence to park arbitrary settings in the
  index. A new index field must be either a frontmatter cache or a corpus-derived-with-floor
  parameter; reviewers should reject anything that is config (that belongs in `.squads.toml`) or
  un-reconstructable state (that belongs in frontmatter).
- **ADR-72's "padding is a presentation concern, not part of identity" still holds** — the
  number is the identity; padding only governs how it is rendered and how wide files are named.
  This ADR adds: that presentation parameter is nonetheless authoritative squad-wide state with a
  legitimate, floored home in the index.

## Relationship to prior ADRs

This **refines** ADR-71 (it names a permitted second class of index state) and **generalises**
the counter mechanism already accepted in ADR-72. Both remain accepted and unedited as the
historical record; this ADR is the cross-linked refinement, per the project convention of one
decision per ADR rather than rewriting accepted ones.
<!-- sq:body:end -->

## Discussion

<!-- sq:discussion -->
- [2026-07-04T20:28:15Z] Robert Architect:
  - Forward pointer: ADR-282 refines this decision. The corpus-derived floor mechanism ruled on here (stored floor, repair recompute from filename width, repad on overflow) is preserved exactly; 282 only narrows the stored padding parameter's consumer from 'all ID formatting' (as it was under FEAT-27, described above) to 'filename formatting only' — display becomes a constant unpadded 0. The Context/Consequences prose here is the point-in-time record and stays unedited per the one-decision-per-ADR convention.
<!-- sq:discussion:end -->
