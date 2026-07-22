---
id: TASK-609
sequence_id: 609
type: task
title: Service open/closed reads switch to not role.settled
status: Done
parent: FEAT-605
author: tech-lead
priority: medium
refs:
- ADR-604
created_at: '2026-07-22T15:37:22Z'
updated_at: '2026-07-22T16:37:14Z'
---
<!-- sq:body -->
Implements FEAT-605 US1. Switch the service-level open/closed reads off the old terminal/is_open inputs onto the role object (`not role.settled`), via the `is_open`/`is_live` helper.

## Scope (per ADR-604 §6, "Services")
- `_services/_roster.py`: the open/closed bucket split reads `not role.settled`.
- `_services/_refs.py`: blocker traversal + `RefContext.is_open` (5 sites) read `not role.settled`.
- `_services/_collab.py`: the open-item collaboration guard reads `not role.settled`.
- `_services/_base.py` default-list visibility: call site is unchanged — `hidden_by_default` re-derives from role internally.

## Acceptance
- Roster open/closed counts, blocker traversal, and the open-item guard behave identically to today for the bundled spec (role-derived open-set == old is_open-set for work/roster).
- Existing service tests pass; add/adjust a test asserting the open-set is role-derived.

## Gates
`uv run --all-extras pyright && uv run --all-extras ruff check . && uv run --all-extras ruff format --check . && uv run --all-extras pytest`. Leave `sq check` clean.
<!-- sq:body:end -->

## Subtasks

_Add with `sq task 609 add-subtask "<title>"`; track with `sq task 609 subtask <n> update --status <Status>`._

<!-- sq:summary -->
<!-- sq:summary:end -->

<!-- sq:subtasks -->
<!-- sq:subtasks:end -->

## Discussion

<!-- sq:discussion -->
- [2026-07-22T16:20:59Z] Elias Python:
  - No source changes needed: _services/_roster.py, _refs.py (incl. RefContext.is_open), _collab.py already routed exclusively through spec.is_open(status), which now derives from role.settled internally. _base.py's default-list visibility call site unchanged (hidden_by_default re-derives). Verified via targeted service tests (blocked/refs/roster/workload/collab + terminal-status reopen/unblock) — all green, no behavior change for the bundled spec.
<!-- sq:discussion:end -->
