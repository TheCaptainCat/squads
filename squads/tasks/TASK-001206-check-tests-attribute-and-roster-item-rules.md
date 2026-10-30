---
id: TASK-1206
sequence_id: 1206
type: task
title: 'Check tests: attribute and roster item rules'
status: Done
parent: FEAT-1202
author: tech-lead
refs:
- TASK-1203:depends-on
subentities:
- local_id: ST1
  title: Field and attribute rule tests
  status: Done
  maps_to: US4
- local_id: ST2
  title: Roster item rule tests
  status: Done
  maps_to: US4
- local_id: ST3
  title: Falsify each test three ways
  status: Done
  maps_to: US4
created_at: '2026-10-28T08:38:00Z'
updated_at: '2026-10-28T10:41:08Z'
---
<!-- sq:body -->
## Scope

FEAT-1202 US4: breach tests in `tests/check/test_attribute_and_roster_item_rules.py` for 6 `CATALOG` members: the item field and attribute rules and the per-item rules on roster types.

- Field and attribute rules: `item_status_valid`, `agent_registered`, `attribute_valid`, `frontmatter_key_undeclared`.
- Roster item rules: `pronouns_valid` (roster bundle), `item_skill_shadowed` (selected on `skill`).

Gated members (`item_status_valid`, `attribute_valid`, `pronouns_valid` at error) are arranged by the file write plus `sq repair`.

## Cases

- 6 breach cases.
- No param case: none of these members takes a param.
- 6 level cases, one per member at its non-default level.

## Acceptance

- Each of the 6 rules has a breach test with its clean pre-state; an opt-in member is enabled through `select_validators`.
- The 6 level cases assert level and exit code.
- The guard reports none of these 6 rules as undeclared.

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

_Add with `sq task 1206 add-subtask "<title>"`; track with `sq task 1206 subtask <n> update --status <Status>`._

<!-- sq:subtasks -->

<!-- sq:subtask:ST1 -->
### ST1 — Field and attribute rule tests

<!-- sq:subtask:ST1:body -->
In `tests/check/test_attribute_and_roster_item_rules.py`: breach and level cases for `item_status_valid`, `agent_registered`, `attribute_valid` and `frontmatter_key_undeclared`, gated breaches arranged by file write plus `sq repair`.
<!-- sq:subtask:ST1:body:end -->

#### Discussion

<!-- sq:subtask:ST1:discussion -->
<!-- sq:subtask:ST1:discussion:end -->
<!-- sq:subtask:ST1:end -->

<!-- sq:subtask:ST2 -->
### ST2 — Roster item rule tests

<!-- sq:subtask:ST2:body -->
In the same module: breach and level cases for `pronouns_valid` on a roster entry and `item_skill_shadowed` on a skill.
<!-- sq:subtask:ST2:body:end -->

#### Discussion

<!-- sq:subtask:ST2:discussion -->
<!-- sq:subtask:ST2:discussion:end -->
<!-- sq:subtask:ST2:end -->

<!-- sq:subtask:ST3 -->
### ST3 — Falsify each test three ways

<!-- sq:subtask:ST3:body -->
For each test: break the member's detection, make it report unconditionally, make its level resolution fall back to the default; each must turn its case red. Restore and record each edit in the handback.
<!-- sq:subtask:ST3:body:end -->

#### Discussion

<!-- sq:subtask:ST3:discussion -->
<!-- sq:subtask:ST3:discussion:end -->
<!-- sq:subtask:ST3:end -->
<!-- sq:subtasks:end -->

## Discussion

<!-- sq:discussion -->
- [2026-10-28T09:32:42Z] `python-dev` Elias Python:
  - Implemented in b1fa0c35: tests/check/test_attribute_and_roster_item_rules.py (12 tests, 6 rules + level cases); _arrange gains add_roster and a recursive rewrite; 12 PENDING entries removed. tests/check+meta 716 passed; each rule falsified three ways, src restored.
<!-- sq:discussion:end -->
