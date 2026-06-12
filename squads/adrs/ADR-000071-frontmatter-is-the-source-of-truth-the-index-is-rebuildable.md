---
id: ADR-000071
sequence_id: 71
type: decision
title: Frontmatter is the source of truth; the index is rebuildable
status: Accepted
author: architect
refs:
- GUIDE-000079
description: Item state lives in .md frontmatter; .squads.json is a derived index
  that sq repair reconstructs
created_at: '2026-06-12T14:22:53Z'
updated_at: '2026-06-12T14:29:31Z'
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

`sq repair` is the proof and the enforcement: it rescans every item file, rebuilds the index from
their frontmatter, and resets the counter to the maximum ID number found. `sq check` lints the two
against each other and reports any drift. A `.squads.json` merge conflict is therefore a non-event —
take either side and run `sq repair`.

## Consequences

What this binds today:

- **Nothing may be added to the index that is not derivable from the files.** Any new piece of
  durable state must land in frontmatter first; the index field is a cache of it. This is the single
  hardest constraint on every feature that adds item state.
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

## Status note

Recorded retroactively. This decision was made before squads tracked itself and lived only in
`CLAUDE.md` (invariant 1) and `docs/internals.md` (§4). It is documented here as a decision already
**in force** across the codebase, not one newly debated in-tool. Left **Proposed** for the manager
to accept with the set.
<!-- sq:body:end -->

## Discussion

<!-- sq:discussion -->
<!-- sq:discussion:end -->
