---
id: ADR-72
sequence_id: 72
type: decision
title: One global monotonic ID counter across all item types
status: Accepted
author: architect
refs:
- ADR-71
- GUIDE-79
description: A single counter makes every ID number globally unique; allocation only
  inside the index transaction
created_at: '2026-06-12T14:22:56Z'
updated_at: '2026-08-03T08:41:19Z'
---
<!-- sq:body -->
## Context

Every tracked item needs a stable, unique identifier that agents and humans can speak aloud and link
by. The open question at design time was how to number them: per-type counters (so `TASK-000001`,
`BUG-000001`, `FEAT-000001` all coexist) or a single counter shared across all types.

Per-type counters are the JIRA-familiar choice, but they carry a hidden cost in a system where
numbers travel as bare references and items cross-link freely: a bare `7` is ambiguous (task 7? bug
7?), and a merge that creates a second item of the same type silently collides on a number that
already means something. A single global counter makes an ID's *number* unique on its own — the
prefix only labels the type — so a reference is unambiguous, collisions are detectable, and the
number sequence honestly reflects creation order.

## Decision

**One global monotonic counter spans all item types.** `SquadsDB.allocate_id(item_type, *, prefix)`
increments the single `counter` and formats the id from the resolved prefix and the squad's padding,
so there is never both a `TASK-000002` and a `BUG-000002` — the number is globally unique and the
prefix is only a type label. Allocation
happens **only inside `IndexStore.transaction()`**, under the cross-process file lock, so two
concurrent `sq` invocations can never collide on an ID or corrupt the index.

The item's real identity is its integer `sequence_id` (the counter value); the formatted `id` is
derived from `type` + `sequence_id`. Both are persisted in frontmatter, and the index is keyed by
the integer.

## Consequences

What this binds today:

- **Numbers are not contiguous within a type** and never will be — `TASK` numbers have gaps wherever
  other types were created in between. This is correct and intended; numbers reflect global creation
  order, not per-type position or hierarchy.
- **ID allocation must stay inside the transaction.** No code path may bump the counter or mint an
  ID outside `IndexStore.transaction()`; doing so would reintroduce the collision the lock prevents.
- **`sq repair` reconstructs the counter** as the maximum ID number across all files, keeping it
  consistent with frontmatter as the source of truth. `sq repair --renumber` resolves duplicate
  numbers from a git merge by reassigning colliding files to fresh numbers and rewriting every
  reference across all files.
- **Padding is a presentation concern**, not part of identity — the width is how the number is
  rendered; the number itself is the durable thing.

## Provenance

Recorded retroactively. This decision predates squads tracking itself and lived only in `CLAUDE.md`
(invariant 2) and `docs/internals.md` (§3). It is documented here as a decision already **in force**,
not newly debated in-tool.

## Provenance note on citations

*Refreshed 2026-08-03.* Both rulings hold — one global counter, allocation only inside
`IndexStore.transaction()` under the cross-process lock, `sequence_id` as the real identity with the
formatted `id` derived from it, and `sq repair` reconstructing the counter as the corpus maximum. Two
mechanism details in the original wording have moved:

- The prefix is **resolved from the active spec** (`_models/_vocab.py::prefix_for`) and passed in, not
  read from a hardcoded map (ADR-266, then ADR-322). The width is the squad's `padding` parameter, not
  a literal 6 (ADR-282 for display, ADR-104 for the filename floor).
- `allocate_id` now raises `SquadsError` when the counter would exceed the capacity of the current
  padding, pointing at `sq migrate repad`. That is a strengthening of the "allocation happens only
  inside the transaction" rule, not a change to it.

`sq repair --renumber` still exists; ADR-295's `sq renumber` is a separate verb for a different job
(pre-merge block shift), and the two do not conflict.
<!-- sq:body:end -->

## Discussion

<!-- sq:discussion -->
- [2026-08-03T08:41:19Z] Robert Architect:
  - Dropped the "Left **Proposed** for the manager to accept with the set" closer and retitled the section from "Status note" to "Provenance". Status prose in a body is forbidden here and this one had been false since the day the set was accepted. The provenance itself is kept and is worth keeping — this decision predates squads tracking itself and lived only in CLAUDE.md and docs/internals.md, which is why the body reads retroactively. Part of one sweep across the ten retroactive decisions (49, 71-78, 85), not ten tickets.
  - Corrected the citations in place, marked as a refresh rather than a change of substance. `allocate_id(item_type, *, prefix)` takes a prefix resolved from the active spec (ADR-266, then ADR-322) and formats at the squads padding, not a literal 6 (ADR-282 for display, ADR-104 for the filename floor). It also now raises when the counter would exceed the paddings capacity, pointing at `sq migrate repad` — a strengthening of the allocate-inside-the-transaction rule, not a change to it.
  - Both rulings hold as decided: one global counter, allocation only inside `IndexStore.transaction()` under the cross-process lock, `sequence_id` as the real identity with `id` derived. `sq repair --renumber` still exists and does not collide with ADR-295s separate `sq renumber` verb.
<!-- sq:discussion:end -->
