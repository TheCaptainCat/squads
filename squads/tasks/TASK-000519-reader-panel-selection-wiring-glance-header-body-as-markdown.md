---
id: TASK-519
sequence_id: 519
type: task
title: 'Reader panel: selection wiring, glance header, body-as-Markdown tab'
status: Done
parent: FEAT-514
author: tech-lead
refs:
- TASK-518:depends-on
subentities:
- local_id: ST1
  title: Tree selection loads item into reader panel
  status: Done
  story: US1
- local_id: ST2
  title: Body-as-Markdown tab
  status: Done
  story: US2
- local_id: ST3
  title: At-a-glance status/priority/assignee header
  status: Done
  story: US4
created_at: '2026-07-21T09:18:54Z'
updated_at: '2026-07-21T12:05:12Z'
---
<!-- sq:body -->
## Scope

Add the reader panel next to the tree: selecting a tree node loads that item's detail, shows an
at-a-glance header (status / priority / assignee) that is always visible, and renders the item's
markdown body in a body tab. This is the reader shell + body tab; the sub-entities and discussion
tabs come in the follow-up task. Depends on the tree-navigation task (selection drives the panel).

## What to build

- Split the `sq ui` layout into the existing tree pane plus a reader panel region.
- Wire tree selection → reader load: when the current tree node changes, load that item's detail
  from the in-process `Service` and update the panel. Use `svc.get(item_id)` for the `Item`
  (metadata) and `svc.read_body(item_id)` for the markdown body. Calls are `async` — invoke them
  from Textual's selection/message handlers (its own loop). Do not shell out to `--json`.
- **At-a-glance header** (a header/summary line above the tabs, visible without switching tabs):
  show status, priority, and assignee. Read status from `item.status`, assignee from
  `item.assignee`, and priority via `item.badge_value("priority")` (the spec-declared badge
  code — do not hard-code the emoji/label; resolve through the active spec / `svc.spec` as the
  CLI does). Handle "no priority"/"unassigned" gracefully (blank or a dim placeholder, not an
  error). Escape `[...]`-bearing strings so Rich does not treat them as markup.
- **Body tab** inside a `TabbedContent`: render the item's markdown body with Textual's
  `Markdown` widget (headings, lists, emphasis, code blocks rendered — not raw source). An item
  with an empty body shows a dim empty state, not an error.
- Changing the selection to another node re-loads header + body for the new item.

## Constraints (from ADR-516 — binding)

- In-process `Service` read layer only; read-only (`get`, `read_body`, spec lookups — no mutating
  calls). No `sq … --json` subprocess.
- `_tui` imports only `_services` / `_models` / `_rendering`; acyclic graph preserved.

## Acceptance (what the reviewer/QA checks)

- Selecting any tree node populates the reader panel with that item's detail; changing selection
  updates it.
- The header line shows status, priority, and assignee and stays visible without switching tabs;
  an item with no priority / no assignee renders cleanly (no crash, no raw `None`).
- The body tab renders markdown legibly (headings/lists/emphasis/code blocks), not raw markdown
  source; an empty body shows an empty state.
- Priority/status/assignee are read through the model + active spec, not hard-coded — a grep
  confirms no literal priority emoji/label baked into `_tui`.
- Driven by `svc.get` / `svc.read_body`; no `--json`/subprocess call in `_tui`.
- `uv run pyright && uv run ruff check . && uv run ruff format --check .` clean; a service/CLI
  test asserts header fields + body content for a known fixture item.

## Story mapping

Satisfies **FEAT-514 / US1 — "Selecting a node shows its detail"**, **US2 — "Body renders as
markdown"**, and **US4 — "Status/priority/assignee at a glance"**. Add three subtasks:
`--story US1` (selection → panel load), `--story US2` (body-as-Markdown tab), `--story US4`
(glance header).
<!-- sq:body:end -->

## Subtasks

_Add with `sq task 519 add-subtask "<title>"`; track with `sq task 519 subtask <n> update --status <Status>`._

<!-- sq:summary -->
| Subtask | Status | Assignee | Title | Story |
| --- | --- | --- | --- | --- |
| ST1 | Done |  | Tree selection loads item into reader panel | US1 |
| ST2 | Done |  | Body-as-Markdown tab | US2 |
| ST3 | Done |  | At-a-glance status/priority/assignee header | US4 |
<!-- sq:summary:end -->

<!-- sq:subtasks -->

<!-- sq:subtask:ST1 -->
### ST1 — Tree selection loads item into reader panel

<!-- sq:subtask:ST1:head -->
**Status:** 🟢 Done
**Implements:** US1 — Selecting a node shows its detail
<!-- sq:subtask:ST1:head:end -->

<!-- sq:subtask:ST1:body -->
Split layout into tree + reader; on tree-selection change load the item via svc.get + svc.read_body and update the panel; re-loads on reselection. In-process, read-only. Done: selecting/changing a node updates the panel.
<!-- sq:subtask:ST1:body:end -->

#### Discussion

<!-- sq:subtask:ST1:discussion -->
<!-- sq:subtask:ST1:discussion:end -->
<!-- sq:subtask:ST1:end -->

<!-- sq:subtask:ST2 -->
### ST2 — Body-as-Markdown tab

<!-- sq:subtask:ST2:head -->
**Status:** 🟢 Done
**Implements:** US2 — Body renders as markdown
<!-- sq:subtask:ST2:head:end -->

<!-- sq:subtask:ST2:body -->
Render the markdown body in a TabbedContent body tab via Textual's Markdown widget (headings/lists/emphasis/code blocks), with a dim empty state for an empty body. Done: body renders formatted, not raw source.
<!-- sq:subtask:ST2:body:end -->

#### Discussion

<!-- sq:subtask:ST2:discussion -->
<!-- sq:subtask:ST2:discussion:end -->
<!-- sq:subtask:ST2:end -->

<!-- sq:subtask:ST3 -->
### ST3 — At-a-glance status/priority/assignee header

<!-- sq:subtask:ST3:head -->
**Status:** 🟢 Done
**Implements:** US4 — Status/priority/assignee at a glance
<!-- sq:subtask:ST3:head:end -->

<!-- sq:subtask:ST3:body -->
Header/summary line above the tabs, always visible: status (item.status), assignee (item.assignee), priority via item.badge_value('priority') resolved through the active spec (no hard-coded emoji/label); graceful when unset. Done: header shows all three, no crash when priority/assignee missing.
<!-- sq:subtask:ST3:body:end -->

#### Discussion

<!-- sq:subtask:ST3:discussion -->
<!-- sq:subtask:ST3:discussion:end -->
<!-- sq:subtask:ST3:end -->
<!-- sq:subtasks:end -->

## Discussion

<!-- sq:discussion -->
- [2026-07-21T10:01:51Z] Elias Python:
  - Built: ReaderPanel (squads/_tui/_reader.py) wired to tree selection via App.on_tree_node_highlighted; loads svc.get + svc.read_body per selection. Glance header resolves status via badges.status_badge and priority via item.badge_value('priority') + badges.resolve_collection/badge_render (spec-driven, no hard-coded emoji/label); unassigned/no-priority render gracefully. Body tab uses Textual's Markdown widget with a dim placeholder for an empty body.
  - Verified: tests/cli/test_ui_app_behavior.py -- selecting/reselecting a node reloads the body; header shows resolved priority label + assignee, and gracefully shows 'unassigned' when unset; body tab mounts real MarkdownH1/MarkdownParagraph blocks (not raw source) and shows the placeholder for an explicitly empty body.
<!-- sq:discussion:end -->
