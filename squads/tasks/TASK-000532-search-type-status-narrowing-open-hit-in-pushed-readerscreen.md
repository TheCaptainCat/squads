---
id: TASK-532
sequence_id: 532
type: task
title: 'Search: type/status narrowing + open hit in pushed ReaderScreen'
status: Done
parent: FEAT-526
author: tech-lead
refs:
- TASK-531:depends-on
subentities:
- local_id: ST1
  title: Item type/status narrowing forwarded to svc.search
  status: Done
  story: US2
- local_id: ST2
  title: Select hit -> push ReaderScreen (not tree navigation)
  status: Done
  story: US3
created_at: '2026-07-21T12:20:46Z'
updated_at: '2026-07-21T14:37:59Z'
---
<!-- sq:body -->
## Scope

Finish search: narrow the query by item type and/or status, and open a selected result in a
pushed reader. Extends the `SearchScreen` built in the previous task and reuses the `ReaderScreen`
from the screen-stack refactor. Depends on the SearchScreen task.

## What to build

- **Type/status narrowing**: add item-type and status inputs to `SearchScreen` and pass them as
  `svc.search(text, item_type=…, status=…)`. They AND-compose with the text exactly as the
  service's own parameters do — no TUI-side re-filtering; just forward the chosen values (unset
  → `None`).
- **Open a hit in a pushed `ReaderScreen`** (ADR-527 §3): selecting a result does
  `push_screen(ReaderScreen(svc, hit_item_id))` — it does **NOT** navigate the browse tree to
  the item. Rationale to honour: search runs over the whole corpus (its own type/status filter),
  so a hit may be an item the browse tree is currently filtering out (closed, or excluded by the
  active `ItemFilter`); navigating the tree would fail for those and would silently move the
  browse position. A pushed `ReaderScreen` opens any hit deterministically and leaves browse
  state untouched, reusing the one reader. (This overrides FEAT-526's US3 wording about
  "positioned at that item's node in the tree" — ADR-527 §3 is binding.)
- **Escape chain**: escape from the pushed reader pops back to the search results; escape again
  pops back to browse. Focus restoration is automatic on pop.
- `ReaderScreen` already exists (screen-stack refactor) and takes `Service` + id — no change to
  its contract; `_search` imports the reader module per ADR-527 §4.

## Constraints (ADR-516 + ADR-527, binding)

- In-process `Service`, read-only (`svc.search` + the reader's existing load path). No `--json`
  subprocess.
- Async on Textual's loop; no `anyio.run`.
- Import direction preserved (`_search` → reader module); graph acyclic; no widget imports a
  screen.

## Acceptance (what the reviewer/QA checks)

- Setting item type and/or status narrows results; the narrowing AND-composes with the query the
  same way `svc.search`'s parameters do (verified: forwarded to `svc.search`, no TUI-side
  re-filter).
- Selecting a result pushes a `ReaderScreen` loading that exact item — including a hit that the
  current browse filter would exclude (e.g. a closed item) — and the browse tree's selection is
  unchanged afterward (no tree navigation side effect).
- Escape from the reader returns to the results; escape again returns to browse.
- Keyboard-only over a plain terminal.
- `uv run pyright && uv run ruff check . && uv run ruff format --check .` clean; TUI tests assert
  type/status narrowing forwards to `svc.search`, selecting a hit opens a `ReaderScreen` for it
  (including a filtered-out item) without moving the browse selection, and the escape chain.

## Story mapping

Satisfies **FEAT-526 / US2 — "Narrow results by item type and/or status"** and **US3 — "Select a
result to open it in the reader"** (opened via a pushed `ReaderScreen` per ADR-527 §3, not tree
navigation). Add two subtasks: one `--story US2` (type/status narrowing), one `--story US3`
(select → pushed ReaderScreen).
<!-- sq:body:end -->

## Subtasks

_Add with `sq task 532 add-subtask "<title>"`; track with `sq task 532 subtask <n> update --status <Status>`._

<!-- sq:summary -->
| Subtask | Status | Assignee | Title | Story |
| --- | --- | --- | --- | --- |
| ST1 | Done |  | Item type/status narrowing forwarded to svc.search | US2 |
| ST2 | Done |  | Select hit -> push ReaderScreen (not tree navigation) | US3 |
<!-- sq:summary:end -->

<!-- sq:subtasks -->

<!-- sq:subtask:ST1 -->
### ST1 — Item type/status narrowing forwarded to svc.search

<!-- sq:subtask:ST1:head -->
**Status:** 🟢 Done
**Implements:** US2 — Narrow results by item type and/or status
<!-- sq:subtask:ST1:head:end -->

<!-- sq:subtask:ST1:body -->
Add item-type and status inputs to SearchScreen; forward as svc.search(text, item_type=, status=) (unset -> None), AND-composing exactly as the service params do — no TUI-side re-filter. Done: narrowing changes results and is forwarded to svc.search.
<!-- sq:subtask:ST1:body:end -->

#### Discussion

<!-- sq:subtask:ST1:discussion -->
<!-- sq:subtask:ST1:discussion:end -->
<!-- sq:subtask:ST1:end -->

<!-- sq:subtask:ST2 -->
### ST2 — Select hit -> push ReaderScreen (not tree navigation)

<!-- sq:subtask:ST2:head -->
**Status:** 🟢 Done
**Implements:** US3 — Select a result to open it in the reader
<!-- sq:subtask:ST2:head:end -->

<!-- sq:subtask:ST2:body -->
Selecting a result does push_screen(ReaderScreen(svc, hit_item_id)) — NOT tree navigation (ADR-527 s3): a hit may be filtered out of the browse tree, so a pushed reader opens any hit deterministically and leaves browse state untouched, reusing the existing ReaderScreen. Escape pops reader->results->browse. Done: selecting a hit (incl. a filtered-out item) opens its reader with the browse selection unchanged; escape chain works.
<!-- sq:subtask:ST2:body:end -->

#### Discussion

<!-- sq:subtask:ST2:discussion -->
<!-- sq:subtask:ST2:discussion:end -->
<!-- sq:subtask:ST2:end -->
<!-- sq:subtasks:end -->

## Discussion

<!-- sq:discussion -->
- [2026-07-21T13:03:15Z] Elias Python:
  - Built: item-type/status Select widgets added to SearchScreen, forwarded as svc.search(text, item_type=, status=) (unset -> None) -- no TUI-side re-filter, re-runs on every select change (reactive narrowing). Selecting a result (ListView.Selected) pushes ReaderScreen(svc, hit.item_id) per ADR-527 s3 -- NOT tree navigation; verified this reaches a Done/closed item the browse ItemFilter would exclude. Escape chain: reader.dismiss() -> search (still on stack) -> search.dismiss() -> browse, browse's own tree cursor/selection is provably untouched by the whole excursion.
  - Verified: 2 new Pilot tests -- narrowing is forwarded to svc.search (spied) and changes the result set; selecting a hit (including a closed item excluded by browse's filter) pushes a ReaderScreen for that exact item, escape pops reader->search->browse, and browse's cursor stays on its pre-search node throughout. Full tests/tui/ (30, stable across repeated runs) + whole-repo pyright/ruff clean. Import graph verified: _search->_reader only, _app->_browse, _browse->_filter/_reader/_search/_tree, _filter has zero runtime _tui imports (TYPE_CHECKING-only) -- matches ADR-527 s4 exactly.
<!-- sq:discussion:end -->
