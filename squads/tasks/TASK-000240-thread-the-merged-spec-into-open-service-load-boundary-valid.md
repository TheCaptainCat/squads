---
id: TASK-240
sequence_id: 240
type: task
title: Thread the merged spec into open_service + load-boundary validate()
status: Done
parent: FEAT-209
author: tech-lead
subentities:
- local_id: ST1
  title: open_service loads merged spec and hard-stops on invalid
  status: Done
  story: US3
created_at: '2026-06-30T07:49:52Z'
updated_at: '2026-06-30T08:26:42Z'
---
<!-- sq:body -->
## Goal
Make the merged project workflow spec actually take effect at runtime by feeding it through
`open_service`, and fail-close if it's invalid. Implements US3 / AC parts of #1 and #3 (the
"open_service merges without error" / "broken spec hard-stops" behaviour).

## Background — the architectural seam (read this first)
`src/squads/_workflow/__init__.py` loads a **module-level singleton** at import time:
`_DEFAULT_SPEC = load_workflow_spec()` (bundled-only), and the ENTIRE public workflow API
(`WORKFLOWS`, `TERMINAL`, `ALLOWED_PARENTS`, and ~14 free functions) is bound to that singleton.
There are ~16 import sites across `_cli/`, `_index/_store.py`, and `_services/`.

ADR-214 §1 (accepted) pins the eventual direction: "F3+ threads a per-`Service` instance; in F1
the singleton keeps the [behavior]." **However**, fully threading a `WorkflowSpec` instance through
all 16 call sites is a large, risky refactor. For FEAT-209's acceptance bar, the pragmatic seam
is to keep the singleton but make it **squad-dir-aware**: when `open_service(dir)` resolves a squad
that has a workflow override, (re)load the spec with `load_workflow_spec(squad_dir=...)` (TASK-239)
and rebind the singleton + derived constants for the process.

>> OPEN DESIGN QUESTION flagged to @manager / @architect on FEAT-209: whether F3 does the narrow
>> squad-dir-aware singleton rebind (recommended, low-risk, satisfies all 7 ACs) OR the full
>> per-Service threading the ADR names as the destination. Do NOT start coding the threading variant
>> until Catherine confirms scope. The body below assumes the rebind approach; adjust if redirected.

## What to build (rebind approach)
- In `open_service` / `Service.__init__` (`src/squads/_services/_service.py`), after resolving the
  squad dir, call `load_workflow_spec(squad_dir=...)`. Wrap it: on `SquadsError`, re-raise with the
  message appended " — run `sq workflow lint` to see details" (AC #3 / US3).
- Provide a way to install the resolved spec as the active singleton (e.g. a
  `_workflow.use_spec(spec)` that rebinds `_DEFAULT_SPEC`, `WORKFLOWS`, `TERMINAL`,
  `ALLOWED_PARENTS`, `SUBENTITY_WORKFLOWS`). Keep it deterministic and idempotent; reset to bundled
  for a squad with no override so test isolation holds (the rebind must not leak across tmp squads
  in the test suite — check `tests/conftest.py` fixture lifecycle).
- The CLI root callback already resolves the service; ensure a broken override hard-stops BEFORE any
  command body runs (no command proceeds with an invalid spec — US3 acceptance).

## Acceptance
- `open_service` on a squad with a valid `incident` override succeeds; `sq list -t incident` works
  end-to-end (AC #1 acceptance in US1 actually flows through here).
- `open_service` on a squad with a spec that fails `WorkflowSpec.validate()` raises `SquadsError`
  pointing to `sq workflow lint`; no command proceeds (AC #3 / US3).
- A squad with NO override behaves byte-identically to today (golden test green — AC #7); the rebind
  does not leak between processes/tests.

## Ordering
After TASK-239 (needs the squad-dir-aware loader). Before/alongside TASK-243 (sq check) and
TASK-242 (lint), which call the same `validate()`. Coordinate test-isolation with QA.
<!-- sq:body:end -->

## Subtasks

_Add with `sq task 240 add-subtask "<title>"`; track with `sq task 240 subtask <n> update --status <Status>`._

<!-- sq:summary -->
| Subtask | Status | Assignee | Title | Story |
| --- | --- | --- | --- | --- |
| ST1 | Done |  | open_service loads merged spec and hard-stops on invalid | US3 |
<!-- sq:summary:end -->

<!-- sq:subtasks -->

<!-- sq:subtask:ST1 -->
### ST1 — open_service loads merged spec and hard-stops on invalid

<!-- sq:subtask:ST1:head -->
**Status:** 🟢 Done
**Implements:** US3 — Broken workflow spec hard-stops sq with a clear actionable error
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
- [2026-06-30T08:11:54Z] Elias Python:
  - Implemented use_spec(spec) and reset_spec() in _workflow/__init__.py.
  - Singleton stored in _active_spec[0] (list mutation avoids pyright reportConstantRedefinition). Dict constants (WORKFLOWS, SUBENTITY_WORKFLOWS, ALLOWED_PARENTS) mutated in-place so import-time references stay live. TERMINAL stored in _terminal_ref[0] and module-level name reassigned.
  - open_service() now calls load_workflow_spec(squad_dir=sp.squad_dir) and use_spec(merged_spec). SquadsError from load wrapped with '— run sq workflow lint to see details'.
  - Added autouse _reset_workflow_spec fixture in conftest.py (reset_spec() after each test) to prevent spec leakage between tests.
  - _maintenance.py and _store.py updated to read _active_spec[0] through the module object so the rebind is visible.
- [2026-06-30T08:26:42Z] Mara Tester:
  - AC#1 (open_service half) PASS: open_service on a squad with a valid override succeeds; use_spec() installs the merged spec; the active _active_spec[0] contains the custom type. test_open_service_picks_up_override + test_ac1_merged_spec_preserves_all_bundled_types.
  - AC#3 (load-time half) PASS: open_service on a squad with an invalid spec (nonexistent lifecycle reference) raises SquadsError containing 'sq workflow lint'. test_open_service_invalid_spec_raises_with_lint_pointer.
  - AC#7 PASS: open_service on a squad with no override leaves the bundled spec in place; all types/statuses match the bundled result. test_open_service_no_override_bundled_unchanged.
  - Isolation PASS: the _reset_workflow_spec autouse fixture fires after each test and resets to bundled. Probed in-place dict mutation (WORKFLOWS identity is stable across use_spec calls — callers that imported the dict at module time see updates). test_isolation_workflows_dict_live_reference added.
  - Cross-squad isolation PASS: after use_spec(squad_A_spec) then use_spec(bundled), squad A's custom type is absent from WORKFLOWS. test_isolation_cross_squad_spec_does_not_carry_over added.
  - reset_spec PASS: after use_spec(custom), reset_spec() removes the custom type from WORKFLOWS. test_isolation_reset_clears_custom_type added.
<!-- sq:discussion:end -->
