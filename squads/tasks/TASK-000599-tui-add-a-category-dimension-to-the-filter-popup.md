---
id: TASK-599
sequence_id: 599
type: task
title: 'TUI: add a category dimension to the filter popup'
status: Draft
parent: FEAT-570
author: tech-lead
priority: medium
created_at: '2026-07-22T13:00:56Z'
updated_at: '2026-07-22T13:03:37Z'
---
<!-- sq:body -->
Implements FEAT-570 US2 (TUI filter popup). Add a category dimension to the filter/sort popup so a browsing user can narrow to roster/work/records. Depends on US1 (TASK-597 `ItemFilter.category`) and pairs with TASK-598.

## VISUAL — requires operator dev-host visual acceptance
Adds a new control to a rendered modal. Lands **InReview**; operator (Pierre) verifies on the Windows dev-host before Done. Note the launch command + what the new control looks like in the handoff.

## Scope
- `src/squads/_tui/_filter.py::FilterScreen`: add a category `Select` (options: the three fixed categories + blank/all) alongside the existing Type/Status/Assignee/Label selects. Seed it from `state.filter.category`, and set it in `_build_state()` / clear it in `_reset_widgets()`.
- Reuse the `ItemFilter.category` field added in TASK-597 — the popup only builds the filter, the service applies it (no re-matching in the popup, per the module's existing contract).
- Category options come from the fixed three-member catalog, not spec vocabulary.

## Acceptance
- The popup offers a Category selector; applying it filters the tree to that category; Clear resets it.
- TUI test that the popup round-trips a category selection into `BrowseState.filter`.
- Operator dev-host visual sign-off before Done.

## Gates
`uv run --all-extras pyright && uv run --all-extras ruff check . && uv run --all-extras ruff format --check . && uv run --all-extras pytest` (the `tui` extra MUST be present). Leave `sq check` clean.
<!-- sq:body:end -->

## Subtasks

_Add with `sq task 599 add-subtask "<title>"`; track with `sq task 599 subtask <n> update --status <Status>`._

<!-- sq:summary -->
<!-- sq:summary:end -->

<!-- sq:subtasks -->
<!-- sq:subtasks:end -->

## Discussion

<!-- sq:discussion -->
<!-- sq:discussion:end -->
