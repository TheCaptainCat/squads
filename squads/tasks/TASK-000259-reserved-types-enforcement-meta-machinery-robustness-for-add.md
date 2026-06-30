---
id: TASK-000259
sequence_id: 259
type: task
title: RESERVED_TYPES enforcement + meta-machinery robustness for additive types
status: Done
parent: FEAT-000210
author: tech-lead
created_at: '2026-06-30T12:01:06Z'
updated_at: '2026-06-30T12:34:54Z'
---
<!-- sq:body -->
**Slice 3 — RESERVED_TYPES enforcement + meta-machinery robustness.**
Maps to: AC#1/AC#2 robustness; the additive-only invariant (op-pierre, from
FEAT-208).

### Scope
Custom types are ADDITIVE over the reserved core: a project may ADD types but
may NEVER DROP the reserved meta-types (role/skill/operator) that the role
backend, skill generation, and operator machinery depend on.

The RESERVED_TYPES invariant is ALREADY enforced at spec-load:
`WorkflowSpec._validate` §5-6a rejects a spec missing any reserved `ItemType`
member, and §5-6b enforces the reserved Status floor. So this task is NOT about
re-adding that check — it is about confirming it holds end-to-end once the CLI
builds from the spec, and hardening the meta-type machinery against the newly
reachable custom types:
- Confirm `work_types()` (spec: `not is_meta`) correctly EXCLUDES meta-types and
  INCLUDES custom work types, so the app-build loop in task 257 registers
  retype/remove only for work types (mirrors today's `if item_type in
  _work_types()` gate in `build_item_app`).
- Confirm a custom type cannot collide with a reserved prefix/folder (F3
  uniqueness check covers this — add a characterization test asserting the
  fail-closed error).
- Confirm `sq workflow lint` reports a dropped reserved type / status with a
  clear author-facing message (it runs the same validation; verify the message
  is actionable).
- Audit the interactions/PLAYBOOK + roster + backend paths that key on
  `ItemType` (e.g. CREATE_LANES, managed_item_types, role-skill mapping): a
  custom type has no PLAYBOOK entry — confirm graceful degradation (no KeyError),
  which is the seam task 260 fills with the thin auto-skill.

### Acceptance
- A spec dropping role/skill/operator (or a floor status) fails closed with a
  clear error at load AND surfaces in `sq workflow lint`.
- A custom work type is in `work_types()` and gets retype/remove; meta-types do
  not (unchanged).
- No reserved prefix/folder can be shadowed by a custom type.
- Reserved-type behaviour byte-identical (task 256 golden green).

### Files
- src/squads/_workflow/_models.py (confirm/extend §5-6 + lint message),
  src/squads/_cli/_workflow_cmd.py (lint surfacing), tests/test_workflow_spec.py
  (or sibling) for the fail-closed cases.

### Dependencies
- Depends on F3 (FEAT-000209) and FEAT-208 (the invariant). Coordinates with
  task 257 (work_types gate) and task 260 (graceful PLAYBOOK degradation).
<!-- sq:body:end -->

## Subtasks

_Add with `sq task 259 add-subtask "<title>"`; track with `sq task 259 subtask <n> update --status <Status>`._

<!-- sq:summary -->
<!-- sq:summary:end -->

<!-- sq:subtasks -->
<!-- sq:subtasks:end -->

## Discussion

<!-- sq:discussion -->
- [2026-06-30T12:34:54Z] Elias Python:
  - Done. Confirmed RESERVED_TYPES invariant is already fail-closed in WorkflowSpec._validate (§5-6a/b): dropping any ItemType member or any floor-status raises SquadsError at spec-load. Tested parametrically across all ItemType members and 12 floor statuses.
  - work_types() correctly excludes all meta-types (role/skill/operator) and includes custom non-meta types; also excludes custom types declared with is_meta=True. Reserved prefix/folder uniqueness (§5-5): shadowing 'TASK' or 'tasks/' by a custom type raises SquadsError.
  - Graceful degradation confirmed: skills_for_role() and _interactions.py yield empty sequences (no KeyError) for custom work types absent from PLAYBOOK. sq workflow lint surfaces missing-reserved-type errors.
  - 34 tests in tests/test_reserved_types_invariants.py — all pass. No new enforcement code needed — tests confirm the invariants already present.
<!-- sq:discussion:end -->
