---
id: TASK-599
sequence_id: 599
type: task
title: 'TUI: add a category dimension to the filter popup'
status: Done
parent: FEAT-570
author: tech-lead
assignee: python-dev
priority: medium
created_at: '2026-07-22T13:00:56Z'
updated_at: '2026-07-23T07:09:23Z'
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

## Role colour
No colour work in the popup itself, but keep the category Select consistent with the role-coloured rows the tree renders (FEAT-605). No is_open/terminal reads remain — the popup only builds ItemFilter.
<!-- sq:body:end -->

## Subtasks

_Add with `sq task 599 add-subtask "<title>"`; track with `sq task 599 subtask <n> update --status <Status>`._

<!-- sq:summary -->
<!-- sq:summary:end -->

<!-- sq:subtasks -->
<!-- sq:subtasks:end -->

## Discussion

<!-- sq:discussion -->
- [2026-07-22T17:26:35Z] Elias Python:
  - Added a Category Select to _tui/_filter.py::FilterScreen alongside Type/Status/Assignee/Label — options built from the closed CATEGORIES catalog (squads._workflow), not spec vocabulary. Seeded from state.filter.category, set (with spec=self._spec so ItemFilter.matches can resolve it, matching how list_items always threads spec) in _build_state(), cleared to Select.NULL in _reset_widgets(). Popup only builds the filter; matching stays in ItemFilter/the service.
  - Test: tests/tui/test_filter_screen.py::test_applying_a_category_filter_round_trips_into_browse_state (apply narrows the tree to Records, reopen re-seeds the select, Clear+Apply resets to None).
  - How to see it: uv run sq ui, press f to open the filter popup — a new Category dropdown (Roster/Work/Records) sits under Status; selecting Records and Apply narrows the tree to records-category items.
  - Gates: pyright/ruff check/ruff format --all-extras clean; targeted uv run --all-extras pytest tests/tui -q (44 passed); sq check clean. Leaving InReview for the operator dev-host visual pass.
<!-- sq:discussion:end -->
