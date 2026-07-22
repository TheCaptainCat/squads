---
id: TASK-607
sequence_id: 607
type: task
title: Drop StatusSpec.terminal; derive is_open/terminal/hidden from role
status: Done
parent: FEAT-605
author: tech-lead
priority: high
refs:
- ADR-604
created_at: '2026-07-22T15:37:19Z'
updated_at: '2026-07-22T16:37:12Z'
---
<!-- sq:body -->
Implements FEAT-605 US1. Drop the explicit `terminal` field and re-express terminal / open / default-visibility as reads of the referenced role object (built in the first US1 task). No expressiveness loss — `settled` + `hidden` on the role carry what a single `terminal` flag plus a category branch used to.

## Scope (per ADR-604 §6 "Core")
- Remove `StatusSpec.terminal`.
- `WorkflowSpec.is_open(s)` -> `not roles[statuses[s].role].settled`.
- `WorkflowSpec.terminal_set()` -> `{s | roles[statuses[s].role].settled}`.
- `WorkflowSpec.hidden_by_default(item_type, s)` -> `roles[statuses[s].role].hidden` (the category branch is deleted — see disposition).
- `_workflow/__init__.py` `TERMINAL` frozenset export -> recomputed from role-derived `terminal_set()`; keep it allowlisted in the module-mutable-state guard as a derived CODE constant.
- `_check_reachable_terminal` lint -> "every lifecycle must reach a status whose role is settled"; drop the old "terminal status not in status set" belt-check.

## Disposition of the uncommitted tree
REPLACE the superseded prior-session code:
- `RETIRED_STATUS_ROLES` frozenset (`_workflow/_models.py`) -> deleted; retired-ness is now `role.settled`/`role.hidden` off the catalog, no hardcoded set.
- The `hidden_by_default` `if category == "records": return status_role(s) in RETIRED_STATUS_ROLES` branch -> deleted; `hidden_by_default = role.hidden` for all categories.
KEEP (orthogonal survivors, do not touch here): `CATEGORIES` (the `get_args` tuple) and the category axis — those ride FEAT-570 US1 and are carried forward, not replaced.

## Acceptance
- No `terminal` field on `StatusSpec`; `is_open`/`terminal_set()`/`TERMINAL` all derive from role.
- Bundled default visibility preserved except the one deliberate change: `Accepted`/`Published` shown, `Done`/`Verified` hidden, `Superseded`/`Deprecated` hidden, and `Rejected` now hidden (was shown). This resolves REV-603 F2 (Rejected -> retired).
- Reachable-settled lint fires on a lifecycle with no settled-role status.

## Gates
`uv run --all-extras pyright && uv run --all-extras ruff check . && uv run --all-extras ruff format --check . && uv run --all-extras pytest`. Leave `sq check` clean.
<!-- sq:body:end -->

## Subtasks

_Add with `sq task 607 add-subtask "<title>"`; track with `sq task 607 subtask <n> update --status <Status>`._

<!-- sq:summary -->
<!-- sq:summary:end -->

<!-- sq:subtasks -->
<!-- sq:subtasks:end -->

## Discussion

<!-- sq:discussion -->
- [2026-07-22T16:20:51Z] Elias Python:
  - Landed: StatusSpec.terminal removed; is_open/terminal_set/hidden_by_default all derive from WorkflowSpec.role_for(status) (fallback to the bundled 'pending' role when a status omits role). RETIRED_STATUS_ROLES + the records category-branch deleted; hidden_by_default is now a pure role.hidden read (item_type param kept for signature stability, unused). Reachable-terminal lint renamed to reachable-settled, message text updated. TERMINAL frozenset export unchanged (still derives from terminal_set()).
<!-- sq:discussion:end -->
