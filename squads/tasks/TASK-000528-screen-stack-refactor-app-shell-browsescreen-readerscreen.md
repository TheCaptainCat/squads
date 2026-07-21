---
id: TASK-528
sequence_id: 528
type: task
title: 'Screen-stack refactor: App shell + BrowseScreen + ReaderScreen'
status: Done
parent: FEAT-525
author: tech-lead
assignee: python-dev
created_at: '2026-07-21T12:20:34Z'
updated_at: '2026-07-21T14:37:56Z'
---
<!-- sq:body -->
## Scope

Enabling refactor for the whole filter+search increment: promote the current single-screen
`sq ui` (tree + reader composed directly on the App) into the screen-stack model ADR-527 fixes.
No new user-facing capability — behaviour is byte-for-byte what browse does today; this only
reshapes the structure both features build on, and migrates the existing TUI tests to it.

## What to build

Per ADR-527 §1 and §4:

- **App becomes a thin shell.** `_tui/_app.py`'s `App` subclass holds the in-process `Service`
  handle and its global bindings only; on mount it `push_screen`s a `BrowseScreen`. The App
  composes no tree/reader of its own anymore.
- **`BrowseScreen`** (full `Screen`) in a new `_tui/_browse.py`: owns the tree + reader layout,
  the `on_mount` `tree_view()` population, node-highlight → reader load, and the tree/nav key
  bindings that live on the App today. It is the base of the stack.
- **`ReaderScreen`** (full `Screen`) added to `_tui/_reader.py` (kept with `ReaderPanel` — one
  "read an item" concern): wraps the existing `ReaderPanel`, taking a `Service` + item id,
  composing the panel and calling its existing `load` path on mount. Escape/quit pops it. This
  is the standalone reader that FEAT-526 will push for a search hit; wire the screen now even
  though nothing pushes it yet.
- `ReaderPanel` and `_tui/_tree.py` are unchanged in contract — `ReaderPanel` still takes just
  a `Service` + id and is now used in two hosts (embedded in `BrowseScreen`, standalone in
  `ReaderScreen`).
- **Migrate `tests/tui/` to the screen structure.** The existing `test_ui_app_behavior.py`
  reaches into the App's widgets directly (`app.query_one(Tree)`, `#glance-header`, etc.);
  update those to locate the widgets through the pushed `BrowseScreen` (the query targets move
  under the screen, the assertions stay the same). Keep every current assertion's intent —
  launch/quit, tree/`tree_view` parity, keyboard nav, selection→reader, header, tabs, empty
  states — green against the new structure.

## Constraints (ADR-516 + ADR-527, binding)

- In-process `Service`, read-only (`tree_view`/`get`/`read_body`/`read_discussion` + spec
  lookups only — no mutating calls). No `sq … --json` subprocess.
- Async service calls awaited on Textual's own loop (screen `on_mount`/handlers) — never
  `anyio.run`; `sq ui` stays the plain sync command it is today.
- Import direction (ADR-527 §4): `_app` → screens; `_browse` → the reader/tree modules; widgets
  never import screens. Everything imports downward only into `_services`/`_models`/`_rendering`;
  nothing in the core path imports `_tui`. Graph stays acyclic.

## Acceptance (what the reviewer/QA checks)

- `sq ui` launches into a `BrowseScreen` on the stack (App composes nothing itself) and quits
  cleanly; browse behaviour — tree parity with `tree_view`, keyboard nav, selection→reader
  header/tabs/empty states — is unchanged from the prior increment.
- A `ReaderScreen` exists, wraps `ReaderPanel`, loads an item by id, and pops on escape; a test
  pushes it directly and asserts it renders the item (even though no in-app path pushes it yet).
- The full `tests/tui/` suite passes against the screen structure, preserving every prior
  assertion's intent.
- Import graph acyclic; `_app`→screens, `_browse`→reader/tree, widgets import no screens — a
  grep confirms no widget module imports a screen module.
- `uv run pyright && uv run ruff check . && uv run ruff format --check .` clean.

## Story mapping

No user story — pure enabling refactor for FEAT-525 (and the base FEAT-526 search reuses). It
unblocks US1–US4 of the filter popup rather than satisfying any one of them.
<!-- sq:body:end -->

## Subtasks

_Add with `sq task 528 add-subtask "<title>"`; track with `sq task 528 subtask <n> update --status <Status>`._

<!-- sq:summary -->
<!-- sq:summary:end -->

<!-- sq:subtasks -->
<!-- sq:subtasks:end -->

## Discussion

<!-- sq:discussion -->
- [2026-07-21T12:38:21Z] Elias Python:
  - Built: App is now a thin shell (_app.py) holding just the Service handle + quit binding, pushing BrowseScreen on mount; BrowseScreen (_browse.py, new) owns the tree+reader layout/bindings/refresh_tree; ReaderScreen (_tui/_reader.py, alongside ReaderPanel) wraps ReaderPanel standalone, pops on escape. Behavior-preserving -- ReaderPanel/_tree.py contracts unchanged.
  - Verified: migrated tests/tui/test_ui_app_behavior.py -> test_browse_screen.py (app.query_one -> app.screen.query_one, same assertions, all 10 green); added test_reader_screen.py pushing ReaderScreen directly (loads item, escape pops); grep confirms _app->_browse, _browse->_reader/_tree, no widget imports a screen. Full tests/tui/ (16) + whole-repo pyright/ruff clean.
<!-- sq:discussion:end -->
