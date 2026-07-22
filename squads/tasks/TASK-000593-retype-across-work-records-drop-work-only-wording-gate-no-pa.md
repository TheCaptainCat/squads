---
id: TASK-593
sequence_id: 593
type: task
title: Retype across work<->records; drop work-only wording + gate no_parent
status: Draft
parent: FEAT-569
author: tech-lead
priority: high
created_at: '2026-07-22T13:00:51Z'
updated_at: '2026-07-22T13:03:33Z'
---
<!-- sq:body -->
Implements FEAT-569 (records-category retype). Make `sq <type> retype` category-generic so a records type is retypeable on the same footing as a work type, per ADR-541's "reassignment allowed among non-roster categories (work <-> records); roster fixed both directions".

## Scope
- `src/squads/_services/_retype.py::_validate_work_types` already keys on `spec.non_roster_types()` (work + records), so records ARE already accepted — but its error text is stale: "only work items can be retyped" / "target must be a work type". Reword to reflect the non-roster (work/records) rule; the docstring at the top of `RetypeMixin.retype` too.
- Close the parent gap: retyping a *parented* work item INTO a records type must be refused, because the `records` bundle now carries `no_parent`. `_validate_refusals` currently checks `spec.parent_allowed(new_type, ...)`, which returns True for a records type's empty `parents` list (lenient) — it does NOT see `no_parent`. Route the retype's post-change conformance through the same `ValidatorEngine` gate the create/update sites use (one engine, no re-encoded rule), so a records target with an existing parent fails closed with an actionable message ("remove the parent first").
- Confirm status carry/reset (`_carry_or_reset_status`) behaves for a work->records reclassification (different lifecycles reset to the records type's initial status) and the retype reflog/system comment are unchanged.

## Acceptance
- Retype work->records and records->work both succeed for unparented items; the file moves to the new type's declared folder; incoming edges rewrite.
- Retyping a parented item to a records type refuses cleanly (no traceback).
- No stale "work type only" wording remains in retype messages.
- Service + CLI smoke tests covering work<->records and the parented-refusal case.

## Gates
`uv run --all-extras pyright && uv run --all-extras ruff check . && uv run --all-extras ruff format --check . && uv run --all-extras pytest` (the `tui` extra must be present). Leave `sq check` clean for touched work.
<!-- sq:body:end -->

## Subtasks

_Add with `sq task 593 add-subtask "<title>"`; track with `sq task 593 subtask <n> update --status <Status>`._

<!-- sq:summary -->
<!-- sq:summary:end -->

<!-- sq:subtasks -->
<!-- sq:subtasks:end -->

## Discussion

<!-- sq:discussion -->
<!-- sq:discussion:end -->
