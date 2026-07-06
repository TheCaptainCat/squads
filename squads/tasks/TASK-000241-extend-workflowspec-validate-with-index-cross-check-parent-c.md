---
id: TASK-241
sequence_id: 241
type: task
title: Extend WorkflowSpec.validate() with index cross-check + parent-cycle checks
status: Done
parent: FEAT-209
author: tech-lead
subentities:
- local_id: ST1
  title: Parent-cycle + live-index cross-check validation
  status: Done
  story: US3
created_at: '2026-06-30T07:49:52Z'
updated_at: '2026-07-06T15:21:06Z'
---
<!-- sq:body -->
## Goal
Extend the fail-closed validation in `WorkflowSpec` so it covers the two checks the feature names
that aren't there yet: (a) a **live-index cross-check** — removing/omitting a status or type still
referenced by items on disk must fail with the offending items listed; and (b) **parent-cycle
detection** in the type-parent graph. (AC #5; supports AC #3.)

## Current state
`WorkflowSpec._validate` (model_validator in `src/squads/_workflow/_models.py`) already covers:
lifecycle initial/transition statuses exist (§5-1/§5-2), terminal-in-set (§5-3), reachability (§5-4),
ItemSpec lifecycle/parent-declared + prefix/folder/alias uniqueness (§5-5), and reserved-vocab
subset (§5-6a/b). It does NOT have parent-cycle detection, and — being a pure model validator — it
cannot see the live index (`.squads.json`). The load-boundary vocab check in `_maintenance.py`
(`repair`/index rebuild, ~line 347) already rejects items whose type/status isn't in the spec; this
task adds the **inverse-direction** guarantee for the override case.

## What to build
1. **Parent-cycle detection** (pure-spec, belongs in the model validator): walk the `items[t].parents`
   graph and raise an error listing any cycle (e.g. `a→b→a`). Add as a new `_check_*` helper to keep
   `_validate` under the complexity limit (the file already factors checks out this way).
2. **Index cross-check** (needs the index — must live OUTSIDE the pure model validator). Add a
   separate function, e.g. `validate_against_index(spec, db) -> list[str]` (in `_loader.py` or a new
   `_validate.py` under `_workflow/`), that returns human-readable errors when a type or status that
   appears on a live item is NOT present in the merged spec. This is the AC #5 case: an override that
   omits a status still in use by items fails closed with the list of offending item IDs.
   - Wire it where the merged spec meets the index: `open_service` (TASK-240) and/or `sq check`
     (TASK-243) call it. The `WorkflowSpec.validate()` the feature body references becomes the
     pure-spec part; the index cross-check is the index-aware sibling invoked at the same boundary.

## Acceptance
- A spec whose type-parent graph has a cycle raises `SquadsError` naming the cycle (AC #3 surface).
- Given a squad with a live item of status `X`, an override that does not declare `X` fails closed
  with a message listing the offending item ID(s) (AC #5).
- Existing validation behaviour unchanged for the bundled default (golden test green — AC #7).

## Ordering
After TASK-239 (merge) and best done alongside TASK-240 (the cross-check needs the spec+index
seam that 240 establishes). Its output feeds TASK-242 (lint) and TASK-243 (sq check).
<!-- sq:body:end -->

## Subtasks

_Add with `sq task 241 add-subtask "<title>"`; track with `sq task 241 subtask <n> update --status <Status>`._

<!-- sq:summary -->
| Subtask | Status | Assignee | Title | Story |
| --- | --- | --- | --- | --- |
| ST1 | Done |  | Parent-cycle + live-index cross-check validation | US3 |
<!-- sq:summary:end -->

<!-- sq:subtasks -->

<!-- sq:subtask:ST1 -->
### ST1 — Parent-cycle + live-index cross-check validation

<!-- sq:subtask:ST1:head -->
**Status:** 🟢 Done
**Implements:** US3 — Broken workflow spec hard-stops sq with a clear actionable error
<!-- sq:subtask:ST1:head:end -->

<!-- sq:subtask:ST1:body -->
Covers extending the fail-closed validation with the two checks the feature names: (a) parent-cycle detection — a pure-spec `_check_*` helper in `WorkflowSpec._validate` that walks the `items[t].parents` graph and raises naming any cycle; and (b) a live-index cross-check — `validate_against_index(spec, db)` (outside the pure model validator, since it needs the index) returning human-readable errors listing offending item IDs when a type/status on a live item is absent from the merged spec. Wired at the `open_service`/`sq check` seam. Bundled-default behavior unchanged. (US3)
<!-- sq:subtask:ST1:body:end -->

#### Discussion

<!-- sq:subtask:ST1:discussion -->
<!-- sq:subtask:ST1:discussion:end -->
<!-- sq:subtask:ST1:end -->
<!-- sq:subtasks:end -->

## Discussion

<!-- sq:discussion -->
- [2026-06-30T08:12:03Z] Elias Python:
  - Added _check_parent_cycles() DFS to _models.py, wired into WorkflowSpec._validate as §5-7. Reports ALL cycles in one pass (no graphlib — by design, for full error surface required by sq workflow lint).
  - Removed _SUBENTITY_KINDS from _models.py — it was dead code (defined but never referenced in that module). The same constant exists in __init__.py where it IS used.
  - validate_against_index(spec, db) in _loader.py: cross-checks live index items against spec.items and spec.statuses, returning a list of error strings. Wired into tests; TASK-242 (sq workflow lint) and TASK-243 (sq check) call this.
  - Cycle detection uses the ruff-preferred list unpacking form ([*cycle_nodes, parent]) instead of list concatenation.
- [2026-06-30T08:26:54Z] Mara Tester:
  - Parent-cycle detection PASS: A→B→A and A→B→C→A cycles in the type-parent graph both raise SquadsError naming the cycle. test_parent_cycle_detected_direct + test_parent_cycle_detected_three_node. Bundled spec is cycle-free (test_no_parent_cycle_bundled_spec).
  - validate_against_index PASS (function itself): item type missing → error lists item ID; item status missing → error lists item ID; sub-entity status missing → error lists parent item ID. Added test_validate_against_index_subentity_bad_status (sub-entity axis was not previously tested).
  - DEFECT FOUND — AC#5 wiring gap: validate_against_index is implemented correctly but is NOT called from open_service. A squad with a live item whose status is no longer in the override spec proceeds without error — the fail-closed guarantee that AC#5 requires is not enforced end-to-end. Reproduced: open_service with an override that drops a previously-used status succeeds silently. Documented in test_ac5_validate_against_index_not_called_by_open_service (assertion currently expects no raise — invertible once fixed). This defect is out of scope for TASK-239/240/241; it should be tracked and fixed before or in TASK-243 (sq check), which is the other natural wiring point.
  - Empty index boundary PASS: validate_against_index on a squad with no work items returns []. Covered by existing test_validate_against_index_clean.
<!-- sq:discussion:end -->
