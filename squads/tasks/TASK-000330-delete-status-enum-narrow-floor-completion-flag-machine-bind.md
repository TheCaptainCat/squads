---
id: TASK-330
sequence_id: 330
type: task
title: Delete Status enum; narrow floor + completion-flag machine binding
status: Ready
parent: FEAT-326
author: tech-lead
subentities:
- local_id: ST1
  title: Delete Status enum; narrow _RESERVED_FLOOR to Draft/Active/Archived + STATUS_*
    constants
  status: Todo
  story: US2
- local_id: ST2
  title: Add completion flag + one-completion-per-machine validation; flag default_workflow.toml
  status: Todo
  story: US2
- local_id: ST3
  title: Sub-entity create=start state, done-toggle=completion status (no Status literals)
  status: Todo
  story: US2
created_at: '2026-07-07T14:50:24Z'
updated_at: '2026-07-08T08:30:15Z'
---
<!-- sq:body -->
## Scope

Remove the `Status` `StrEnum` so the spec's `[statuses.*]` is the sole status
vocabulary; narrow the reserved floor to the **agent lifecycle** only; and bind
sub-entity/finding lifecycle **by role in the state machine** via a new
`completion` flag layered on FEAT-211's `terminal` flag. Implements the
status-axis half of ADR-322 (US2). This is the primary bisectable unit for the
status axis.

## Areas / files

- `_models/_enums.py` — delete the `Status` `StrEnum`.
- `_workflow/_loader.py` — drop the `Status(value)` coercion (keys stay `str`).
- `_workflow/_models.py` — `StatusSpec` keyed by `str`; narrow `_RESERVED_FLOOR`
  to exactly `Draft`/`Active`/`Archived` (the agent lifecycle); add a
  `completion` (done-role) flag on `StatusSpec` layered atop the existing
  `terminal` flag; add spec-load validation that each sub-entity/finding machine
  names **exactly one** completion status (a machine with >1 terminal must
  designate one completion, distinct from cancel-style terminals).
- `_workflow/default_workflow.toml` — flag each sub-entity/finding machine's
  completion status (`Done`/`Fixed`) so the done-toggle resolves the same
  end-state it does today with no override (byte-identical behavior).
- `_services/_subentities.py` — `create` sets the machine's **start state** (no
  `Status.TODO` literal); the done-toggle resolves the machine's **completion**
  status (no `Status.DONE` literal); terminal-but-not-done states
  (`Cancelled`/`WontFix`) must not satisfy the toggle.
- `_services/_maintenance.py`, `_roster.py` — `Status.ACTIVE` (role/skill/operator
  creation) → validated `STATUS_ACTIVE` constant; add `STATUS_DRAFT`/`STATUS_ARCHIVED`
  constants as needed. These stay reserved (agent lifecycle).
- `_models/_item.py`, `_subentity.py`, `_services/_results.py`, `_retype.py`,
  `_cli/_items.py`, `_cli/_main.py`, `_discussion.py` — drop the `Status`
  re-export; flip `Status` annotations to `str`. Status badge/filter rendering is
  already spec-resolved via `status_badge()`.

## Done criteria

- `grep -rn '\bStatus\b' src/squads` returns no vocabulary-enum hits (verify
  identically-named locals by hand).
- `_RESERVED_FLOOR == {Draft, Active, Archived}`; the sub-entity statuses
  (`Todo`/`InProgress`/`Blocked`/`Done`/`Cancelled`) and finding statuses
  (`Open`/`Fixed`/`Verified`/`WontFix`) are ordinary spec vocabulary
  (renamable/reorderable, referenced nowhere by literal name).
- Sub-entity/finding `create` and done-toggle resolve via machine role /
  `completion` flag; byte-identical to today on the bundled default spec.
- Spec load rejects a sub-entity/finding machine that lacks exactly one
  completion status.
- `pyright` + `ruff check` + `ruff format --check` clean (this absorbs the
  status-axis half of the enum→`str` annotation inversion).

## Sequencing note

The floor narrowing, the `completion` flag, and the machine-role binding are
behavior-preserving and can precede the `Status` deletion; deleting the enum
last flips the remaining annotations to `str`.
<!-- sq:body:end -->

## Subtasks

_Add with `sq task 330 add-subtask "<title>"`; track with `sq task 330 subtask <n> update --status <Status>`._

<!-- sq:summary -->
| Subtask | Status | Assignee | Title | Story |
| --- | --- | --- | --- | --- |
| ST1 | Todo |  | Delete Status enum; narrow _RESERVED_FLOOR to Draft/Active/Archived + STATUS_* constants | US2 |
| ST2 | Todo |  | Add completion flag + one-completion-per-machine validation; flag default_workflow.toml | US2 |
| ST3 | Todo |  | Sub-entity create=start state, done-toggle=completion status (no Status literals) | US2 |
<!-- sq:summary:end -->

<!-- sq:subtasks -->

<!-- sq:subtask:ST1 -->
### ST1 — Delete Status enum; narrow _RESERVED_FLOOR to Draft/Active/Archived + STATUS_* constants

<!-- sq:subtask:ST1:head -->
**Status:** ⚪ Todo
**Implements:** US2 — Statuses become ordinary spec vocabulary
<!-- sq:subtask:ST1:head:end -->

<!-- sq:subtask:ST1:body -->
Delete the Status StrEnum from _enums.py; drop the Status(value) coercion in _workflow/_loader.py (keys stay str). Narrow _RESERVED_FLOOR to exactly Draft/Active/Archived and add validated STATUS_ACTIVE/STATUS_DRAFT/STATUS_ARCHIVED constants for the agent-lifecycle bindings in _maintenance.py/_roster.py. Flip remaining Status annotations to str.
<!-- sq:subtask:ST1:body:end -->

#### Discussion

<!-- sq:subtask:ST1:discussion -->
<!-- sq:subtask:ST1:discussion:end -->
<!-- sq:subtask:ST1:end -->

<!-- sq:subtask:ST2 -->
### ST2 — Add completion flag + one-completion-per-machine validation; flag default_workflow.toml

<!-- sq:subtask:ST2:head -->
**Status:** ⚪ Todo
**Implements:** US2 — Statuses become ordinary spec vocabulary
<!-- sq:subtask:ST2:head:end -->

<!-- sq:subtask:ST2:body -->
Add a completion (done-role) flag on StatusSpec layered atop FEAT-211's terminal flag, plus spec-load validation that each sub-entity/finding machine names exactly one completion status. Flag Done/Fixed as the completion status on each sub-entity/finding machine in default_workflow.toml so behavior stays byte-identical with no override.
<!-- sq:subtask:ST2:body:end -->

#### Discussion

<!-- sq:subtask:ST2:discussion -->
<!-- sq:subtask:ST2:discussion:end -->
<!-- sq:subtask:ST2:end -->

<!-- sq:subtask:ST3 -->
### ST3 — Sub-entity create=start state, done-toggle=completion status (no Status literals)

<!-- sq:subtask:ST3:head -->
**Status:** ⚪ Todo
**Implements:** US2 — Statuses become ordinary spec vocabulary
<!-- sq:subtask:ST3:head:end -->

<!-- sq:subtask:ST3:body -->
In _services/_subentities.py, create sets the machine's start state (no Status.TODO literal) and the done-toggle resolves the machine's completion status (no Status.DONE literal); terminal-but-not-done states like Cancelled/WontFix must not satisfy the toggle.
<!-- sq:subtask:ST3:body:end -->

#### Discussion

<!-- sq:subtask:ST3:discussion -->
<!-- sq:subtask:ST3:discussion:end -->
<!-- sq:subtask:ST3:end -->
<!-- sq:subtasks:end -->

## Discussion

<!-- sq:discussion -->
<!-- sq:discussion:end -->
