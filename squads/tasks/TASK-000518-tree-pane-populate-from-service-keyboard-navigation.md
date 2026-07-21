---
id: TASK-518
sequence_id: 518
type: task
title: 'Tree pane: populate from Service + keyboard navigation'
status: InReview
parent: FEAT-513
author: tech-lead
refs:
- TASK-517:depends-on
subentities:
- local_id: ST1
  title: Populate tree from svc.tree_view matching sq tree
  status: Done
  story: US2
- local_id: ST2
  title: Keyboard navigation with visible selection indicator
  status: Done
  story: US3
created_at: '2026-07-21T09:18:49Z'
updated_at: '2026-07-21T10:01:34Z'
---
<!-- sq:body -->
## Scope

Fill the `sq ui` shell (built in the foundation task) with the item tree: populate a Textual
`Tree` widget from the in-process read layer so it matches what `sq tree` renders, and make the
selection navigable by keyboard. Depends on the foundation task's `_tui` package + `sq ui`
command. Still no reader panel.

## What to build

- In `squads/_tui/`, add the tree screen/widget: a Textual `Tree` populated from the in-process
  `Service` — call `svc.tree_view()` (the same call `sq tree` uses) and build the tree nodes
  from the returned `TreeNode` forest (`node.item`, `node.children`, `node.path_only`).
  **Do not** shell out to `sq tree --json` and **do not** reimplement traversal or ID handling —
  consume `tree_view` directly.
- `Service` read methods are `async`; call them from Textual's async lifecycle (e.g. `on_mount`
  / a worker) — awaiting inside Textual's own loop is correct here. The `Service` handle (or the
  resolved squad dir to build it via `open_service`) is passed in from the `sq ui` command; the
  app must not construct a second read path.
- Load the tree **once at launch** reflecting current on-disk state (no live-reload — explicitly
  out of scope per the feature's non-goals).
- Each tree row shows enough to identify the item as `sq tree` does (id + title; type nesting is
  conveyed by the tree structure). Escape any `[...]`-bearing content so it is not mis-read as
  markup.
- Keyboard navigation via the `Tree` widget's built-in bindings: move between siblings
  (up/down), expand into a node's children, collapse/step back out to the parent, with a visible
  current-selection indicator at all times. Verify it works with keyboard only (no mouse) over a
  plain terminal.

## Constraints (from ADR-516 — binding)

- In-process `Service` read layer only; read-only (query/get/tree methods, no mutation).
- `_tui` imports only `_services` / `_models` / `_rendering`; acyclic graph preserved.

## Acceptance (what the reviewer/QA checks)

- The tree pane shows every item type in the hierarchy with the same parent/child nesting
  `sq tree` prints for the same squad; a spot-comparison against `sq tree` matches.
- Items added/changed since the previous run appear on a fresh `sq ui` launch (state read at
  launch).
- Keyboard alone moves selection between siblings, into children, and back to the parent; the
  current selection is always visibly indicated.
- Works over a plain SSH/no-GUI terminal, no mouse required.
- Behaviour is driven by `svc.tree_view()`; a grep confirms no `--json`/subprocess call and no
  re-implemented tree walk in `_tui`.
- `uv run pyright && uv run ruff check . && uv run ruff format --check .` clean; a service/CLI
  test asserts the tree is built from a `tree_view` result (e.g. node count/structure for a
  known fixture squad).

## Story mapping

Satisfies **FEAT-513 / US2 — "Tree matches sq tree at launch"** and **US3 — "Navigate siblings,
into children, back to parent"**. Add two subtasks: one `--story US2` (populated tree matches
`sq tree`), one `--story US3` (keyboard navigation + visible selection).
<!-- sq:body:end -->

## Subtasks

_Add with `sq task 518 add-subtask "<title>"`; track with `sq task 518 subtask <n> update --status <Status>`._

<!-- sq:summary -->
| Subtask | Status | Assignee | Title | Story |
| --- | --- | --- | --- | --- |
| ST1 | Done |  | Populate tree from svc.tree_view matching sq tree | US2 |
| ST2 | Done |  | Keyboard navigation with visible selection indicator | US3 |
<!-- sq:summary:end -->

<!-- sq:subtasks -->

<!-- sq:subtask:ST1 -->
### ST1 — Populate tree from svc.tree_view matching sq tree

<!-- sq:subtask:ST1:head -->
**Status:** 🟢 Done
**Implements:** US2 — Tree matches sq tree at launch
<!-- sq:subtask:ST1:head:end -->

<!-- sq:subtask:ST1:body -->
Build the Textual Tree from svc.tree_view() (async, from Textual's loop), mirroring sq tree's parent/child nesting; load once at launch. No --json, no re-implemented traversal. Done: tree structure matches sq tree for the same squad.
<!-- sq:subtask:ST1:body:end -->

#### Discussion

<!-- sq:subtask:ST1:discussion -->
<!-- sq:subtask:ST1:discussion:end -->
<!-- sq:subtask:ST1:end -->

<!-- sq:subtask:ST2 -->
### ST2 — Keyboard navigation with visible selection indicator

<!-- sq:subtask:ST2:head -->
**Status:** 🟢 Done
**Implements:** US3 — Navigate siblings, into children, back to parent
<!-- sq:subtask:ST2:head:end -->

<!-- sq:subtask:ST2:body -->
Keyboard-only navigation via the Tree widget: siblings up/down, expand into children, collapse/step out to parent, with an always-visible current-selection indicator; works over a plain no-mouse terminal. Done: all three moves work by keyboard with visible selection.
<!-- sq:subtask:ST2:body:end -->

#### Discussion

<!-- sq:subtask:ST2:discussion -->
<!-- sq:subtask:ST2:discussion:end -->
<!-- sq:subtask:ST2:end -->
<!-- sq:subtasks:end -->

## Discussion

<!-- sq:discussion -->
- [2026-07-21T10:01:34Z] Elias Python:
  - Built: squads/_tui/_tree.py populates a Textual Tree from svc.tree_view() (node.item/children/path_only) -- no --json, no reimplemented traversal; fully expanded at launch to match sq tree's default display. Keyboard nav is Tree's built-in bindings (up/down/shift+left/enter/space) -- no custom key handling needed.
  - Verified: tests/cli/test_ui_app_behavior.py asserts tree structure == svc.tree_view() for a fixture hierarchy, and keyboard-only down/down/shift+left moves through siblings, into children, and back to parent with the cursor always on a real node.
<!-- sq:discussion:end -->
