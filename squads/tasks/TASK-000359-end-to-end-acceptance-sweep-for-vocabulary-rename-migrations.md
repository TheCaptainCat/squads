---
id: TASK-359
sequence_id: 359
type: task
title: End-to-end acceptance sweep for vocabulary rename migrations
status: Done
parent: FEAT-281
author: tech-lead
subentities:
- local_id: ST1
  title: End-to-end acceptance of rename-type
  status: Todo
  story: US1
- local_id: ST2
  title: End-to-end acceptance of rename-status
  status: Todo
  story: US2
created_at: '2026-07-09T21:34:36Z'
updated_at: '2026-07-13T09:27:39Z'
---
<!-- sq:body -->
Feature-acceptance sweep proving FEAT-281's criteria end-to-end (separate from the per-task unit/smoke tests in 355-358; this is the honest ground-truth gate — green unit tests are not acceptance).

AC1 (rename-type full): on a squad with a 'ticket' type declared via .overrides/workflow.toml, seed FEAT/TASK/REV items that CARRY sub-entities (stories/subtasks/findings) and non-initial statuses, plus cross-refs and prose @mentions/ID mentions between them; run rename-type task ticket; assert all TASK-… ids -> TICKET-…, the folder moved, every parent/ref/frontmatter and prose mention rewritten, and CRITICALLY that sub-entities AND status are preserved unconditionally (the retype guardrails would have rejected/reset these — the whole point of the feature). Then assert 'sq check' and 'sq repair' are both clean (repair produces no diff).

AC2 (rename-status fail-closed): rename-status to a status NOT in the type's lifecycle fails cleanly with no partial rewrite (assert every item's status unchanged after the failed call). Plus a happy-path rename-status moving all matching items.

AC3 (audit): assert one reflog line per renamed item (op rename-type / rename-status) and a system discussion comment per item, consistent with retype's trail.

AC4 (reserved meta): rename-type / rename-status on role|skill|operator is rejected with a clear error.

AC5 (no schema drift): assert SCHEMA_VERSION is unchanged and _migrations/_registry.py has no new entry (guards the re-baseline #4 decision).

Files owned: tests/ (new acceptance test module, name by behaviour not ticket id per project convention). May add a shared .overrides/workflow.toml fixture under tests/ if 358 didn't. Depends on TASK-358 (full CLI path in place).
<!-- sq:body:end -->

## Subtasks

_Add with `sq task 359 add-subtask "<title>"`; track with `sq task 359 subtask <n> update --status <Status>`._

<!-- sq:summary -->
| Subtask | Status | Assignee | Title | Story |
| --- | --- | --- | --- | --- |
| ST1 | Todo |  | End-to-end acceptance of rename-type | US1 |
| ST2 | Todo |  | End-to-end acceptance of rename-status | US2 |
<!-- sq:summary:end -->

<!-- sq:subtasks -->

<!-- sq:subtask:ST1 -->
### ST1 — End-to-end acceptance of rename-type

<!-- sq:subtask:ST1:head -->
**Status:** ⚪ Todo
**Implements:** US1 — As a project admin, I want sq migrate rename-type to safely rename a built-in type across my whole squad
<!-- sq:subtask:ST1:head:end -->

<!-- sq:subtask:ST1:body -->
End-to-end acceptance of rename-type: on a squad with a target type declared via `.overrides/workflow.toml`, seeded items carrying sub-entities, non-initial statuses, cross-refs, and prose mentions are renamed and every id, folder, parent/ref, frontmatter, and prose mention is rewritten — with sub-entities and status preserved unconditionally (the point of the feature, which retype's guardrails would have rejected or reset) — and `sq check` plus `sq repair` both come out clean. Covered by the behaviour-named `tests/test_rename_acceptance.py`.
<!-- sq:subtask:ST1:body:end -->

#### Discussion

<!-- sq:subtask:ST1:discussion -->
<!-- sq:subtask:ST1:discussion:end -->
<!-- sq:subtask:ST1:end -->

<!-- sq:subtask:ST2 -->
### ST2 — End-to-end acceptance of rename-status

<!-- sq:subtask:ST2:head -->
**Status:** ⚪ Todo
**Implements:** US2 — As a project admin, I want sq migrate rename-status to safely rename a status across all items of a type
<!-- sq:subtask:ST2:head:end -->

<!-- sq:subtask:ST2:body -->
End-to-end acceptance of rename-status: a rename to a status outside the type's lifecycle fails closed with no partial rewrite (every item's status unchanged after the failed call), plus a happy-path move of all matching items. Also asserts the audit trail (one reflog line + one system discussion comment per item), reserved-meta rejection, and no `SCHEMA_VERSION`/registry drift.
<!-- sq:subtask:ST2:body:end -->

#### Discussion

<!-- sq:subtask:ST2:discussion -->
<!-- sq:subtask:ST2:discussion:end -->
<!-- sq:subtask:ST2:end -->
<!-- sq:subtasks:end -->

## Discussion

<!-- sq:discussion -->
- [2026-07-10T01:28:10Z] Mara Tester:
  - Starting FEAT-281 acceptance sweep: writing behaviour-named test module exercising AC1-AC5 end-to-end through service/CLI.
- [2026-07-10T01:37:12Z] Mara Tester:
  - FEAT-281 acceptance verdict: AC1-AC5 all PASS end-to-end (real .overrides/workflow.toml + open_service(), not a hand-built spec).
  - AC1: rename-type task ticket via CLI rewrites ids/folder/parent/refs/prose; sub-entities + non-initial status carried unconditionally; sq check + sq repair clean, repair produces no index diff.
  - AC2: rename-status to a non-member status (e.g. task->Approved) fails closed with zero status drift across all items; happy-path move verified scoped per-type.
  - AC3: one reflog line + one system discussion comment per renamed/moved item, verified for both ops.
  - AC4: rename-type/rename-status on role|skill|operator rejected with 'reserved meta-type' via CLI, exit != 0.
  - AC5: SCHEMA_VERSION unchanged across both ops; _migrations/_registry.py has no rename entry and its highest to_schema still matches SCHEMA_VERSION.
  - Real gap found (not in rename_type/rename_status itself): BUG-362 -- once a rename-target type shares subentity_kind with the type it's replacing (task->ticket, both 'subtask', exactly this feature's own worked example), add_subtask/add_finding/add_story on a pre-existing old-type item breaks (ambiguous kind->owner map in _base.py::subentity_parent_map). Worked around in the acceptance test by seeding before writing the override; filed as BUG-362, commented on FEAT-281.
  - Module: tests/test_rename_acceptance.py (14 tests, all green). Fast gates green: pyright, ruff check, ruff format --check, plus test_squad_ref_hygiene.py. Did not run the full suite (main loop's job). Leaving TASK-359 InProgress for tech-lead/manager to close out alongside BUG-362 triage.
- [2026-07-10T01:53:00Z] Paul Reviewer:
  - Reviewed the finalized acceptance sweep (tests/test_rename_acceptance.py) alongside the BUG-362 fix. VERDICT: APPROVE — the ACs genuinely hold with the de-workaround; full suite green (exit 0, 0 failures).
  - De-workaround truly proves BUG-362 fixed (Q4): YES. _seed_scenario writes .overrides/workflow.toml declaring ticket (subentity_kind=subtask) and loads it via open_service() through the real loader/merge/validate path FIRST (lines 60-65), THEN add_subtask on pre-existing task1/task2 items (lines 79-80) while task+ticket share the kind — the exact BUG-362 repro. Before the fix, seeding itself would raise at line 79; it no longer sidesteps via seeding order.
  - AC coverage genuine (Q5): AC1 — rename_type end-to-end asserts status carried unconditionally (InProgress/Blocked), sub-entities carried (title checks), folder moved on disk, parent/child/cross-ref/prose-mention rewrites, AND sq check exit 0 + repair produces byte-identical item data (frontmatter is source of truth). AC2 — rename_status per-type scoping (rev untouched) + invalid-target fail-closed with statuses unchanged (no partial rewrite). AC3 — reflog+comment per item for both. AC4 — reserved-meta parametrized over role/skill/operator for both. AC5 — no SCHEMA_VERSION drift + registry has no rename entry. Mara's all-PASS verdict corroborated.
  - Note (carried from the fix review): 3 new BUG-362 references in test comments (test_rename_acceptance.py:54,77; test_subentity_kind_spec_driven.py:62) — LOW hygiene, drop the ID token, keep the behavior prose; matches an existing pattern, non-blocking. subentity_parent_map + the subentity_parent property now have NO functional src caller (only a test asserts the map) — consider removing the footgun map in a later hygiene pass, or keep as the documented naming-hint. Neither blocks acceptance.
- [2026-07-10T01:55:27Z] Catherine Manager:
  - Acceptance sweep: all 5 ACs PASS (verified through the real CLI/loader). Surfaced BUG-362 (now fixed) and de-worked-around to prove the real declare-then-rename pattern. Reviewer-approved; full suite green. Landing.
<!-- sq:discussion:end -->
