---
id: ADR-527
sequence_id: 527
type: decision
title: TUI screen & modal navigation model for sq ui (filter + search)
status: Accepted
parent: EPIC-28
author: architect
refs:
- ADR-516
created_at: '2026-07-21T12:16:25Z'
updated_at: '2026-07-21T12:18:39Z'
---
<!-- sq:body -->
# Context

The `sq ui` browse-first increment ships a single view: an item `Tree` on the left, a
tabbed `ReaderPanel` on the right, both composed directly on the Textual `App`'s default
screen (no `Screen` subclass yet). The next increment adds two surfaces on top of that
view — a **filter/sort popup** and a **full-text search** — and future increments (mutation)
will add more. This decision pins the screen and navigation model the whole `_tui` package
grows on, so each new surface plugs into the same shape instead of being bolted onto the
`App` ad hoc.

It sits strictly inside the frame ADR-516 already fixed: in-process `Service`, read-only for
this increment, a plain synchronous `sq ui` command that hands off to Textual's own event
loop (never the CLI's `anyio.run` bridge), and an acyclic `_tui` import graph that nothing in
the core path imports at module load.

No new **service** capability is introduced. Filtering already exists — `tree_view(filter=…,
include_closed=…)` takes an `ItemFilter` and an open/closed toggle. Search already exists —
`search(text, item_type=…, status=…)` returns `SearchResult`/`SearchHit`. The decisions here
are entirely about **TUI structure**: how these existing calls are surfaced through screens.

# Decision

## 1. Every surface is a `Screen`; the App is a thin shell

Promote the browse view out of the `App` body into a `BrowseScreen`. The `App` becomes a
shell that holds the in-process `Service` handle and, on mount, pushes `BrowseScreen`. From
then on the App composes nothing itself — every surface is a screen on the stack:

- **`BrowseScreen`** (full `Screen`) — the tree + reader layout and its key bindings. It is
  the base of the stack and the only screen that owns the shared browse state (§2).
- **`FilterScreen`** (`ModalScreen`) — the filter/sort popup. Pushed over `BrowseScreen`,
  which stays mounted and dimmed underneath. Modal semantics are exactly what a popup wants:
  the browse view is visible but inert until the popup resolves.
- **`SearchScreen`** (full `Screen`) — a query input over a results list. Pushed over
  `BrowseScreen`; it fully replaces the view because search is its own mode, not an overlay.
- **`ReaderScreen`** (full `Screen`) — a standalone item reader that wraps the existing
  `ReaderPanel` widget (§3). Reused wherever an item must be opened outside the browse tree.

Invocation is by key binding on `BrowseScreen` (the concrete keys are the tech-lead's to set):
a filter key does `push_screen(FilterScreen(...), callback)`; a search key does
`push_screen(SearchScreen(...))`. Escape / cancel calls `dismiss(...)` on the top screen,
which `pop_screen`s it. Focus needs no manual handling — Textual restores focus to the screen
beneath on pop, so escaping any surface lands back on the tree with its selection intact.

## 2. Filter/sort state lives on `BrowseScreen`; the popup returns a value via dismiss

The active view state is a small frozen dataclass held on the `BrowseScreen` instance:

```python
@dataclass(frozen=True)
class BrowseState:
    filter: ItemFilter
    include_closed: bool
    sort: SortKey
```

Because `BrowseScreen` stays mounted underneath the modal, this state persists across popup
opens for free — the popup is *seeded* from the current state (passed to `FilterScreen`'s
constructor) so it opens pre-populated, and it returns a **new** `BrowseState` (or `None` for
cancel) as its dismiss value:

```python
def open_filter(self) -> None:
    self.app.push_screen(FilterScreen(self.state), self._apply)

def _apply(self, result: BrowseState | None) -> None:
    if result is None:
        return
    self.state = result
    self.refresh_tree()
```

`refresh_tree()` re-runs `tree_view(filter=self.state.filter,
include_closed=self.state.include_closed)` and repopulates the `Tree`. The callback form of
`push_screen` (not a worker + `push_screen_wait`) is chosen because the flow is a single
fire-and-return with no surrounding async work to suspend.

**Sort is applied TUI-side**, not pushed into the service. `tree_view` returns a
sequence-ordered forest; a chosen `SortKey` reorders siblings within that returned forest
before it is handed to the tree population — a pure presentation reordering that keeps the
"no new service capability" line. The initial `BrowseState` reproduces today's behaviour:
empty `ItemFilter`, `include_closed=False`, sequence order.

## 3. A search hit opens in a pushed `ReaderScreen`, reusing `ReaderPanel`

Selecting a result in `SearchScreen` pushes a `ReaderScreen` for that item id, which loads it
into a `ReaderPanel` — the same widget the browse view already uses. Escape pops the reader
back to the results; escape again pops back to browse.

A pushed reader is chosen over "navigate the browse tree to the item" because search runs over
the whole corpus (its own `item_type`/`status` filter), so a hit can be an item the browse
tree is currently filtering out — closed, or excluded by the active `ItemFilter`. Navigating
the tree would fail for those items and would silently move the browse position as a side
effect of a search. A pushed `ReaderScreen` opens **any** hit deterministically, leaves the
browse view's state untouched, and reuses the one reader implementation rather than growing a
second. It stays read-only: `ReaderScreen` calls only the panel's existing load path.

This makes `ReaderPanel` a shared widget used in two hosts (embedded in browse, standalone in
`ReaderScreen`); it already takes just a `Service` and an item id, so no change to its contract.

## 4. Module placement & the loop

Keep the flat `_tui/` layout that is already in place; add one module per new screen:

- `_tui/_app.py` — the `App` shell (holds `Service`, pushes `BrowseScreen`).
- `_tui/_browse.py` — `BrowseScreen` + `BrowseState` + `SortKey`.
- `_tui/_filter.py` — `FilterScreen` (`ModalScreen`).
- `_tui/_search.py` — `SearchScreen`.
- `_tui/_reader.py` — `ReaderPanel` (existing) **and** the `ReaderScreen` that wraps it, kept
  together because they are one concern ("read an item").
- `_tui/_tree.py` — tree population (existing, unchanged).

Import direction stays one-way and acyclic: `_app` → screens; `_browse` → `_filter`, `_search`,
and the reader/tree modules; `_search` → the reader module; `_filter` imports no other `_tui`
module. Widgets never import screens. As under ADR-516, everything imports downward only into
`_services` / `_models` / `_rendering`, and nothing here is imported by the core path.

The async service calls stay on Textual's loop: `tree_view` and `search` are awaited directly
inside the screens' async message handlers (`on_mount`, input submit, the filter callback's
refresh) — never through `anyio.run`. A long-running search may be wrapped in a Textual worker
(`@work(exclusive=True)`) so keystrokes stay responsive; that is a responsiveness detail within
this model, not a change to it.

# Consequences

- The stack is uniform: browse, filter, search, and reader are all screens, so future
  surfaces (a mutation form, a help overlay) push onto the same model with no App-level
  special-casing.
- View state has one home (`BrowseState` on `BrowseScreen`) and a single re-render path
  (`refresh_tree`), so filter, sort, and open/closed changes all flow through the same seam.
- Search is self-contained: it can open any matching item regardless of the browse filter, and
  never perturbs the browse position — at the cost that a hit and the tree selection are
  independent, which is the intended read-only behaviour.
- The reader exists once and is reused in both hosts; a later mutation increment adds actions
  to `ReaderPanel`/its screen in one place.
- The package stays flat and small; the acyclicity check and the lazy-import boundary from
  ADR-516 are unaffected.
<!-- sq:body:end -->

## Discussion

<!-- sq:discussion -->
- [2026-07-21T12:18:36Z] Catherine Manager:
  - Accepted after a full read. Build rules stand: App is a thin shell pushing BrowseScreen; FilterScreen (ModalScreen) + SearchScreen (full Screen) + ReaderScreen (wraps existing ReaderPanel) on the stack; frozen BrowseState (ItemFilter + include_closed + SortKey) owned by BrowseScreen, popup seeded from it and returns a new state via dismiss; sort is presentation-only sibling reorder; search hits open in a pushed ReaderScreen (not tree nav). Import direction acyclic per the ADR; async awaited on Textual's loop, optional @work(exclusive) for search. Note for the tech-lead: this refactors the current single-screen _app.py into BrowseScreen and updates the tests/tui suite accordingly.
<!-- sq:discussion:end -->
