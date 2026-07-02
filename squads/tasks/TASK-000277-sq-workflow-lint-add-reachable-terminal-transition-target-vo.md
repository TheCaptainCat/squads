---
id: TASK-000277
sequence_id: 277
type: task
title: 'sq workflow lint: add reachable-terminal + transition-target vocab check'
status: Draft
parent: FEAT-000211
author: tech-lead
priority: medium
subentities:
- local_id: ST1
  title: Lint rejects undeclared transition targets and terminal-less lifecycles
  status: Todo
  story: US1
created_at: '2026-07-02T09:20:17Z'
updated_at: '2026-07-02T09:22:05Z'
---
<!-- sq:body -->
## Goal — `sq workflow lint`: reachable-terminal + transition-target vocab (AC#5, US1)

`sq workflow lint` must catch two spec defects an author can introduce in
`.overrides/workflow.toml`:
1. a transition target status not in the declared status vocabulary; and
2. a lifecycle (machine) with **no reachable terminal state** (would create items that can
   never close — breaking `sq blocked`, the default filter, and inbox suppression).

## Current state (read before coding)

- Transition targets: `WorkflowSpec._validate` → `_check_lifecycle_statuses` (in
  `_workflow/_models.py`) already errors on a transition src/dst not in the status set. This
  surfaces through `lint_workflow_spec` phase 2 (`load_workflow_spec` raises → captured as one
  finding). VERIFY it reports the offending lifecycle+status clearly; if the message is adequate,
  this half is a **test-only** confirmation, not new code.
- Reachable-terminal: there is currently **NO** check that a machine reaches a terminal state.
  `_check_reachability` only proves every state is reachable *from* initial — not that a terminal
  is reachable. This is the real new validation.

## Design

- Add a reachable-terminal check: for each lifecycle, BFS from `initial`; if none of the
  reachable states is terminal (`spec.statuses[s].terminal`), emit an error. Add it to
  `WorkflowSpec._validate` (as a new `_check_*` helper, matching the existing §5-x style) so it
  fails closed AND surfaces in `sq workflow lint` phase 2, OR add it as a dedicated lint finding
  in `lint_workflow_spec` — pick the placement that keeps `lint` reporting the config key + fix
  hint (the lint UX contract). Prefer the validator so `open_service` also fails closed.
- Ensure the terminal check is skipped/soft for lifecycles that legitimately have no terminal if
  any exist among built-ins — CHECK: agent lifecycle (Draft→Active→Archived) and sub-entity/
  finding lifecycles all have terminals, so the built-in spec must pass. Confirm the bundled
  spec lints clean (no regression) as part of acceptance.

## Acceptance

1. `sq workflow lint` on an override whose lifecycle transitions to an undeclared status reports
   that error (location = the config key, plus a fix hint), exit 1.
2. `sq workflow lint` on an override whose custom lifecycle has no reachable terminal state
   reports that error with a fix hint, exit 1.
3. The bundled spec (no override) and a valid custom override both lint clean (exit 0).
4. Tests: lint-level tests for both failure modes + the clean case.

## Files
`src/squads/_workflow/_models.py` (`_validate`, new `_check_reachable_terminal`),
`src/squads/_workflow/_loader.py` (`lint_workflow_spec` if surfacing there),
`src/squads/_cli/_workflow_cmd.py` (no logic change expected — it renders findings).
<!-- sq:body:end -->

## Subtasks

_Add with `sq task 277 add-subtask "<title>"`; track with `sq task 277 subtask <n> update --status <Status>`._

<!-- sq:summary -->
| Subtask | Status | Assignee | Title | Story |
| --- | --- | --- | --- | --- |
| ST1 | Todo |  | Lint rejects undeclared transition targets and terminal-less lifecycles | US1 |
<!-- sq:summary:end -->

<!-- sq:subtasks -->

<!-- sq:subtask:ST1 -->
### ST1 — Lint rejects undeclared transition targets and terminal-less lifecycles

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
