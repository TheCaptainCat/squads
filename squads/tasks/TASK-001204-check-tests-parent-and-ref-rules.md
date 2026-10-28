---
id: TASK-1204
sequence_id: 1204
type: task
title: 'Check tests: parent and ref rules'
status: Done
parent: FEAT-1202
author: tech-lead
refs:
- TASK-1203:depends-on
subentities:
- local_id: ST1
  title: Parent rule tests
  status: Done
  story: US2
- local_id: ST2
  title: Ref rule tests
  status: Done
  story: US2
- local_id: ST3
  title: Falsify each test three ways
  status: Done
  story: US2
created_at: '2026-10-28T08:37:58Z'
updated_at: '2026-10-28T10:41:06Z'
---
<!-- sq:body -->
## Scope

FEAT-1202 US2: breach tests in `tests/check/test_parent_rules.py` and `tests/check/test_ref_rules.py` for 9 `CATALOG` members.

- `test_parent_rules.py` (4): `parent_in`, `no_parent`, `parent_present` (opt-in, through `select_validators`), `parent_acyclic`.
- `test_ref_rules.py` (5): `dangling_ref`, `ref_kind_valid`, `supersedes_incoming`, `ref_rule_target_present`, `ref_rule_target_typed` (opt-in).

Members the create/update gate refuses (error level: `parent_in`, `no_parent`, `parent_acyclic`, and `parent_present` once selected) are arranged by writing the item file and running `sq repair`.

## Cases

- 9 breach cases.
- 1 param case: `ref_rule_target_present:param`, a multi-selection member, so one case selects two params, one breached and one satisfied, asserting resolution and the union.
- 8 level cases: `@<level>` at the non-default level for each member except `parent_acyclic`, whose floor equals its default.

## Acceptance

- Each of the 9 rules has a breach test with its clean pre-state, and a near-miss sibling where the rule has a boundary.
- The param case and the 8 level cases exist; each level case asserts the issue's level and the exit code that level earns.
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

_Add with `sq task 1204 add-subtask "<title>"`; track with `sq task 1204 subtask <n> update --status <Status>`._

<!-- sq:subtasks -->

<!-- sq:subtask:ST1 -->
### ST1 — Parent rule tests

<!-- sq:subtask:ST1:body -->
`tests/check/test_parent_rules.py`: breach tests for `parent_in`, `no_parent`, `parent_present` and `parent_acyclic`, gated breaches arranged by file write plus `sq repair`, with level cases for all but `parent_acyclic`.
<!-- sq:subtask:ST1:body:end -->

#### Discussion

<!-- sq:subtask:ST1:discussion -->
<!-- sq:subtask:ST1:discussion:end -->
<!-- sq:subtask:ST1:end -->

<!-- sq:subtask:ST2 -->
### ST2 — Ref rule tests

<!-- sq:subtask:ST2:body -->
`tests/check/test_ref_rules.py`: breach tests for `dangling_ref`, `ref_kind_valid`, `supersedes_incoming`, `ref_rule_target_present` and `ref_rule_target_typed`, their level cases, and the `ref_rule_target_present:param` case selecting two params, one breached and one satisfied.
<!-- sq:subtask:ST2:body:end -->

#### Discussion

<!-- sq:subtask:ST2:discussion -->
<!-- sq:subtask:ST2:discussion:end -->
<!-- sq:subtask:ST2:end -->

<!-- sq:subtask:ST3 -->
### ST3 — Falsify each test three ways

<!-- sq:subtask:ST3:body -->
For each test: break the member's detection (breach goes red), make it report unconditionally (pre-state goes red), make its param or level resolution fall back to the default (param or level case goes red); restore and record each edit in the handback.
<!-- sq:subtask:ST3:body:end -->

#### Discussion

<!-- sq:subtask:ST3:discussion -->
<!-- sq:subtask:ST3:discussion:end -->
<!-- sq:subtask:ST3:end -->
<!-- sq:subtasks:end -->

## Discussion

<!-- sq:discussion -->
- [2026-10-28T08:57:45Z] `python-dev` Elias Python:
  - Implemented in 3131ce0e: tests/check/test_parent_rules.py (7), test_ref_rules.py (11), shared tests/check/_arrange.py; 18 declarations removed from PENDING. tests/check+meta 669 passed; pyright/ruff clean; each rule falsified three ways, src restored.
<!-- sq:discussion:end -->
