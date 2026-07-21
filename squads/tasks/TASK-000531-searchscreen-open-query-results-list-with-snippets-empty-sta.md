---
id: TASK-531
sequence_id: 531
type: task
title: 'SearchScreen: open, query, results list with snippets, empty states'
status: Done
parent: FEAT-526
author: tech-lead
refs:
- TASK-528:depends-on
subentities:
- local_id: ST1
  title: Open search page, query, results list with snippets
  status: Done
  story: US1
- local_id: ST2
  title: Empty-query and no-results states; escape back to browse
  status: Done
  story: US4
created_at: '2026-07-21T12:20:43Z'
updated_at: '2026-07-21T14:37:58Z'
---
<!-- sq:body -->
## Scope

The full-text search surface: a full-screen search view pushed over browse, with a query input
and a results list showing each hit's id/type/title/snippets, plus the empty-query and
no-results states and escape-back. Depends on the screen-stack refactor (needs the screen model
+ `BrowseScreen` to bind the search key). Type/status narrowing and opening a hit are the
follow-up task.

## What to build

Per ADR-527 §1 and §4:

- **`SearchScreen`** (full `Screen`, not modal) in a new `_tui/_search.py`: a query input over a
  results list. Search is its own mode, so it fully replaces the view (a full Screen, not an
  overlay). Opened from `BrowseScreen` via a search key binding doing `push_screen(SearchScreen(
  svc))`.
- **Query + results**: on submit, call `svc.search(text)` (in-process, async — awaited on
  Textual's loop; a long search may run in a Textual worker, e.g. `@work(exclusive=True)`, so
  keystrokes stay responsive). Render one row per `SearchResult`: the item's id, type, and title,
  plus the matched `snippet`(s) from its `SearchHit`s (`hit.snippet`; `hit.location` is the
  human-readable locator). Escape `[...]`-bearing text so Rich does not treat it as markup.
- **States**: an empty/blank query shows a clean "type to search" prompt state (do not call
  `svc.search` with an empty needle — it raises; guard before calling). A submitted query with
  zero matches shows a clean "no results" state. Neither is an error or a traceback.
- **Escape/back**: escape pops `SearchScreen` back to `BrowseScreen`, leaving the tree's prior
  position intact (Textual restores focus to the screen beneath on pop — no manual focus
  handling).
- `_search.py` imports the reader module (for the follow-up hit-open) per ADR-527 §4;
  `BrowseScreen` imports `_search`. No widget imports a screen.

## Constraints (ADR-516 + ADR-527, binding)

- In-process `Service`, read-only (`svc.search` only). No `sq … --json` subprocess.
- Async `search` on Textual's loop (optionally a Textual worker); never `anyio.run`.
- Import direction preserved; graph acyclic.

## Acceptance (what the reviewer/QA checks)

- A keyboard shortcut opens the full-screen search page from the browse view.
- Submitting a query lists matching items, each showing id, type, title, and the snippet(s)
  `svc.search` returned for that hit.
- An empty/blank query shows a "type to search" state and never calls `svc.search` (no raised
  "non-empty query" error); a zero-match query shows a clean "no results" state — neither is a
  traceback.
- Escape returns to the browse view with the tree's prior selection/position intact.
- All keyboard-only over a plain terminal; results built from `svc.search` (a grep confirms no
  `--json`/subprocess in `_tui`).
- `uv run pyright && uv run ruff check . && uv run ruff format --check .` clean; TUI tests assert
  a query lists hits with snippets, the empty-query prompt (search not called), the no-results
  state, and escape returns to browse.

## Story mapping

Satisfies **FEAT-526 / US1 — "Open the search page and enter a query"** and **US4 —
"Empty-query and no-results states, escape back to browse"**. Add two subtasks: one `--story US1`
(open + query + results list with snippets), one `--story US4` (empty/no-results states +
escape back).
<!-- sq:body:end -->

## Subtasks

_Add with `sq task 531 add-subtask "<title>"`; track with `sq task 531 subtask <n> update --status <Status>`._

<!-- sq:summary -->
| Subtask | Status | Assignee | Title | Story |
| --- | --- | --- | --- | --- |
| ST1 | Done |  | Open search page, query, results list with snippets | US1 |
| ST2 | Done |  | Empty-query and no-results states; escape back to browse | US4 |
<!-- sq:summary:end -->

<!-- sq:subtasks -->

<!-- sq:subtask:ST1 -->
### ST1 — Open search page, query, results list with snippets

<!-- sq:subtask:ST1:head -->
**Status:** 🟢 Done
**Implements:** US1 — Open the search page and enter a query
<!-- sq:subtask:ST1:head:end -->

<!-- sq:subtask:ST1:body -->
SearchScreen (full Screen) pushed from BrowseScreen via a search key; query input + results list. On submit call svc.search(text) (async on Textual's loop, optionally @work(exclusive=True)); render id/type/title + hit.snippet(s) per SearchResult, escaping markup. Done: submitting a query lists hits with snippets.
<!-- sq:subtask:ST1:body:end -->

#### Discussion

<!-- sq:subtask:ST1:discussion -->
<!-- sq:subtask:ST1:discussion:end -->
<!-- sq:subtask:ST1:end -->

<!-- sq:subtask:ST2 -->
### ST2 — Empty-query and no-results states; escape back to browse

<!-- sq:subtask:ST2:head -->
**Status:** 🟢 Done
**Implements:** US4 — Empty-query and no-results states, escape back to browse
<!-- sq:subtask:ST2:head:end -->

<!-- sq:subtask:ST2:body -->
Guard empty/blank query -> 'type to search' state without calling svc.search (it raises on empty needle); zero-match query -> clean 'no results' state; neither is a traceback. Escape pops SearchScreen back to BrowseScreen with the tree's prior position intact (focus restored automatically). Done: empty prompt (search not called), no-results state, escape returns to browse.
<!-- sq:subtask:ST2:body:end -->

#### Discussion

<!-- sq:subtask:ST2:discussion -->
<!-- sq:subtask:ST2:discussion:end -->
<!-- sq:subtask:ST2:end -->
<!-- sq:subtasks:end -->

## Discussion

<!-- sq:discussion -->
- [2026-07-21T12:59:14Z] Elias Python:
  - Built: SearchScreen (_search.py, full Screen) pushed via '/' from BrowseScreen. Query Input -> Input.Submitted guards blank/whitespace-only text (never calls svc.search, shows 'Type to search...') and otherwise runs svc.search(text) in a @work(exclusive=True) worker for keystroke responsiveness; results render as a keyboard-navigable ListView, one _HitItem row per SearchResult showing id/type/title + each hit's location:snippet, all escaped. Zero matches -> clean 'No results for ...' state. Escape pops back to BrowseScreen, which stays mounted (tree/cursor position untouched, confirmed by test).
  - Verified: 5 new Pilot tests -- '/' opens SearchScreen, a real query lists a hit with its snippet, blank query shows the prompt AND never calls svc.search (spied), a no-match query shows the no-results state, and escape returns to browse with cursor position intact. Full tests/tui/ (28) + whole-repo pyright/ruff clean; grep confirms no --json/subprocess in _tui.
<!-- sq:discussion:end -->
