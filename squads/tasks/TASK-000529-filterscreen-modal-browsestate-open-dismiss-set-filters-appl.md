---
id: TASK-529
sequence_id: 529
type: task
title: 'FilterScreen modal + BrowseState: open/dismiss, set filters, apply'
status: Done
parent: FEAT-525
author: tech-lead
refs:
- TASK-528:depends-on
subentities:
- local_id: ST1
  title: Open/dismiss popup; seed from and dismiss BrowseState
  status: Done
  story: US1
- local_id: ST2
  title: ItemFilter dimensions; apply -> refresh_tree keeps ancestors
  status: Done
  story: US2
created_at: '2026-07-21T12:20:36Z'
updated_at: '2026-07-21T14:37:57Z'
---
<!-- sq:body -->
## Scope

The filter popup's core: a modal filter screen seeded from and returning the browse view's
state, plus the shared frozen state object it edits. Covers opening/dismissing the popup by
keyboard and setting the `ItemFilter` dimensions so applying re-renders the tree, keeping
ancestors of matches visible. Depends on the screen-stack refactor. Show-closed, sort, clear,
and the active-filter indicator are the follow-up task.

## What to build

Per ADR-527 §2:

- **`BrowseState`** — a `@dataclass(frozen=True)` on `BrowseScreen` (in `_tui/_browse.py`) with
  `filter: ItemFilter`, `include_closed: bool`, `sort: SortKey`. Define `SortKey` here too (an
  enum/simple type; the sibling-sort behaviour it drives lands in the follow-up task — for this
  task it exists and defaults to sequence/id order). Initial state reproduces today's browse:
  empty `ItemFilter`, `include_closed=False`, id/sequence order. `BrowseScreen` holds the live
  `state` instance; because it stays mounted under the modal, state persists across popup opens
  for free.
- **`FilterScreen`** (`ModalScreen`) in a new `_tui/_filter.py`: constructed with the current
  `BrowseState` (seeded so it opens pre-populated), pushed over `BrowseScreen` (which stays
  mounted and dimmed). Offers each `ItemFilter` dimension — item type, status, assignee, label,
  and a badge field such as priority (spec-generic via the active spec's fields, not hard-coded
  to priority). On apply it `dismiss(...)`es a **new** `BrowseState`; on cancel/escape it
  `dismiss(None)`.
- **Open / apply plumbing on `BrowseScreen`**: a filter key binding does
  `push_screen(FilterScreen(self.state), self._apply)` (callback form, not a worker). `_apply`
  returns on `None`; otherwise sets `self.state` and calls `refresh_tree()`.
- **`refresh_tree()`** on `BrowseScreen`: re-runs `tree_view(filter=self.state.filter,
  include_closed=self.state.include_closed)` and repopulates the `Tree` (reuse `_tree.py`'s
  populate path). Because `tree_view` already returns matches plus their ancestors (the
  `path_only` context nodes), applying a filter keeps ancestors visible as context automatically
  — do not re-implement pruning.
- `FilterScreen` imports no other `_tui` module (ADR-527 §4); `BrowseScreen` imports
  `_filter`.

## Constraints (ADR-516 + ADR-527, binding)

- In-process `Service`, read-only (`tree_view` + spec field lookups only). No `--json`
  subprocess.
- Async `tree_view` awaited on Textual's loop inside the `_apply` refresh; no `anyio.run`.
- Import direction preserved; graph acyclic; `_filter` depends on no other `_tui` module.

## Acceptance (what the reviewer/QA checks)

- A keyboard shortcut over the browse tree opens the popup pre-populated from the current state;
  Escape dismisses it without applying pending changes (tree unchanged).
- The popup exposes item type, status, assignee, label, and a spec-declared badge field; setting
  one or more and applying updates the tree to matches while ancestors of matches remain visible
  as context (matching `sq tree`'s match+ancestor behaviour).
- Applying returns a new `BrowseState` via `dismiss`; the browse view holds the updated state and
  a subsequent open is seeded from it (state persists across opens).
- Everything is reachable by keyboard alone (no mouse), works over a plain terminal.
- Driven by `tree_view(filter=…, include_closed=…)`; a grep confirms no re-implemented
  match/ancestor pruning and no `--json`/subprocess in `_tui`.
- `uv run pyright && uv run ruff check . && uv run ruff format --check .` clean; a TUI test
  asserts open→set a dimension→apply narrows the tree and keeps an ancestor visible, and
  escape leaves it unchanged.

## Story mapping

Satisfies **FEAT-525 / US1 — "Open/dismiss the filter+sort popup by keyboard"** and **US2 —
"Set filters and apply, tree updates keeping ancestors as context"**. Add two subtasks: one
`--story US1` (open/dismiss + seed/dismiss plumbing), one `--story US2` (filter dimensions +
apply/refresh_tree keeping ancestors).
<!-- sq:body:end -->

## Subtasks

_Add with `sq task 529 add-subtask "<title>"`; track with `sq task 529 subtask <n> update --status <Status>`._

<!-- sq:summary -->
| Subtask | Status | Assignee | Title | Story |
| --- | --- | --- | --- | --- |
| ST1 | Done |  | Open/dismiss popup; seed from and dismiss BrowseState | US1 |
| ST2 | Done |  | ItemFilter dimensions; apply -> refresh_tree keeps ancestors | US2 |
<!-- sq:summary:end -->

<!-- sq:subtasks -->

<!-- sq:subtask:ST1 -->
### ST1 — Open/dismiss popup; seed from and dismiss BrowseState

<!-- sq:subtask:ST1:head -->
**Status:** 🟢 Done
**Implements:** US1 — Open/dismiss the filter+sort popup by keyboard
<!-- sq:subtask:ST1:head:end -->

<!-- sq:subtask:ST1:body -->
Filter key binding on BrowseScreen does push_screen(FilterScreen(self.state), self._apply) (callback form). FilterScreen is a ModalScreen seeded with the current BrowseState so it opens pre-populated; apply dismiss()es a new BrowseState, escape/cancel dismiss(None). _apply returns on None. Done: open pre-populated, escape leaves tree unchanged, state persists across opens.
<!-- sq:subtask:ST1:body:end -->

#### Discussion

<!-- sq:subtask:ST1:discussion -->
<!-- sq:subtask:ST1:discussion:end -->
<!-- sq:subtask:ST1:end -->

<!-- sq:subtask:ST2 -->
### ST2 — ItemFilter dimensions; apply -> refresh_tree keeps ancestors

<!-- sq:subtask:ST2:head -->
**Status:** 🟢 Done
**Implements:** US2 — Set filters and apply, tree updates keeping ancestors as context
<!-- sq:subtask:ST2:head:end -->

<!-- sq:subtask:ST2:body -->
FilterScreen offers item type, status, assignee, label, and a spec-declared badge field (generic via the active spec's fields, not hard-coded to priority). refresh_tree() re-runs tree_view(filter=state.filter, include_closed=state.include_closed) and repopulates via _tree.py; ancestors stay visible because tree_view already returns match+ancestor (path_only) nodes. Done: applying a dimension narrows the tree, an ancestor of a match stays visible, no re-implemented pruning.
<!-- sq:subtask:ST2:body:end -->

#### Discussion

<!-- sq:subtask:ST2:discussion -->
<!-- sq:subtask:ST2:discussion:end -->
<!-- sq:subtask:ST2:end -->
<!-- sq:subtasks:end -->

## Discussion

<!-- sq:discussion -->
- [2026-07-21T12:48:22Z] Elias Python:
  - Built: BrowseState/SortKey (frozen dataclasses) on _browse.py; FilterScreen (_filter.py, ModalScreen) offers type/status/assignee/label + one spec-generic badge field (union of fields_for() across all work types, not hard-coded to priority); apply/cancel via Button + escape binding. 'f' opens push_screen(FilterScreen(state, spec), self._apply_filter); _apply_filter is an async callback (Textual supports async ScreenResultCallbackType) that sets state and awaits refresh_tree(). refresh_tree() threads filter+include_closed into tree_view -- ancestors of matches stay visible for free (tree_view's own path_only nodes), no re-implemented pruning.
  - Import direction: FilterScreen imports zero _tui modules at runtime (BrowseState only under TYPE_CHECKING; new BrowseState/ItemFilter built via dataclasses.replace() on the seed instance, never by importing the class) -- grep confirms. Verified via 3 new Pilot tests (test_filter_screen.py): escape leaves the tree/state unchanged, applying a type filter narrows the tree keeping an ancestor visible, and a later re-open is seeded from the applied state. Full tests/tui/ (19) + whole-repo pyright/ruff clean.
<!-- sq:discussion:end -->
