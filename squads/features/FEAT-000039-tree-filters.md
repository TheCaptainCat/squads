---
id: FEAT-39
sequence_id: 39
type: feature
title: Tree filters
status: Done
parent: EPIC-38
author: product-owner
priority: low
description: sq tree gains the same filters as list (--status, --priority, --assignee,
  --type) plus --depth; matches keep their ancestor path so the tree stays a tree
subentities:
- local_id: US1
  title: Filter tree by status/priority/assignee/type for focused reviews
  status: Todo
- local_id: US2
  title: --depth and context-preserving pruning keep filtered trees readable
  status: Todo
created_at: '2026-06-11T07:58:43Z'
updated_at: '2026-06-24T14:14:34Z'
---
<!-- sq:body -->
## Problem

`sq tree` shows everything or (with `--all`) even more. On a board the size of ours it's already
two screens; there is no way to ask the tree-shaped questions a backlog review actually poses:
*show me only the high-priority work*, *only what's Ready*, *only Mara's items*, *just the first
two levels*.

## Value

The tree becomes the review tool instead of just the inventory: one flag turns the full board
into "the Ready highs" during a greenlight discussion. Filters mirror `sq list`'s existing flags,
so there is nothing new to learn — the same vocabulary, applied to the hierarchical view.

## Scope

- `sq tree [ROOT] --status S --priority P --assignee A --type T` — same flags and semantics as
  `list`; repeatable where list's are; combinable (AND).
- `--depth N` — cut the tree below N levels from the root.
- **Tree semantics preserved**: a filter matches *nodes*, but matched nodes keep their ancestor
  chain so every hit is shown in context — ancestors that only serve as path are rendered dimmed
  (or marked), not counted as matches.
- `--json` carries the same filtering (the shape itself unchanged — pruned, not reshaped);
  piped/plain behaviour per the epic's standing constraint.
- Out of scope: filtering by ref kinds or graph relations — that's FEAT-37's territory.

## Acceptance

- Each filter works alone and combined, with and without an explicit root; `--depth` truncates
  correctly.
- A filtered tree never shows an orphaned match: ancestor paths always intact, path-only nodes
  visually distinct.
- `--json` output is the same shape, pruned consistently with the rendered tree.
- Filter flags, names and parsing are shared with `list` (one implementation), so the two never
  drift.
<!-- sq:body:end -->

## User Stories

_Add with `sq feature 39 add-story "As a <role>, I want … so that …"`; track with `sq feature 39 story <n> update --status <Status>`._

<!-- sq:summary -->
| Story | Status | Assignee | Title |
| --- | --- | --- | --- |
| US1 | Todo |  | Filter tree by status/priority/assignee/type for focused reviews |
| US2 | Todo |  | --depth and context-preserving pruning keep filtered trees readable |
<!-- sq:summary:end -->

<!-- sq:stories -->

<!-- sq:story:US1 -->
### US1 — Filter tree by status/priority/assignee/type for focused reviews

<!-- sq:story:US1:head -->
**Status:** ⚪ Todo
<!-- sq:story:US1:head:end -->

<!-- sq:story:US1:body -->
As an operator reviewing the board, I want to filter the tree by status, priority, assignee or type, so that greenlight discussions look at exactly the slice that matters.
<!-- sq:story:US1:body:end -->

#### Discussion

<!-- sq:story:US1:discussion -->
<!-- sq:story:US1:discussion:end -->
<!-- sq:story:US1:end -->

<!-- sq:story:US2 -->
### US2 — --depth and context-preserving pruning keep filtered trees readable

<!-- sq:story:US2:head -->
**Status:** ⚪ Todo
<!-- sq:story:US2:head:end -->

<!-- sq:story:US2:body -->
As a reader of a deep backlog, I want --depth and context-preserving pruning, so that a filtered tree stays readable and every match keeps its place in the hierarchy.
<!-- sq:story:US2:body:end -->

#### Discussion

<!-- sq:story:US2:discussion -->
<!-- sq:story:US2:discussion:end -->
<!-- sq:story:US2:end -->
<!-- sq:stories:end -->

## Discussion

<!-- sq:discussion -->
<!-- sq:discussion:end -->
