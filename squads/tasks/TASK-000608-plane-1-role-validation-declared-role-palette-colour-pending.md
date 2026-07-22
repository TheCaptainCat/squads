---
id: TASK-608
sequence_id: 608
type: task
title: 'Plane-1 role validation: declared role, palette colour, pending fallback'
status: Done
parent: FEAT-605
author: tech-lead
priority: high
refs:
- ADR-604
created_at: '2026-07-22T15:37:21Z'
updated_at: '2026-07-22T16:37:13Z'
---
<!-- sq:body -->
Implements FEAT-605 US1. Add the Plane-1 (load-time) spec validation for the role catalog so a malformed spec fails closed instead of surfacing later as a render or derivation error.

## Scope (per ADR-604 §6, `_validate`)
- Every `status.role` must name a role declared in `[roles.<name>]` — an unknown reference is a load-time `SquadsError`.
- Every `role.color` must be one of the closed semantic-intent palette: `positive` / `danger` / `warning` / `muted` / `neutral` / `info`. An unknown intent fails closed at load.
- A status with no `role` resolves to the bundled `pending` role (neutral, live, shown) — fail-safe-visible; validate that `pending` is present so the fallback always resolves.

## Acceptance
- A spec whose status references an undeclared role fails to load with a clear `SquadsError`.
- A spec whose role declares an off-palette colour fails to load.
- A status omitting `role` resolves to `pending` (shown/live) with no error.
- Unit tests for each of the three cases.

## Gates
`uv run --all-extras pyright && uv run --all-extras ruff check . && uv run --all-extras ruff format --check . && uv run --all-extras pytest`. Leave `sq check` clean.
<!-- sq:body:end -->

## Subtasks

_Add with `sq task 608 add-subtask "<title>"`; track with `sq task 608 subtask <n> update --status <Status>`._

<!-- sq:summary -->
<!-- sq:summary:end -->

<!-- sq:subtasks -->
<!-- sq:subtasks:end -->

## Discussion

<!-- sq:discussion -->
- [2026-07-22T16:20:55Z] Elias Python:
  - Landed: Plane-1 checks in WorkflowSpec._validate — every explicit status.role must name a declared role, every role.color must be in the closed {positive,danger,warning,muted,neutral,info} palette. Old 'terminal status not in status set' belt-check removed (terminal is gone). Covered by test_workflow_spec_models_fail_closed_on_unknown_keys.py plus the many hand-built WorkflowSpec fixtures across tests/unit + tests/service now carrying a roles catalog.
<!-- sq:discussion:end -->
