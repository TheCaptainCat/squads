---
id: TASK-1208
sequence_id: 1208
type: task
title: 'Check tests: work policy rules'
status: Done
parent: FEAT-1202
author: tech-lead
refs:
- TASK-1203:depends-on
subentities:
- local_id: ST1
  title: Selectable squad-wide member tests
  status: Done
  maps_to: US6
- local_id: ST2
  title: Per-item work policy tests
  status: Done
  maps_to: US6
- local_id: ST3
  title: Falsify each test three ways
  status: Done
  maps_to: US6
created_at: '2026-10-28T08:38:02Z'
updated_at: '2026-10-28T10:41:10Z'
---
<!-- sq:body -->
## Scope

FEAT-1202 US6: breach tests in `tests/check/test_work_policy_rules.py` for 9 members: the 6 selectable `SQUAD_GLOBAL_CATALOG` members and 3 opt-in per-item work policy members of `CATALOG`.

- Selectable squad-wide (through `select_validators` on `[squad] validators`): `type_has_live_author`, `children_settled_with_parent`, `dependency_acyclic`, `wip_limit`, `unassigned_active`, `stale_active`. `stale_active` ages its items with the frozen clock, never a real wait.
- Per-item work policy (selected on one work type): `assignee_present`, `blocked_has_blocker`, `settled_requires_discussion`.

## Cases

- 9 breach cases.
- 3 param cases: `wip_limit:param`, `unassigned_active:param`, `stale_active:param`. Each param is required (`SQUAD_GLOBAL_PARAM_MINIMUM`), so each param case is also the member's breach case; the near-miss sits exactly at the limit or age.
- 9 level cases: one per member at its non-default level.

## Acceptance

- Each of the 9 members has a breach test with its clean pre-state, enabled through `select_validators`.
- The 3 param cases and the 9 level cases exist and assert level and exit code.
- The guard reports none of these 9 rules as undeclared.

## Ground rules (every check rule task)

- Rulebook: ADR-1201, with ADR-1172 rules 4 and 5 for in-process runs on a copied squad under the frozen clock. Read it first; its rules are cited here, not restated.
- Every breach test runs `check_json` twice: on the arranged pre-state, asserting `[]`, then after the one breaching change, asserting the whole JSON array (rule, level, message, item) and the exit code (3 when the list holds an error, 0 otherwise). Where the member has a boundary, a sibling item left at the boundary stays in the arranged state as a near-miss.
- Declare with `@pytest.mark.breaches(...)` using literal strings: `"<rule>"`, `"<rule>:param"`, `"<rule>@<level>"`. Param and level cases are never crossed with each other or with other members.
- Opt-in members are enabled only through `select_validators` (a minimal override that selects the one member on one type and keeps the bundled selection by splat reference).
- Gated breaches are arranged by writing the item file and running `sq repair`; drift breaches by the file write alone. Only `sq check --json` output honours a declaration.
- Falsify each test three ways when written (breach, clean, param or level), restore, and record in the handback which edit turned each case red.
- Gates: `uv run --all-extras pyright`, `uv run --all-extras ruff check .` and `ruff format --check .`, `tests/check` and `tests/meta` green, `sq check` clean. Test names describe behaviour; no ticket ids in code; docstrings of one or two sentences.
<!-- sq:body:end -->

## Subtasks

_Add with `sq task 1208 add-subtask "<title>"`; track with `sq task 1208 subtask <n> update --status <Status>`._

<!-- sq:subtasks -->

<!-- sq:subtask:ST1 -->
### ST1 — Selectable squad-wide member tests

<!-- sq:subtask:ST1:body -->
In `tests/check/test_work_policy_rules.py`: breach and level cases for `type_has_live_author`, `children_settled_with_parent`, `dependency_acyclic`, `wip_limit`, `unassigned_active` and `stale_active`, selected through `select_validators`; the three required-param members carry their param case on the breach test, `stale_active` aged with the frozen clock.
<!-- sq:subtask:ST1:body:end -->

#### Discussion

<!-- sq:subtask:ST1:discussion -->
<!-- sq:subtask:ST1:discussion:end -->
<!-- sq:subtask:ST1:end -->

<!-- sq:subtask:ST2 -->
### ST2 — Per-item work policy tests

<!-- sq:subtask:ST2:body -->
In the same module: breach and level cases for `assignee_present`, `blocked_has_blocker` and `settled_requires_discussion`, each selected on one work type.
<!-- sq:subtask:ST2:body:end -->

#### Discussion

<!-- sq:subtask:ST2:discussion -->
<!-- sq:subtask:ST2:discussion:end -->
<!-- sq:subtask:ST2:end -->

<!-- sq:subtask:ST3 -->
### ST3 — Falsify each test three ways

<!-- sq:subtask:ST3:body -->
For each test: break the member's detection, make it report unconditionally, make its param or level resolution fall back to the default; each must turn its case red. Restore and record each edit in the handback.
<!-- sq:subtask:ST3:body:end -->

#### Discussion

<!-- sq:subtask:ST3:discussion -->
<!-- sq:subtask:ST3:discussion:end -->
<!-- sq:subtask:ST3:end -->
<!-- sq:subtasks:end -->

## Discussion

<!-- sq:discussion -->
- [2026-10-28T09:52:11Z] `python-dev` Elias Python:
  - Implemented in 06949539: tests/check/test_work_policy_rules.py (18 tests: 9 rules, 3 param, 9 level); _arrange gains at() over sq --at for the frozen-clock stale case. tests/check+meta 743 passed after merge; each rule falsified breach/clean/level/param, src restored.
<!-- sq:discussion:end -->
