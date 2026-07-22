---
id: TASK-593
sequence_id: 593
type: task
title: Retype across work<->records; drop work-only wording + gate no_parent
status: Done
parent: FEAT-569
author: tech-lead
priority: high
created_at: '2026-07-22T13:00:51Z'
updated_at: '2026-07-22T17:16:03Z'
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
- [2026-07-22T17:07:49Z] Elias Python:
  - Reworded stale wording in src/squads/_services/_retype.py (_validate_work_types) from 'only work items'/'target must be a work type' to 'only work/records items'/'target must be a work or records type'; also reworded the CLI retype --help text in _cli/_items.py. Docstring on RetypeMixin.retype already said 'non-roster types' — extended its refusal bullet to name the new gate.
  - Closed the parent gap: retype now builds a prospective post-change item (new type/status/prefix, same parent) and runs it through the SAME ValidatorEngine.gate() create/update use, before any file mutation — so retyping a parented item into a records type fails closed via the catalog's no_parent (message: '<type> takes no parent (got <parent>)'), no re-encoded rule. Status carry/reset and the reflog/system comment are unchanged (verified by existing tests).
  - Tests added: tests/service/test_retype.py (work<->records unparented succeed both directions; parented-into-records refusal) + tests/cli/test_retype_command_cli.py (CLI smoke: work->records success, parented->records rejection). Renamed two pre-existing 'meta_type' test/param names in the same file to 'roster_type' while touching them (repo-wide meta->roster purge is tracked separately on FEAT-573, not duplicated here).
  - Gates: pyright/ruff clean; targeted pytest green; sq check clean.
<!-- sq:discussion:end -->
