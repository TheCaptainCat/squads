---
id: TASK-1207
sequence_id: 1207
type: task
title: 'Check tests: roster config rules'
status: Done
parent: FEAT-1202
author: tech-lead
refs:
- TASK-1203:depends-on
subentities:
- local_id: ST1
  title: Roster member tests
  status: Done
  maps_to: US5
- local_id: ST2
  title: Display, language and view member tests
  status: Done
  maps_to: US5
- local_id: ST3
  title: Falsify each test two ways
  status: Done
  maps_to: US5
created_at: '2026-10-28T08:38:01Z'
updated_at: '2026-10-28T10:41:09Z'
---
<!-- sq:body -->
## Scope

FEAT-1202 US5: breach tests in `tests/check/test_roster_config_rules.py` for 9 always-on `SQUAD_GLOBAL_CATALOG` members.

- Roster: `roster_config_integrity`, `default_designation_duplicated`, `roster_slug_valid`, `role_base_resolves`, `role_definition_shadowed`, `playbook_guide_role_live`.
- Display and language: `display_config_valid`, `working_language_valid`.
- Views: `view_transform_resolves`.

The two always-on reconciliation members (`index_reconciled`, `backend_reconciled`) belong to the corpus integrity task.

## Cases

- 9 breach cases.
- No param or level case: always-on members cannot be selected (ADR-1201 rule 2).

## Acceptance

- Each of the 9 members has a breach test asserting the whole array and exit code, with its clean pre-state.
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

_Add with `sq task 1207 add-subtask "<title>"`; track with `sq task 1207 subtask <n> update --status <Status>`._

<!-- sq:subtasks -->

<!-- sq:subtask:ST1 -->
### ST1 — Roster member tests

<!-- sq:subtask:ST1:body -->
In `tests/check/test_roster_config_rules.py`: breach tests for `roster_config_integrity`, `default_designation_duplicated`, `roster_slug_valid`, `role_base_resolves`, `role_definition_shadowed` and `playbook_guide_role_live`, each asserting the whole array and exit code.
<!-- sq:subtask:ST1:body:end -->

#### Discussion

<!-- sq:subtask:ST1:discussion -->
<!-- sq:subtask:ST1:discussion:end -->
<!-- sq:subtask:ST1:end -->

<!-- sq:subtask:ST2 -->
### ST2 — Display, language and view member tests

<!-- sq:subtask:ST2:body -->
In the same module: breach tests for `display_config_valid`, `working_language_valid` and `view_transform_resolves`. No level case: these members are always on.
<!-- sq:subtask:ST2:body:end -->

#### Discussion

<!-- sq:subtask:ST2:discussion -->
<!-- sq:subtask:ST2:discussion:end -->
<!-- sq:subtask:ST2:end -->

<!-- sq:subtask:ST3 -->
### ST3 — Falsify each test two ways

<!-- sq:subtask:ST3:body -->
Always-on members have no param or level case, so each test is shown red on breach (detection broken) and on clean (member reports unconditionally). Restore and record each edit in the handback.
<!-- sq:subtask:ST3:body:end -->

#### Discussion

<!-- sq:subtask:ST3:discussion -->
<!-- sq:subtask:ST3:discussion:end -->
<!-- sq:subtask:ST3:end -->
<!-- sq:subtasks:end -->

## Discussion

<!-- sq:discussion -->
- [2026-10-28T09:43:15Z] `python-dev` Elias Python:
  - Implemented in 72866d67: tests/check/test_roster_config_rules.py (9 always-on members); _arrange gains write_override, edit_config, role_id; check_json parses stdout (a stderr warning preceded the JSON). tests/check+meta 725 passed; each rule falsified breach+clean, src restored.
<!-- sq:discussion:end -->
