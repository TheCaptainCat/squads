---
id: TASK-606
sequence_id: 606
type: task
title: Role catalog spec construct + regenerated bundled workflow
status: Done
parent: FEAT-605
author: tech-lead
priority: high
refs:
- ADR-604
created_at: '2026-07-22T15:37:18Z'
updated_at: '2026-07-22T18:42:47Z'
---
<!-- sq:body -->
Implements FEAT-605 US1. Introduce the role catalog as a first-class spec construct and regenerate the bundled workflow — the model the rest of FEAT-605 and FEAT-570's rework depend on.

## Scope
- New `RoleSpec` model in `_workflow/_models.py`: `settled: bool`, `hidden: bool = False`, `color: str` (validated against the closed intent palette in US1c).
- `WorkflowSpec.roles: dict[str, RoleSpec]`, loaded from a `[roles.<name>]` table block, sibling to `[statuses.…]`.
- `StatusSpec.role` stays as the reference (name of a role); no longer a free-form marker used only for a couple of special cases.
- Regenerate the bundled `_workflow/default_workflow.toml`: add the eight `[roles.<name>]` blocks and give every status a `role`. Catalog per ADR-604 §2:
  - `pending` (neutral, live, shown): Draft, Ready, Proposed, Requested, Todo
  - `active` (positive, live, shown): InProgress, InReview, ChangesRequested, Fixed, Active
  - `attention` (danger, live, shown): Open
  - `blocked` (danger, live, shown): Blocked
  - `in_force` (info, settled, shown): Accepted, Published
  - `done` (positive, settled, hidden): Done, Verified, Approved
  - `retired` (muted, settled, hidden): Cancelled, Rejected, Deprecated, WontFix, Archived
  - `superseded` (muted, settled, hidden): Superseded
- Remove every per-status `terminal = …` line from the bundled spec (the field itself is dropped in US1b).

## Acceptance
- `[roles.<name>]` parses into `WorkflowSpec.roles`; every bundled status resolves to a declared role.
- Bundled spec carries no `terminal` line.
- Spec loads clean; existing load tests pass (derivation wired in US1b).

## Gates
`uv run --all-extras pyright && uv run --all-extras ruff check . && uv run --all-extras ruff format --check . && uv run --all-extras pytest`. Leave `sq check` clean.
<!-- sq:body:end -->

## Subtasks

_Add with `sq task 606 add-subtask "<title>"`; track with `sq task 606 subtask <n> update --status <Status>`._

<!-- sq:summary -->
<!-- sq:summary:end -->

<!-- sq:subtasks -->
<!-- sq:subtasks:end -->

## Discussion

<!-- sq:discussion -->
- [2026-07-22T16:20:49Z] Elias Python:
  - Landed: RoleSpec model (settled/hidden/color) + WorkflowSpec.roles, loaded from [roles.<name>] (loader + override-merge, additive like collections). Regenerated default_workflow.toml: 8 role blocks, role= on all 23 statuses, every terminal= line removed. Targeted gates green (pyright/ruff/ruff format clean; unit+cli+service+integration subset green).
<!-- sq:discussion:end -->
