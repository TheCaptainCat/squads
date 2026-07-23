---
id: TASK-598
sequence_id: 598
type: task
title: 'TUI: group the tree by category with a third records root'
status: Done
parent: FEAT-570
author: tech-lead
assignee: python-dev
priority: medium
created_at: '2026-07-22T13:00:55Z'
updated_at: '2026-07-23T07:09:22Z'
---
<!-- sq:body -->
Implements FEAT-570 US2 (TUI records root). Switch the browse tree's grouping from the roster/not-roster boolean to `category`, adding a third `records` root alongside Work and Roster. Depends on US1 (TASK-595 category on the wire / spec accessor).

## VISUAL — requires operator dev-host visual acceptance
This changes rendered TUI layout. It lands **InReview**, not auto-accepted: the operator (Pierre) must visually verify it on the Windows `code`/terminal dev-host before it moves to Done. Include a short "how to see it" note in the handoff (which command launches the TUI, what the third root should look like).

## Scope
- `src/squads/_tui/_tree.py::populate_tree` currently builds two synthetic roots (Work / Roster) and routes each node via `spec.item_is_roster(...)`. Replace with a three-way split on `spec.items[type].category`: Work, Records, Roster. Records-category items (decision/contract/guide + any custom) move under the new Records root.
- Fixed root order and each root always present even when empty (mirror the roster provider's always-present buckets). Keep the `Text.assemble` label construction (bracket-safe) unchanged.
- Read the split from the spec accessor (single source), consistent with US1 — do not re-derive a roster/work/records list in the TUI.

## Acceptance
- The tree shows three roots (Work / Records / Roster); ADRs/guides/contracts appear under Records, work items under Work, roster under Roster.
- Empty roots render without error.
- TUI-level test asserting node placement by category.
- Operator dev-host visual sign-off recorded before Done.

## Gates
`uv run --all-extras pyright && uv run --all-extras ruff check . && uv run --all-extras ruff format --check . && uv run --all-extras pytest` (the `tui` extra MUST be present for the TUI tests). Leave `sq check` clean.

## Role colour
Alongside the category grouping above, render each tree row's colour from its status role: join status -> role via the roles catalog and map role.color intent to a Textual attribute, with a neutral fallback for an unrecognised intent. Depends on FEAT-605.
<!-- sq:body:end -->

## Subtasks

_Add with `sq task 598 add-subtask "<title>"`; track with `sq task 598 subtask <n> update --status <Status>`._

<!-- sq:summary -->
<!-- sq:summary:end -->

<!-- sq:subtasks -->
<!-- sq:subtasks:end -->

## Discussion

<!-- sq:discussion -->
- [2026-07-22T17:26:28Z] Elias Python:
  - Replaced the Work/Roster two-way split in _tui/_tree.py::populate_tree with a fixed-order three-root split (Work/Records/Roster), each root always present via spec.items[type].category (no re-derived list). Rides ADR-604: row status text is now coloured by spec.role_for(status).color, mapped through a local TUI-owned intent->Rich-style dict (positive=green, danger=red, warning=yellow, info=cyan, muted=bright_black, neutral=no override), plus spec.hidden_by_default(type,status) dims the whole row like path_only ancestors already did.
  - Tests: tests/tui/test_browse_screen.py (3-root split + empty-Records-root render), tests/tui/test_status_role_colour.py (colour mapping + hidden dimming), tests/tui/test_bracket_content_renders_safely.py comment tweak.
  - How to see it: uv run sq ui in a squad with a decision/guide item — tree now shows Work / Records / Roster roots; a decision node sits under Records; InProgress rows render green, Blocked rows red, Done rows dimmed.
  - Gates: pyright/ruff check/ruff format --all-extras clean; targeted uv run --all-extras pytest tests/tui -q (44 passed); sq check clean. Leaving InReview for the operator dev-host visual pass.
<!-- sq:discussion:end -->
