---
id: TASK-530
sequence_id: 530
type: task
title: 'Filter popup: show-closed toggle, sibling sort, clear, active indicator'
status: Done
parent: FEAT-525
author: tech-lead
refs:
- TASK-529:depends-on
subentities:
- local_id: ST1
  title: Show-closed toggle reveals/hides terminal items
  status: Done
  story: US3
- local_id: ST2
  title: Sibling sort (TUI-side) + clear/reset + active-filter indicator
  status: Done
  story: US4
created_at: '2026-07-21T12:20:38Z'
updated_at: '2026-07-21T14:37:57Z'
---
<!-- sq:body -->
## Scope

Complete the filter popup: the show-closed toggle, presentation-only sibling sort, a
clear/reset action, and a visible active-filter indicator on the browse view. Extends the
`FilterScreen`/`BrowseScreen`/`BrowseState` built in the previous task. Depends on it.

## What to build

- **Show-closed toggle** in `FilterScreen`, bound to `BrowseState.include_closed`. Applying with
  it on makes `refresh_tree()` pass `include_closed=True` to `tree_view`, revealing terminal/Done
  items; off hides them again. (This is the answer to "no way to display terminal/Done items.")
- **Sibling sort — applied TUI-side, not in the service** (ADR-527 §2). `BrowseState.sort`
  (`SortKey`) selects one of: id/sequence (default), a badge field (e.g. priority), status,
  title, or last-updated. `tree_view` returns a sequence-ordered forest; reorder **siblings
  within each level** of that returned forest before handing it to the tree population — a pure
  presentation reordering (recurse into children; never reorder across levels). Do not push a
  sort into the service and do not add a service capability. Read the sort keys off the `Item`
  (title, status, `updated_at`, `badge_value(<field>)`); id order is default when no sort chosen.
- **Clear/reset**: one action in the popup returns every filter dimension to unset, show-closed
  off, and sort to default, in a single step — then apply reproduces the initial browse view.
- **Active-filter indicator** on `BrowseScreen`: a visible marker whenever any filter dimension
  (or show-closed, or a non-default sort) is active, so a short/empty tree is never mistaken for
  "no more items". Derive the indicator from `BrowseState` (e.g. non-empty `ItemFilter` /
  include_closed / non-default sort); clear it when state returns to default.

## Constraints (ADR-516 + ADR-527, binding)

- In-process `Service`, read-only. Sort is presentation-only — no new service capability, no
  `--json` subprocess.
- Async `tree_view` on Textual's loop; no `anyio.run`.
- Import direction preserved (`_filter` imports no other `_tui`); graph acyclic.

## Acceptance (what the reviewer/QA checks)

- Toggling show-closed on reveals terminal/Done items in the tree; toggling off hides them.
- Choosing a sort dimension reorders siblings at every level (id, badge field, status, title,
  last-updated); id/sequence order is the default; sort is verified applied TUI-side (siblings
  reorder within a parent, ordering across levels never changes) with no service call carrying a
  sort argument.
- Clear/reset returns filters, show-closed, and sort to default in one step; applying then
  reproduces the initial unfiltered view.
- The active-filter indicator is visible while any dimension/show-closed/non-default sort is
  active and absent at default.
- All reachable by keyboard alone over a plain terminal.
- `uv run pyright && uv run ruff check . && uv run ruff format --check .` clean; TUI tests assert
  show-closed reveal/hide, sibling reorder for a sort key, clear→default, and indicator
  on/off.

## Story mapping

Satisfies **FEAT-525 / US3 — "Show-closed toggle reveals and hides terminal items"** and **US4 —
"Choose sibling sort order, clear/reset filters, see active-filter indicator"**. Add two
subtasks: one `--story US3` (show-closed toggle), one `--story US4` (sort + clear/reset +
indicator).
<!-- sq:body:end -->

## Subtasks

_Add with `sq task 530 add-subtask "<title>"`; track with `sq task 530 subtask <n> update --status <Status>`._

<!-- sq:summary -->
| Subtask | Status | Assignee | Title | Story |
| --- | --- | --- | --- | --- |
| ST1 | Done |  | Show-closed toggle reveals/hides terminal items | US3 |
| ST2 | Done |  | Sibling sort (TUI-side) + clear/reset + active-filter indicator | US4 |
<!-- sq:summary:end -->

<!-- sq:subtasks -->

<!-- sq:subtask:ST1 -->
### ST1 — Show-closed toggle reveals/hides terminal items

<!-- sq:subtask:ST1:head -->
**Status:** 🟢 Done
**Implements:** US3 — Show-closed toggle reveals and hides terminal items
<!-- sq:subtask:ST1:head:end -->

<!-- sq:subtask:ST1:body -->
Show-closed toggle in FilterScreen bound to BrowseState.include_closed; applying with it on passes include_closed=True to tree_view, revealing terminal/Done items; off hides them. Done: toggle reveals/hides terminal items in the tree.
<!-- sq:subtask:ST1:body:end -->

#### Discussion

<!-- sq:subtask:ST1:discussion -->
<!-- sq:subtask:ST1:discussion:end -->
<!-- sq:subtask:ST1:end -->

<!-- sq:subtask:ST2 -->
### ST2 — Sibling sort (TUI-side) + clear/reset + active-filter indicator

<!-- sq:subtask:ST2:head -->
**Status:** 🟢 Done
**Implements:** US4 — Choose sibling sort order, clear/reset filters, see active-filter indicator
<!-- sq:subtask:ST2:head:end -->

<!-- sq:subtask:ST2:body -->
SortKey on BrowseState reorders siblings within each level of the tree_view forest TUI-side before population (id default, badge field, status, title, last-updated via Item fields; recurse, never across levels); no sort pushed to the service. Clear/reset returns filters+show-closed+sort to default in one step. Active-filter indicator on BrowseScreen derived from BrowseState, shown when any dimension/show-closed/non-default sort is active. Done: siblings reorder per key, clear->default, indicator on/off.
<!-- sq:subtask:ST2:body:end -->

#### Discussion

<!-- sq:subtask:ST2:discussion -->
<!-- sq:subtask:ST2:discussion:end -->
<!-- sq:subtask:ST2:end -->
<!-- sq:subtasks:end -->

## Discussion

<!-- sq:discussion -->
- [2026-07-21T12:53:59Z] Elias Python:
  - Built: show-closed Switch in FilterScreen bound to BrowseState.include_closed (already threaded through tree_view by task529's refresh_tree). Sort: SortKey now has kind (sequence/status/title/updated/badge) + badge_code; sort_siblings() in _browse.py recurses into TreeNode.children and reorders only at each level (never across) via dataclasses.replace on the frozen TreeNode, applied TUI-side in refresh_tree before populate_tree -- no sort kwarg on any tree_view call. Clear button resets the popup's own widgets to default (item stays open; Apply still required, matching 'clear then apply reproduces the initial view'). Active-filter indicator: a Static above the tree, driven by BrowseState.is_default(), updated in refresh_tree.
  - Verified: 4 new Pilot tests -- show-closed toggle reveal/hide, sort-by-title reorders siblings without moving a child across parents, clear (still-filtered until Apply) -> apply reproduces the default view, indicator on while filtered / off at default. Full tests/tui/ (23) + whole-repo pyright/ruff clean. Grep confirms no tree_view call carries a sort argument.
<!-- sq:discussion:end -->
