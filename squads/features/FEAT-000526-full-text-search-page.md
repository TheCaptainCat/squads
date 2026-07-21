---
id: FEAT-526
sequence_id: 526
type: feature
title: Full-text search page
status: Done
parent: EPIC-28
author: product-owner
priority: medium
subentities:
- local_id: US1
  title: Open the search page and enter a query
  status: Todo
- local_id: US2
  title: Narrow results by item type and/or status
  status: Todo
- local_id: US3
  title: Select a result to open it in the reader
  status: Todo
- local_id: US4
  title: Empty-query and no-results states, escape back to browse
  status: Todo
created_at: '2026-07-21T12:14:45Z'
updated_at: '2026-07-21T14:38:13Z'
---
<!-- sq:body -->
## Capability

A dedicated full-screen search view in `sq ui`, separate from the browse tree (FEAT-513/514),
for finding items by content rather than by navigating the hierarchy.

A pure read-only consumer of the existing `svc.search(text, item_type=, status=)`, which
already searches titles, summaries, and body/discussion text and returns per-hit snippets with
their matched region. No new backend capability is introduced — the page only calls this
existing method and renders what it returns.

## Acceptance

- A keyboard shortcut opens the full-screen search page from the browse view.
- Typing a query and submitting it lists matching items, each showing its id, type, title, and
  the matched snippet(s) `svc.search` returned for that hit.
- The query can be narrowed by item type and/or status, AND-composed with the text the same
  way `svc.search`'s own `item_type`/`status` parameters compose.
- An empty query shows a clean "type to search" state, not an error; a query with zero matches
  shows a clean "no results" state, not an error or a traceback.
- Selecting a result opens that item in the reader panel (FEAT-514), positioned at that item's
  node in the tree, so the user lands back in familiar browse context rather than a dead end.
- Escape/back from the search page returns to the browse view, leaving the tree's prior
  position intact.

## Non-goals (this feature)

- No new search capability beyond what `svc.search` already does (no new indexes, ranking, or
  fields searched).
- No mutation of any item (no status change, comment, assignment) from the search page.
- No saved/recent searches.
<!-- sq:body:end -->

## User Stories

_Add with `sq feature 526 add-story "As a <role>, I want … so that …"`; track with `sq feature 526 story <n> update --status <Status>`._

<!-- sq:summary -->
| Story | Status | Assignee | Title |
| --- | --- | --- | --- |
| US1 | Todo |  | Open the search page and enter a query |
| US2 | Todo |  | Narrow results by item type and/or status |
| US3 | Todo |  | Select a result to open it in the reader |
| US4 | Todo |  | Empty-query and no-results states, escape back to browse |
<!-- sq:summary:end -->

<!-- sq:stories -->

<!-- sq:story:US1 -->
### US1 — Open the search page and enter a query

<!-- sq:story:US1:head -->
**Status:** ⚪ Todo
<!-- sq:story:US1:head:end -->

<!-- sq:story:US1:body -->
A keyboard shortcut opens a full-screen search page; typing a query and submitting lists matching items with id, type, title, and matched snippet(s).
<!-- sq:story:US1:body:end -->

#### Discussion

<!-- sq:story:US1:discussion -->
<!-- sq:story:US1:discussion:end -->
<!-- sq:story:US1:end -->

<!-- sq:story:US2 -->
### US2 — Narrow results by item type and/or status

<!-- sq:story:US2:head -->
**Status:** ⚪ Todo
<!-- sq:story:US2:head:end -->

<!-- sq:story:US2:body -->
The query can be narrowed by item type and/or status, AND-composed with the text, same as svc.search's own parameters.
<!-- sq:story:US2:body:end -->

#### Discussion

<!-- sq:story:US2:discussion -->
<!-- sq:story:US2:discussion:end -->
<!-- sq:story:US2:end -->

<!-- sq:story:US3 -->
### US3 — Select a result to open it in the reader

<!-- sq:story:US3:head -->
**Status:** ⚪ Todo
<!-- sq:story:US3:head:end -->

<!-- sq:story:US3:body -->
Selecting a result opens that item in the reader panel, positioned at that item's node in the tree.
<!-- sq:story:US3:body:end -->

#### Discussion

<!-- sq:story:US3:discussion -->
<!-- sq:story:US3:discussion:end -->
<!-- sq:story:US3:end -->

<!-- sq:story:US4 -->
### US4 — Empty-query and no-results states, escape back to browse

<!-- sq:story:US4:head -->
**Status:** ⚪ Todo
<!-- sq:story:US4:head:end -->

<!-- sq:story:US4:body -->
An empty query shows a clean prompt state and a zero-match query shows a clean no-results state, never an error; Escape/back returns to the browse view at its prior position.
<!-- sq:story:US4:body:end -->

#### Discussion

<!-- sq:story:US4:discussion -->
<!-- sq:story:US4:discussion:end -->
<!-- sq:story:US4:end -->
<!-- sq:stories:end -->

## Discussion

<!-- sq:discussion -->
<!-- sq:discussion:end -->
