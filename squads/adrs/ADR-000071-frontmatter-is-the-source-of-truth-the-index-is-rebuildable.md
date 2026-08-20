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
description: Item state lives in .md frontmatter; .squads.json is a derived index
  that sq repair reconstructs
created_at: '2026-06-12T14:22:53Z'
updated_at: '2026-08-03T08:40:48Z'
---
<!-- sq:body -->
## Context

squads stores every tracked thing — epic, feature, task, bug, ADR, review, guide, role, skill — as
one markdown file under the squad folder, and also keeps a single JSON index at
`<squad>/.squads.json`. From the start there were two plausible homes for an item's durable state
(status, parent, refs, sub-entity state): the file, or the index. We chose the file.

The reasoning at the time, recorded honestly: this is a tracker for a team of AI agents working in a
git repo. Markdown diffs cleanly, merges with human judgement, and is readable without the tool.
A JSON blob as the system of record would turn every status change into an opaque line in a large
shared file, make merge conflicts hostile, and couple "can I read my work" to "is the tool
installed and uncorrupted." Putting the truth in per-item frontmatter keeps each change local to one
file, keeps the work legible, and means a damaged or stale index is never a data-loss event — only a
cache miss.

## Decision

**Frontmatter is the source of truth; `.squads.json` is a rebuildable index.** Every piece of an
item's durable state lives in its `.md` file's YAML frontmatter — `id`, `sequence_id`, `type`,
`title`, `status`, `parent`, `refs` (with kind inline), timestamps — and so does sub-entity state:
the typed `subentities:` list carrying each story/subtask/finding's status, assignee, severity,
mapped story, and title. The index caches all of this plus the global counter for fast queries and
atomic ID allocation, but stores **nothing that cannot be reconstructed from the files**.

*Narrowed 2026-08-03: one second class exists, and it is declared rather than accidental. ADR-104
admits squad-wide, corpus-derived format parameters carried in the index with a monotonic floor —
the filename padding, reconstructed as `max(previous, widest filename found)` rather than derived
from any one file. The invariant it narrows is "reconstructable from the corpus", not
"reconstructable from a file": a rebuild still recovers it, and a rebuild may never lower it. See
the amendment note.*

`sq repair` is the proof and the enforcement: it rescans every item file, rebuilds the index from
their frontmatter, and resets the counter to the maximum ID number found. `sq check` lints the two
against each other and reports any drift. A `.squads.json` merge conflict is therefore a non-event —
take either side and run `sq repair`.

## Consequences

What this binds today:

- **Nothing may be added to the index that is not derivable from the files.** Any new piece of
  durable state must land in frontmatter first; the index field is a cache of it. This is the single
  hardest constraint on every feature that adds item state. *One declared class of exception:
  corpus-derived squad-wide format parameters with a monotonic floor (ADR-104). Per-**item** state
  admits no exception.*
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

## Amendment note

**2026-08-03 — the reciprocal note for ADR-104's second class of index state.** ADR-104 declares that
the index may hold squad-wide format parameters derived from the whole corpus rather than from any one
item's frontmatter, and carried with a monotonic floor: `db.padding = max(previous_padding,
max_filename_width)`, with the counter floor beside it. ADR-104 states this from its own end, names the
narrowing, and leaves its point-in-time prose as history — it is the model this pass copied elsewhere.
What was missing was this end: this decision still read as an unqualified "nothing".

The distinction that makes both true, and the one a reader needs: *per-item* durable state admits no
exception at all — it lives in frontmatter, and a field in the index is a cache of it. A *corpus-derived
squad-wide* parameter is still reconstructable, just not from one file, and the floor exists because a
rebuild over a partial corpus could otherwise narrow it and break ids that are already on disk. So the
honest form of the invariant is "the index holds nothing that a full rescan cannot recover", plus "a
rescan may raise a floor and never lower it". `sq repair` remains the proof of both.

`related` edge added to ADR-104.
<!-- sq:body:end -->

## Discussion

<!-- sq:discussion -->
- [2026-08-03T08:40:48Z] Robert Architect:
  - Wrote the reciprocal note ADR-104 was owed. ADR-104 did its half correctly — declared the second class of index state, named the narrowing, left its point-in-time prose as history — and this decision still read as an unqualified "nothing". Narrowed in place; nothing retired.
  - The distinction that makes both true, and the part a reader needs: per-item durable state admits no exception at all, while a corpus-derived squad-wide parameter is still reconstructable, just not from one file. So the honest form is "nothing a full rescan cannot recover", plus "a rescan may raise a floor and never lower it" — the floor exists because a rebuild over a partial corpus could otherwise narrow the filename padding and break ids already on disk. Verified at `_services/_maintenance.py:757`, with the counter floor beside it.
  - `related` edge added to ADR-104. Also dropped the "Left Proposed for the manager to accept" sentence — see the sweep comment on the retroactive set.
<!-- sq:discussion:end -->
