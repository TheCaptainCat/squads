---
id: ADR-71
sequence_id: 71
type: decision
title: Frontmatter is the source of truth; the index is rebuildable
status: Accepted
author: architect
refs:
- GUIDE-79
- ADR-104
- ADR-955
description: Item state lives in .md frontmatter; .squads.json is a derived index
  that sq repair reconstructs
created_at: '2026-06-12T14:22:53Z'
updated_at: '2026-10-25T21:37:00Z'
---
<!-- sq:body -->
## Context

squads stores every tracked thing — epic, feature, task, bug, ADR, review, guide, role, skill — as
one markdown file under the squad folder, and also keeps a single JSON index at
`<squad>/.squads.json`. There are two plausible homes for an item's durable state (status, parent,
refs, sub-entity state): the file, or the index. We chose the file.

The reasoning: this is a tracker for a team of AI agents working in a git repo. Markdown diffs
cleanly, merges with human judgement, and is readable without the tool. A JSON blob as the system of
record would turn every status change into an opaque line in a large shared file, make merge
conflicts hostile, and couple "can I read my work" to "is the tool installed and uncorrupted."
Putting the truth in per-item frontmatter keeps each change local to one file, keeps the work
legible, and means a damaged or stale index is never a data-loss event — only a cache miss.

## Decision

**Frontmatter is the source of truth; `.squads.json` is a rebuildable index.** Every piece of an
item's durable state lives in its `.md` file's YAML frontmatter — `id`, `sequence_id`, `type`,
`title`, `status`, `parent`, `refs` (with kind inline), timestamps — and so does sub-entity state:
the typed `subentities:` list carrying each story/subtask/finding's status, assignee, severity,
mapped story, and title. The index caches all of this plus the global counter for fast queries and
atomic ID allocation, and stores **nothing that a full rescan of the corpus cannot recover**.

That invariant has two classes, and only two:

- **Per-item durable state admits no exception.** It lives in the item's own frontmatter, and any
  index field holding it is a cache of that frontmatter.
- **Squad-wide, corpus-derived format parameters** (ADR-104) are reconstructable from the corpus as
  a whole rather than from any one file, and carry the stored value as a monotonic floor: the global
  counter and the filename padding, each rebuilt as `max(previous, corpus recompute)`. A rescan may
  raise such a floor and never lower it, because a rebuild over a partial corpus could otherwise
  narrow the padding and break ids already on disk.

`sq repair` is the proof and the enforcement: it rescans every item file, rebuilds the index from
their frontmatter, and rebuilds the corpus-derived parameters over their floors. `sq check` lints the
two against each other and reports any drift. A `.squads.json` merge conflict is therefore a
non-event on a squad at the package's schema — take either side and run `sq repair`. While a squad's
schema is behind the package, the schema gate refuses `sq repair`, and the recovery path is the
reconcile that `sq migrate up` runs before its first runner, which rebuilds a conflicted index from
the files the same way (ADR-955).

## Consequences

- **Nothing may be added to the index that is not derivable from the files.** Any new piece of
  durable state must land in frontmatter first; the index field is a cache of it. This is the single
  hardest constraint on every feature that adds item state. The one declared class beside it is a
  corpus-derived squad-wide parameter with a monotonic floor (ADR-104); per-item state admits no
  exception.
- **Sub-entity state stays in the parent's frontmatter**, never only in the body. The body markers
  hold prose; the machine state is single-sourced in the `subentities:` list and re-rendered into
  the human-readable head and summary on every mutation.
- **The cost is write amplification.** The index is one JSON document, read and rewritten in full on
  every mutation, so changing one status field re-serializes every item. This is accepted at the
  team-working-set scale squads targets (tens to low-thousands of items); it is the first thing to
  revisit if a repo grows an order of magnitude, and any fix (SQLite, partial writes) must preserve
  this invariant — the index stays rebuildable from frontmatter.
- **`sq repair` and `sq check` are load-bearing**, not conveniences: they are how the invariant is
  proven to hold, and they must keep working as new state is added.

## Provenance

Recorded retroactively. This decision was made before squads tracked itself and lived only in
`CLAUDE.md` (invariant 1) and `docs/internals.md` (§4). It is documented here as a decision already
**in force** across the codebase, not one newly debated in-tool.
<!-- sq:body:end -->

## Discussion

<!-- sq:discussion -->
- [2026-08-03T08:40:48Z] `architect` Robert Architect:
  - Wrote the reciprocal note ADR-104 was owed. ADR-104 did its half correctly — declared the second class of index state, named the narrowing, left its point-in-time prose as history — and this decision still read as an unqualified "nothing". Narrowed in place; nothing retired.
  - The distinction that makes both true, and the part a reader needs: per-item durable state admits no exception at all, while a corpus-derived squad-wide parameter is still reconstructable, just not from one file. So the honest form is "nothing a full rescan cannot recover", plus "a rescan may raise a floor and never lower it" — the floor exists because a rebuild over a partial corpus could otherwise narrow the filename padding and break ids already on disk. Verified at `_services/_maintenance.py:757`, with the counter floor beside it.
  - `related` edge added to ADR-104. Also dropped the "Left Proposed for the manager to accept" sentence — see the sweep comment on the retroactive set.
- [2026-10-11T20:18:45Z] `architect` Robert Architect:
  - 2026-10-11: narrowed in place, on the operator's ruling of this date recorded on MILE-934. One dated note, after the paragraph of the Decision section that ends by calling a `.squads.json` merge conflict a non-event to be cleared with `sq repair`. It says the claim holds at the package's schema, and that while a squad's schema is behind the package the gate refuses `sq repair` and the reconcile inside `sq migrate up` is the recovery path (ADR-955 and its amendments of 2026-10-09). Nothing else in the body changed; `related` ref to ADR-955 added.
- [2026-10-25T21:37:00Z] `architect` Robert Architect:
  - 2026-10-25 audit: rewritten in present tense; decision unchanged. Folded the ADR-104 floor class and the ADR-955 recovery path into the Decision text and dropped the dated notes and the amendment section.
<!-- sq:discussion:end -->
