---
id: TASK-350
sequence_id: 350
type: task
title: Retire global StatusSpec.completion; per-kind completion + rehome tests
status: Draft
parent: FEAT-212
author: tech-lead
refs:
- TASK-349:depends-on
created_at: '2026-07-09T21:31:27Z'
updated_at: '2026-07-09T21:33:35Z'
---
<!-- sq:body -->
The ADR-348-blessed StatusSpec.completion retirement (ADR-348 §2, resolves REV-337 F3). Isolated as its own step because it re-homes TASK-330's blessed code + its 5 regression tests onto the per-kind validator — the single decision that touches recently-blessed work.

## Scope

Add `completion: str` to `SubentityKindSpec` — names the done-toggle target status inside that kind's own machine.

Remove the global `StatusSpec.completion: bool` field (TASK-330's mechanism).

Rewrite `_check_completion_status`: iterate declared `self.subentity_kinds` (not kinds derived from ItemSpec.subentity_kind); assert each kind's `completion` names a **reachable, non-initial** state of that kind's `lifecycle`. This is FEAT-212 AC5's catch — a custom kind whose done-target falls outside its machine fails closed at load / `sq workflow lint`.

Rewrite `subentity_completion(kind)` to an O(1) `self.subentity_kinds[kind].completion` lookup (was a scan for the flagged status). Keep the same signature so _workflow/__init__.py re-export and callers are unchanged.

In default_workflow.toml move the two `completion = true` flags out of `[statuses.Done]`/`[statuses.Fixed]` and onto `[subentity_kinds.*].completion`: subtask=Done, story=Done, finding=Fixed (same targets TASK-330 encoded, relocated). Golden regenerates.

Re-home TASK-330's 5 regression tests in tests/test_workflow_spec.py (currently ~L518-560: no-completion-status, two-completion-status for subtask/story + finding, and the bundled resolves-one-per-kind assertion) onto the per-kind validator — e.g. a kind whose completion is unset / points at an undeclared or initial-only status now fails; the bundled resolves subtask/story=Done, finding=Fixed via the O(1) lookup.

## Files owned

- src/squads/_workflow/_models.py (StatusSpec.completion removal, _check_completion_status rewrite, subentity_completion rewrite)

- src/squads/_workflow/default_workflow.toml (relocate completion flags; golden regenerates)

- tests/test_workflow_spec.py (re-home the 5 TASK-330 tests)

## Acceptance

- No item-data migration (spec-schema-only change); bundled subentity_completion returns Done/Done/Fixed for subtask/story/finding.

- The 5 re-homed tests pass against the per-kind validator; a custom kind with an out-of-machine completion fails load (AC5).

- Golden regenerated; full suite green.

## Depends on

TASK-349 — needs subentity_kinds carrying the other keys first; shares _models.py + default_workflow.toml, so runs strictly after 349 (no parallel collision on the core files).
<!-- sq:body:end -->

## Subtasks

_Add with `sq task 350 add-subtask "<title>"`; track with `sq task 350 subtask <n> update --status <Status>`._

<!-- sq:summary -->
<!-- sq:summary:end -->

<!-- sq:subtasks -->
<!-- sq:subtasks:end -->

## Discussion

<!-- sq:discussion -->
<!-- sq:discussion:end -->
