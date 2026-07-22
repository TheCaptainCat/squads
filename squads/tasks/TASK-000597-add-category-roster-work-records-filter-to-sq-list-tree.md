---
id: TASK-597
sequence_id: 597
type: task
title: Add --category roster|work|records filter to sq list/tree
status: Done
parent: FEAT-570
author: tech-lead
priority: medium
created_at: '2026-07-22T13:00:54Z'
updated_at: '2026-07-22T17:18:00Z'
---
<!-- sq:body -->
Implements FEAT-570 US1. Add a `--category roster|work|records` filter dimension alongside today's type/status/priority filters.

## Scope
- Add a `category` field to `ItemFilter` (`_services/_filter` / wherever `ItemFilter` lives) that matches an item when its type's `spec.items[type].category` equals the requested category. Validate the value against the three-category catalog with a clean `SquadsError` on an unknown value.
- `src/squads/_cli/_main.py`: add `--category` to `sq list` and (for parity, since they share `ItemFilter`) `sq tree`. Wire it into the filter built for `list_items`/`tree_view`.
- The category axis is a fixed three-member catalog (roster/work/records), not spec vocabulary — enumerate it from the category catalog, do not hardcode a literal tuple at the CLI.

## Acceptance
- `sq list --category records` shows only records-category items; `--category work`/`roster` likewise; composes with other filters (AND).
- Unknown `--category` value errors cleanly (exit 1).
- CLI smoke tests + a filter-level test.

## Gates
`uv run --all-extras pyright && uv run --all-extras ruff check . && uv run --all-extras ruff format --check . && uv run --all-extras pytest` (the `tui` extra must be present). Leave `sq check` clean.
<!-- sq:body:end -->

## Subtasks

_Add with `sq task 597 add-subtask "<title>"`; track with `sq task 597 subtask <n> update --status <Status>`._

<!-- sq:summary -->
<!-- sq:summary:end -->

<!-- sq:subtasks -->
<!-- sq:subtasks:end -->

## Discussion

<!-- sq:discussion -->
- [2026-07-22T13:28:33Z] Elias Python:
  - Added --category roster|work|records to sq list/sq tree, threaded through ItemFilter.category (spec-resolved, graceful no-match without a spec) and Service.list_items; category catalog (_workflow.CATEGORIES) derived from ItemSpec's own Literal, not hand-duplicated; parse_category validates with a clean SquadsError. Composes (AND) with existing filters. Gates green; sq check clean.
- [2026-07-22T15:38:04Z] Olivia Lead:
  - Carried by FEAT-605: this work (--category roster|work|records filter + CATEGORIES catalog) is ADR-604-compatible and orthogonal to the role-object change. The FEAT-605 implementer keeps this code as-is; it lands with FEAT-605 from the current tree. Status left InReview for the manager to reconcile once FEAT-605 lands.
- [2026-07-22T17:17:58Z] Catherine Manager:
  - Landed with FEAT-605 (sq list/tree --category filter survived the trunk absorption; exercised by FEAT-569's end-to-end test). Closing.
<!-- sq:discussion:end -->
