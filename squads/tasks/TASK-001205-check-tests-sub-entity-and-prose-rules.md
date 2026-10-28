---
id: TASK-1205
sequence_id: 1205
type: task
title: 'Check tests: sub-entity and prose rules'
status: Done
parent: FEAT-1202
author: tech-lead
refs:
- TASK-1203:depends-on
subentities:
- local_id: ST1
  title: Sub-entity rule tests
  status: Done
  story: US3
- local_id: ST2
  title: Prose rule tests
  status: Done
  story: US3
- local_id: ST3
  title: Falsify each test three ways
  status: Done
  story: US3
created_at: '2026-10-28T08:37:59Z'
updated_at: '2026-10-28T10:41:07Z'
---
<!-- sq:body -->
## Scope

FEAT-1202 US3: breach tests in `tests/check/test_subentity_rules.py` and `tests/check/test_prose_rules.py` for 12 `CATALOG` members.

- `test_subentity_rules.py` (7): `subtask_story_mapping`, `subentity_status_valid`, `subentity_container_marker`, `subentity_body_written`, `subentity_title_max` (opt-in), `subentity_deferral_resolved`, `subentities_settled_with_parent`.
- `test_prose_rules.py` (5): `no_status_banner`, `item_title_max`, `body_written`, `description_present`, `external_id_not_in_title` (no bundled type selects them, so all five are opt-in).

Gated members (`subtask_story_mapping`, `subentity_status_valid`, `subentity_container_marker` at error) are arranged by the file write plus `sq repair`.

## Cases

- 12 breach cases.
- 3 param cases: `subentity_title_max:param` with a length between the param and the default, so the param reports and the default would not; `item_title_max:param` and `external_id_not_in_title:param` are required-param members, so each param case is also its breach case.
- 11 level cases: every member except `subentity_container_marker`, whose floor equals its default.

## Acceptance

- Each of the 12 rules has a breach test with its clean pre-state and a near-miss sibling at the boundary (title lengths, the id pattern).
- The 3 param cases use a value the default would judge differently; the 11 level cases assert level and exit code.
- The guard reports none of these 12 rules as undeclared.

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

_Add with `sq task 1205 add-subtask "<title>"`; track with `sq task 1205 subtask <n> update --status <Status>`._

<!-- sq:subtasks -->

<!-- sq:subtask:ST1 -->
### ST1 — Sub-entity rule tests

<!-- sq:subtask:ST1:body -->
`tests/check/test_subentity_rules.py`: breach tests for `subtask_story_mapping`, `subentity_status_valid`, `subentity_container_marker`, `subentity_body_written`, `subentity_title_max`, `subentity_deferral_resolved` and `subentities_settled_with_parent`, level cases for all but `subentity_container_marker`, and `subentity_title_max:param` with a length between the param and the default.
<!-- sq:subtask:ST1:body:end -->

#### Discussion

<!-- sq:subtask:ST1:discussion -->
<!-- sq:subtask:ST1:discussion:end -->
<!-- sq:subtask:ST1:end -->

<!-- sq:subtask:ST2 -->
### ST2 — Prose rule tests

<!-- sq:subtask:ST2:body -->
`tests/check/test_prose_rules.py`: breach tests for `no_status_banner`, `item_title_max`, `body_written`, `description_present` and `external_id_not_in_title`, enabled through `select_validators`, with their level cases; the two required-param members carry their param case on the breach test, with a near-miss at the boundary.
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
- [2026-10-28T09:00:19Z] `python-dev` Elias Python:
  - Implemented in fc060f62: tests/check/test_subentity_rules.py (14), test_prose_rules.py (11); 26 declarations removed from PENDING. tests/check+meta 694 passed after merge; pyright/ruff clean; each rule falsified three ways, src restored.
<!-- sq:discussion:end -->
