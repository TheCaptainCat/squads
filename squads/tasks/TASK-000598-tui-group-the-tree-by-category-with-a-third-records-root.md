---
id: TASK-598
sequence_id: 598
type: task
title: 'TUI: group the tree by category with a third records root'
status: Draft
parent: FEAT-570
author: tech-lead
priority: medium
created_at: '2026-07-22T13:00:55Z'
updated_at: '2026-07-22T13:03:37Z'
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
<!-- sq:body:end -->

## Subtasks

_Add with `sq task 598 add-subtask "<title>"`; track with `sq task 598 subtask <n> update --status <Status>`._

<!-- sq:summary -->
<!-- sq:summary:end -->

<!-- sq:subtasks -->
<!-- sq:subtasks:end -->

## Discussion

<!-- sq:discussion -->
<!-- sq:discussion:end -->
