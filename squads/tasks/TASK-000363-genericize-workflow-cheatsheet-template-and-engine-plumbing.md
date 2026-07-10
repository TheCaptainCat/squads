---
id: TASK-363
sequence_id: 363
type: task
title: Genericize workflow cheatsheet template and engine plumbing
status: Draft
parent: FEAT-334
author: tech-lead
created_at: '2026-07-10T02:00:02Z'
updated_at: '2026-07-10T02:02:35Z'
---
<!-- sq:body -->
## Scope

Redesign the "Team workflow" section of `src/squads/_rendering/templates/workflow.md.j2`
so it is driven generically from the loaded spec + playbook + roster instead of
hardcoded bundled type/kind/status literals, plus the data plumbing this needs in
`src/squads/_rendering/_engine.py`. Also fix the retype static example in
`workflow_static.md.j2`. This template is the shared source for both the `squads`
skill's cheatsheet and `sq workflow`.

## Covered REV-360 findings (FEAT-334 scope)

- MEDIUM — `workflow.md.j2:5` — authoring-lane blocks gated on literal
  `authoring_owner('feature')` + `item_subentity_kind('feature')=='story'` and the
  `task`/`subtask` equivalent; renamed/dropped types silently drop the guidance.
- MEDIUM — `workflow.md.j2:23` — "Sub-entities are tracked too" bullet hand-writes
  bundled kinds ("Subtasks & user stories", "review findings"), literal lifecycles
  ("Todo → InProgress → Done", "Open → Fixed → Verified"), `--severity high`, and
  type names task/feature/review.
- MEDIUM — `workflow_static.md.j2:19` — retype "Status behaviour" prose hardcodes
  workflow-sharing type pairs "task↔bug, feature↔epic"; wrong under custom vocab.
- LOW — `workflow.md.j2:33` — per-type skills bullet hardcodes example skill names
  `(sq-feature, sq-task, sq-bug, …)`.

## Design constraints (from FEAT-334)

- Iterate `spec.items` (non-meta) and the roster in declared order; render from
  `_interactions` data (`ItemPlaybookSpec`/`RoleGuideSpec`) + `authoring_owner(type)`
  + spec accessors — never an if-branch keyed to one specific type name.
- CONCISE cross-type overview: roughly one condensed line per type-role pairing
  (who acts + the single highest-signal handoff), NOT a duplicate of the full
  enter/do/handoff/watch that the per-type `sq-<type>` skills already render. State
  the chosen summarization/altitude rule in a code comment so a future editor knows
  why it stops short of full playbook detail (US2 acceptance).
- The retype static section should describe workflow-sharing generically (types that
  share a status machine) rather than naming bundled pairs.
- Note: `_interactions/__init__.py` `CREATE_LANES`/`authoring_owner()` is the data
  source for authoring lanes; the REV-360 LOW on CREATE_LANES documents it degrades
  gracefully (a custom type with no lane owner gets no authoring bullet) — consume it
  as-is, do not rework it here.

## Acceptance

- Rendered "Team workflow" section contains no hardcoded literal type/kind/status
  words as template text; every name in the output comes from iterating
  spec/playbook/roster (US1 acceptance).
- Every non-meta spec type with at least one playbook role guide renders at least one
  line; renaming a type changes only the rendered name, not whether guidance appears.
- Update the cheatsheet golden/snapshot(s) atomically with the template change; the
  bundled-default render carries every fact present today (authoring flow, subtask→
  story mapping, sub-entity machines, hierarchy line, alias table, lifecycle table,
  retype/remove-vs-cancel/ref-kind static sections) — nothing the default squad relies
  on silently disappears (US3).
- `uv run pytest`, `uv run pyright`, `uv run ruff check .`, `ruff format --check .`
  all clean.

## Notes

Already-generic parts (alias table, lifecycle table iterating `spec.machine_for(...)`)
stay untouched except as needed to keep them consistent. Do not touch the per-type
`sq-<type>` skill templates (FEAT-334 non-goal). The tech-writer/altitude read-through
(US2/US3 human verification) is the sibling verification task.
<!-- sq:body:end -->

## Subtasks

_Add with `sq task 363 add-subtask "<title>"`; track with `sq task 363 subtask <n> update --status <Status>`._

<!-- sq:summary -->
<!-- sq:summary:end -->

<!-- sq:subtasks -->
<!-- sq:subtasks:end -->

## Discussion

<!-- sq:discussion -->
<!-- sq:discussion:end -->
