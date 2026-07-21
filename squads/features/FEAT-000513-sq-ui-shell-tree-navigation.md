---
id: FEAT-513
sequence_id: 513
type: feature
title: sq ui shell + tree navigation
status: Draft
parent: EPIC-28
author: product-owner
priority: medium
refs:
- FEAT-15:depends-on
- FEAT-19:depends-on
subentities:
- local_id: US1
  title: Launch and quit cleanly
  status: Todo
- local_id: US2
  title: Tree matches sq tree at launch
  status: Todo
- local_id: US3
  title: Navigate siblings, into children, back to parent
  status: Todo
created_at: '2026-07-21T09:11:23Z'
updated_at: '2026-07-21T09:12:37Z'
---
<!-- sq:body -->
## Capability

Running `sq ui` opens a terminal application showing the squad's hierarchy — the same
epic/feature/story/task/... tree that `sq tree` prints, but interactive: the user moves
a selection up/down/in/out through the tree with the keyboard and quits cleanly back to
the shell. This is the shell increment only — no item detail pane yet (that's the reader
panel feature) and no mutation of any kind.

Consumes the already-frozen machine surface: the tree's data comes from the same
`--json` shapes finalized in FEAT-15, resolved via the shared ID resolver from FEAT-19.
The TUI is a pure read-only consumer of that surface — it does not reimplement tree
traversal or ID handling.

## Acceptance

- `sq ui` launches a full-screen terminal application and exits cleanly on quit (no
  leftover terminal state, no traceback on normal exit).
- The tree pane shows every item type in the hierarchy, matching what `sq tree` would
  render for the same squad (parent/child nesting, collapsed/expanded structure).
- The tree reflects the current on-disk squad state at launch — items added/changed
  since the last `sq ui` run show up on a fresh launch.
- Keyboard navigation moves the selection between siblings, into a node's children, and
  back out to its parent, with a visible current-selection indicator at all times.
- Works over a plain SSH/terminal session (no GUI, no mouse required for any of the
  above).

## Non-goals (this feature)

- No item detail/reader pane — selecting a node need not show anything beyond the tree
  itself yet.
- No mutation of any kind (no status change, comment, assignment) from the TUI.
- No live-reload while the TUI is open — reflecting a change made in another terminal
  mid-session is out of scope here.
<!-- sq:body:end -->

## User Stories

_Add with `sq feature 513 add-story "As a <role>, I want … so that …"`; track with `sq feature 513 story <n> update --status <Status>`._

<!-- sq:summary -->
| Story | Status | Assignee | Title |
| --- | --- | --- | --- |
| US1 | Todo |  | Launch and quit cleanly |
| US2 | Todo |  | Tree matches sq tree at launch |
| US3 | Todo |  | Navigate siblings, into children, back to parent |
<!-- sq:summary:end -->

<!-- sq:stories -->

<!-- sq:story:US1 -->
### US1 — Launch and quit cleanly

<!-- sq:story:US1:head -->
**Status:** ⚪ Todo
<!-- sq:story:US1:head:end -->

<!-- sq:story:US1:body -->
sq ui opens a full-screen TUI and exits cleanly on quit, leaving the terminal in a normal state.
<!-- sq:story:US1:body:end -->

#### Discussion

<!-- sq:story:US1:discussion -->
<!-- sq:story:US1:discussion:end -->
<!-- sq:story:US1:end -->

<!-- sq:story:US2 -->
### US2 — Tree matches sq tree at launch

<!-- sq:story:US2:head -->
**Status:** ⚪ Todo
<!-- sq:story:US2:head:end -->

<!-- sq:story:US2:body -->
The tree pane shows the full hierarchy for the current squad, matching sq tree's structure, reflecting on-disk state as of launch.
<!-- sq:story:US2:body:end -->

#### Discussion

<!-- sq:story:US2:discussion -->
<!-- sq:story:US2:discussion:end -->
<!-- sq:story:US2:end -->

<!-- sq:story:US3 -->
### US3 — Navigate siblings, into children, back to parent

<!-- sq:story:US3:head -->
**Status:** ⚪ Todo
<!-- sq:story:US3:head:end -->

<!-- sq:story:US3:body -->
Keyboard moves the selection between sibling nodes, down into a node's children, and back out to its parent, with the current selection always visible.
<!-- sq:story:US3:body:end -->

#### Discussion

<!-- sq:story:US3:discussion -->
<!-- sq:story:US3:discussion:end -->
<!-- sq:story:US3:end -->
<!-- sq:stories:end -->

## Discussion

<!-- sq:discussion -->
<!-- sq:discussion:end -->
