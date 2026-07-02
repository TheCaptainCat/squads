---
id: TASK-000278
sequence_id: 278
type: task
title: 'Custom-status regression: parse_status, sq list --status, blocked, default
  filter'
status: Draft
parent: FEAT-000211
author: tech-lead
priority: medium
subentities:
- local_id: ST1
  title: sq list --status + default filter + blocked + inbox honor custom statuses
  status: Todo
  story: US1
created_at: '2026-07-02T09:20:18Z'
updated_at: '2026-07-02T09:22:05Z'
---
<!-- sq:body -->
## Goal — custom statuses through query/filter surfaces (AC#1, AC#2, US1)

Prove (and fix if needed) that `parse_status`, `sq list --status`, `sq list` default filter,
`sq blocked`, and `sq inbox` all classify items by the loaded spec's custom statuses.

## Current state (read before coding — much of this may already work)

- `parse_status` (`_cli/_common.py`) already validates against `get_active_spec().statuses`
  (exact + loose match) and errors "unknown status … (one of: …)". Custom statuses SHOULD already
  parse. Confirm the error lists custom values too.
- Open/terminal classification is already spec-derived: `self.spec.is_open(status)` is used in
  `_services/_base.py` (list filter), `_roster.py`, `_refs.py` (blocked graph), `_collab.py`
  (inbox suppression), and `_cli/_main.py` (list default filter, tree). So AC#1/AC#2 are largely
  a **characterization + regression** job, not new wiring — but VERIFY each path end-to-end with
  a real custom-status override rather than assuming.

## Scope

- Add an end-to-end test override (`.overrides/workflow.toml`) with a custom lifecycle whose
  statuses include a custom **non-terminal** status (e.g. `Triage`, `Mitigating`) and a custom
  **terminal** status (e.g. `Resolved`, terminal=true).
- Assert: `sq list --status Triage` returns the item; `sq list` (no `--all`) hides an item in the
  terminal custom status and shows one in a non-terminal custom status; `sq blocked` treats a
  blocker in a non-terminal custom status as still-blocking and one in a terminal custom status as
  cleared; `sq inbox` suppresses mentions in items with a terminal custom status.
- Unknown `--status Bogus` → actionable "known values" error (exit 1).
- Fix any surface still hardcoding `TERMINAL`/`Status(...)`/enum membership that a custom status
  would break (grep for `Status(` and `TERMINAL` in services/CLI first).

## Acceptance

Matches FEAT-211 AC#1 and AC#2 exactly. All new tests pin roster/clock/flags and run green
under the TASK-000275 guard.

## Files
`src/squads/_cli/_common.py` (parse_status — likely no change), `src/squads/_cli/_main.py`
(list/blocked/inbox), `src/squads/_services/_base.py`, `_refs.py`, `_collab.py`, `_roster.py`
(verify only), tests under `tests/`.
<!-- sq:body:end -->

## Subtasks

_Add with `sq task 278 add-subtask "<title>"`; track with `sq task 278 subtask <n> update --status <Status>`._

<!-- sq:summary -->
| Subtask | Status | Assignee | Title | Story |
| --- | --- | --- | --- | --- |
| ST1 | Todo |  | sq list --status + default filter + blocked + inbox honor custom statuses | US1 |
<!-- sq:summary:end -->

<!-- sq:subtasks -->

<!-- sq:subtask:ST1 -->
### ST1 — sq list --status + default filter + blocked + inbox honor custom statuses

<!-- sq:subtask:ST1:head -->
**Status:** ⚪ Todo
**Implements:** US1 — As a team member, I want sq list --status and sq blocked to work correctly with my custom statuses
<!-- sq:subtask:ST1:head:end -->

<!-- sq:subtask:ST1:body -->
_Describe this subtask here — free-form paragraphs or bullet lists._
<!-- sq:subtask:ST1:body:end -->

#### Discussion

<!-- sq:subtask:ST1:discussion -->
<!-- sq:subtask:ST1:discussion:end -->
<!-- sq:subtask:ST1:end -->
<!-- sq:subtasks:end -->

## Discussion

<!-- sq:discussion -->
<!-- sq:discussion:end -->
