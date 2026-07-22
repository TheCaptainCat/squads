---
id: TASK-583
sequence_id: 583
type: task
title: ItemSpec.validators assignment surface + Plane-1 load validation
status: Done
parent: FEAT-568
author: tech-lead
refs:
- ADR-541
- TASK-581:depends-on
description: Extend-only per-type validators list + load-time catalog-membership /
  well-formed parent_in checks
created_at: '2026-07-22T10:33:01Z'
updated_at: '2026-07-22T11:46:32Z'
---
<!-- sq:body -->
## Scope

Build the declarative per-type validator **assignment** surface — the
extend-only `validators` list on a type — and its Plane-1 (load-time) validity
checks. This is additive over the bundled spec (every bundled type keeps an
empty `validators`, except epic once the enforcement task lands).

- Add `ItemSpec.validators: list[str] = []` (`_workflow/_models.py`): extend-only
  additions over the category floor; no per-validator deselect.
- Wire the engine to include them: `effective_validator_names(category,
  extra=item_spec.validators)` (the `extra` seam already exists).
- Plane-1 checks in `WorkflowSpec._validate` (the fail-closed load pass,
  `sq workflow lint` diagnostic):
  - **catalog membership** — every name in a type's `validators` is a member of
    the closed catalog; an unknown name fails closed.
  - **well-formed parent validator** — an empty `parent_in` allowlist is
    rejected, with the diagnostic pointing the author at `no_parent` (per
    ADR-541). Note: if `parent_in` reads the structured `parents` field with no
    param (see the @architect note), this rule reduces to "a type declaring
    `parent_in` must have non-empty `parents`" — confirm framing with the
    architect's answer.

## Layering note (flag @architect if needed)

The membership check runs in `_workflow/_models.py`, but `CATALOG` lives in
`_services/_validators.py`, and `_workflow` sits **below** `_services` in the
import graph (`_cli → _services → … → _workflow/_models`) — `_workflow` importing
`_services` would invert the layer / risk a cycle. The set of valid validator
**names** must therefore be reachable from `_workflow` without importing
`_services`. See the @architect point on the feature; do not introduce a
back-edge — relocate the name registry (or expose a plain name frozenset in a
lower layer) per the architect's guidance.

## Acceptance

- A `validators` entry naming a non-catalog validator fails at spec load
  (`SquadsError` → exit 1, `sq workflow lint` diagnostic); service + CLI test.
- Empty `parent_in` (or its structured-field equivalent) rejected at load with
  the `no_parent` hint.
- Bundled spec unchanged: every bundled type's effective set is identical to the
  routing task's output (empty `validators` everywhere).
- Import graph stays acyclic (the verified acyclicity check passes).
- Full suite green; pyright + ruff clean.
<!-- sq:body:end -->

## Subtasks

_Add with `sq task 583 add-subtask "<title>"`; track with `sq task 583 subtask <n> update --status <Status>`._

<!-- sq:summary -->
<!-- sq:summary:end -->

<!-- sq:subtasks -->
<!-- sq:subtasks:end -->

## Discussion

<!-- sq:discussion -->
- [2026-07-22T11:20:34Z] Elias Python:
  - Added ItemSpec.validators: list[str] = [] (extend-only, bare bundled spec everywhere); wired effective_validator_names(category, extra=item_spec.validators) into the engine (colon-param stripped before the CATALOG lookup).
  - Plane-1: _check_validators_assignment in WorkflowSpec._validate — param-aware catalog-membership only (bare name in VALIDATOR_NAMES; a ':param' suffix legal only for PARAMETERIZED_VALIDATOR_NAMES = {subentity_title_max}). Per Robert's pin, no empty-parent_in check added (moot under the no-param reading).
  - Tests: unit (bundled-spec-empty, unknown-name/param-on-non-parameterized/param-on-subentity_title_max load failures, engine actually runs a type's own addition) + CLI (sq workflow lint exit 1 on a custom type with a bad validators entry).
  - Gates: pyright/ruff/format clean; full fast suite green; sq check on this repo still clean. TASK-584 untouched (Draft).
<!-- sq:discussion:end -->
