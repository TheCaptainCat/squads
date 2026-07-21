---
id: TASK-520
sequence_id: 520
type: task
title: 'Reader panel: sub-entities and discussion tabs with empty states'
status: Done
parent: FEAT-514
author: tech-lead
refs:
- TASK-519:depends-on
subentities:
- local_id: ST1
  title: Sub-entities tab with empty state
  status: Done
  story: US3
- local_id: ST2
  title: Discussion tab with empty state
  status: Done
  story: US3
created_at: '2026-07-21T09:18:54Z'
updated_at: '2026-07-21T12:05:13Z'
---
<!-- sq:body -->
## Scope

Complete the reader panel's `TabbedContent` with the two remaining tabs — sub-entities and
discussion — each keyboard-switchable and each with a clean empty state. Depends on the reader
shell + body tab task (this adds tabs to the same `TabbedContent`).

## What to build

- **Sub-entities tab**: list the selected item's stories / subtasks / findings — whichever kind
  applies to its type. Resolve the kind from the active spec (`svc.spec.item_subentity_kind(
  item.type)`) and read the rows from `item.subentities` (or the corresponding
  `svc.list_stories` / `list_subtasks` / `list_findings`). For each sub-entity show its status,
  assignee, and title. Prefer the shared field-driven column derivation the CLI uses
  (`_discussion.summary_columns` / `summary_row`) so the tab does not drift from `sq … show`.
  A type with no sub-entity kind, or an item with none, shows an empty state — not an error.
- **Discussion tab**: show the item's comment history in order, author + timestamp per entry.
  Read the region via `svc.read_discussion(item_id)` and parse it with
  `_discussion.split_discussion(...)` into `Comment` records (`timestamp`, `author`, `body`) —
  do not re-parse the markers by hand. An item with no discussion shows an empty state.
- Both tabs live in the same `TabbedContent` as the body tab and are switchable **by keyboard**;
  changing the tree selection refreshes all tabs for the newly selected item.
- Escape `[...]`-bearing content (titles, comment bodies) so Rich does not treat it as markup.

## Constraints (from ADR-516 — binding)

- In-process `Service` read layer only; read-only (`read_discussion`, sub-entity list/query, spec
  lookups — no mutation). No `sq … --json` subprocess.
- `_tui` imports only `_services` / `_models` / `_rendering`; acyclic graph preserved.

## Acceptance (what the reviewer/QA checks)

- The sub-entities tab lists the item's stories/subtasks/findings (as applies to its type) with
  status, assignee, and title each visible.
- The discussion tab shows comments in order, each with author and timestamp.
- An item with no sub-entities, and one with no discussion, each show an empty state rather than
  an error (verified on a type that has no sub-entity kind too).
- Tabs (body / sub-entities / discussion) are switchable with the keyboard alone.
- Discussion parsing goes through `_discussion.split_discussion`; sub-entity rows go through the
  shared summary derivation — a grep confirms no hand-rolled marker parsing in `_tui`.
- `uv run pyright && uv run ruff check . && uv run ruff format --check .` clean; service/CLI
  tests assert sub-entity rows and parsed comments for known fixture items, plus the empty-state
  paths.

## Story mapping

Satisfies **FEAT-514 / US3 — "Sub-entities and discussion as tabs"**. Add two subtasks:
`--story US3` for the sub-entities tab and `--story US3` for the discussion tab (both map to the
same story; split for reviewability).
<!-- sq:body:end -->

## Subtasks

_Add with `sq task 520 add-subtask "<title>"`; track with `sq task 520 subtask <n> update --status <Status>`._

<!-- sq:summary -->
| Subtask | Status | Assignee | Title | Story |
| --- | --- | --- | --- | --- |
| ST1 | Done |  | Sub-entities tab with empty state | US3 |
| ST2 | Done |  | Discussion tab with empty state | US3 |
<!-- sq:summary:end -->

<!-- sq:subtasks -->

<!-- sq:subtask:ST1 -->
### ST1 — Sub-entities tab with empty state

<!-- sq:subtask:ST1:head -->
**Status:** 🟢 Done
**Implements:** US3 — Sub-entities and discussion as tabs
<!-- sq:subtask:ST1:head:end -->

<!-- sq:subtask:ST1:body -->
Sub-entities tab: resolve kind via spec.item_subentity_kind(item.type), list rows from item.subentities using the shared summary_columns/summary_row derivation (status/assignee/title); empty state when the type has no kind or the item has none. Done: rows show for applicable types, empty state otherwise.
<!-- sq:subtask:ST1:body:end -->

#### Discussion

<!-- sq:subtask:ST1:discussion -->
<!-- sq:subtask:ST1:discussion:end -->
<!-- sq:subtask:ST1:end -->

<!-- sq:subtask:ST2 -->
### ST2 — Discussion tab with empty state

<!-- sq:subtask:ST2:head -->
**Status:** 🟢 Done
**Implements:** US3 — Sub-entities and discussion as tabs
<!-- sq:subtask:ST2:head:end -->

<!-- sq:subtask:ST2:body -->
Discussion tab: read svc.read_discussion + _discussion.split_discussion into Comment records; show comments in order with author + timestamp; empty state when none. Keyboard-switchable alongside body/sub-entities tabs. Done: ordered comments with author/timestamp, empty state when none.
<!-- sq:subtask:ST2:body:end -->

#### Discussion

<!-- sq:subtask:ST2:discussion -->
<!-- sq:subtask:ST2:discussion:end -->
<!-- sq:subtask:ST2:end -->
<!-- sq:subtasks:end -->

## Discussion

<!-- sq:discussion -->
- [2026-07-21T10:02:07Z] Elias Python:
  - Built: sub-entities tab resolves kind via spec.item_subentity_kind + renders rows through discussion.summary_columns/summary_row (same derivation sq show uses); discussion tab reads svc.read_discussion + discussion.split_discussion into Comment records -- no hand-rolled marker parsing. Both empty-state ('(none)') for no-kind types, kind-but-no-rows, and no-discussion. All three tabs (body/sub-entities/discussion) share one TabbedContent, switchable by keyboard (Tabs' left/right when focused).
  - Verified: tests/cli/test_ui_app_behavior.py -- sub-entities tab lists story rows (status/assignee/title) and empty-states for a role (no kind) and a story-less feature; discussion tab shows ordered comments with author+timestamp and empty-states when none; keyboard right/right cycles body -> sub-entities -> discussion.
<!-- sq:discussion:end -->
