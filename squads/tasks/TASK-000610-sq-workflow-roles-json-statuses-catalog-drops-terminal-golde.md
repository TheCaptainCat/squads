---
id: TASK-610
sequence_id: 610
type: task
title: sq workflow roles --json + statuses catalog drops terminal + goldens
status: Done
parent: FEAT-605
author: tech-lead
priority: medium
refs:
- ADR-604
created_at: '2026-07-22T15:37:24Z'
updated_at: '2026-07-22T16:37:16Z'
---
<!-- sq:body -->
Implements FEAT-605 US2. Expose the role catalog on the machine surface and drop `terminal` from the status catalog, so clients join `status -> role -> {settled, hidden, color}` themselves and re-derive no policy. Depends on the US1 model.

## Scope (per ADR-604 §5/§6)
- New `sq workflow roles --json` catalog in `_cli/_workflow_cmd.py`: one row per role, `{role, settled, hidden, color}`.
- `sq workflow statuses --json`: drop `terminal`; keep the `role` reference and `badge`.
- Goldens: regenerate `tests/goldens/workflow_statuses.json` (drop `terminal`, populate `role`); add a new `tests/goldens/workflow_roles.json`.
- Re-express the terminal/settled unit tests against the role-derived set: `test_accepted_and_published_are_terminal`, `test_status_machine_transitions`, `test_workflow_spec_artifact`.
- `test_no_unallowlisted_module_level_mutable_state`: keep `TERMINAL` allowlisted (derived CODE constant).

## Acceptance
- `sq workflow roles --json` emits `{role, settled, hidden, color}` for each declared role; key set stable across rows.
- `sq workflow statuses --json` carries `role` + `badge`, no `terminal`.
- Both goldens present and matched; re-expressed unit tests green.

## Gates
`uv run --all-extras pyright && uv run --all-extras ruff check . && uv run --all-extras ruff format --check . && uv run --all-extras pytest`. Leave `sq check` clean.
<!-- sq:body:end -->

## Subtasks

_Add with `sq task 610 add-subtask "<title>"`; track with `sq task 610 subtask <n> update --status <Status>`._

<!-- sq:summary -->
<!-- sq:summary:end -->

<!-- sq:subtasks -->
<!-- sq:subtasks:end -->

## Discussion

<!-- sq:discussion -->
- [2026-07-22T16:21:02Z] Elias Python:
  - Landed: new 'sq workflow roles --json' ({role, settled, hidden, color}); 'sq workflow statuses --json' drops terminal (keeps role+badge). Regenerated tests/goldens/workflow_statuses.json + new tests/goldens/workflow_roles.json via UPDATE_GOLDENS=1. Re-expressed test_workflow_statuses_cli.py, test_status_semantic_role_active.py, test_category_aware_default_visibility.py (Rejected now hides by default — deliberate), test_type_spec_capability_flags.py's role-catalog test, and the reachability-lint message/assertions in test_lifecycle_reachability_lint.py. TERMINAL stays allowlisted in the mutable-state guard (unchanged, still a derived CODE constant).
<!-- sq:discussion:end -->
