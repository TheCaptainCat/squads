---
id: TASK-1203
sequence_id: 1203
type: task
title: 'Check tests: harness, breaches guard and baseline'
status: Done
parent: FEAT-1202
author: tech-lead
subentities:
- local_id: ST1
  title: check_json, select_validators and teardown
  status: Done
  story: US1
- local_id: ST2
  title: Check surface derivation and breaches guard
  status: Done
  story: US1
- local_id: ST3
  title: Baseline test
  status: Done
  story: US1
- local_id: ST4
  title: Show the guard and teardown red
  status: Done
  story: US1
created_at: '2026-10-28T08:37:57Z'
updated_at: '2026-10-28T10:31:31Z'
---
<!-- sq:body -->
## Scope

FEAT-1202 US1: the harness every rule task builds on, as ADR-1201 rules 1, 3, 4 and 7 and its Consequences section name it. This task owns no rule of the three tables; it owns the baseline.

1. **`tests/check/conftest.py`**: `check_json` (runs `sq check --json` through `invoke`, returns the parsed array and exit code, records the reported (rule, level) pairs); `select_validators` (writes the minimal `squads/.overrides/workflow.toml` selecting the given entries on one type or in `[squad] validators`, keeping the bundled selection with `"$(*items.<type>.validators)"` / `"$(*squad.validators)"`, and records what it selected and with which param); the `breaches` teardown.
2. **The per-test check** (ADR-1201 rule 4): at teardown, fail when `rule` was reported by none of the test's runs, `rule@<level>` was not reported at that level, or `rule:param` was declared but `select_validators` did not select that member with a param. A test declaring `breaches` without `check_json` fails.
3. **`tests/_check_surface.py`**: derives the required declarations from `CATALOG`, `SQUAD_GLOBAL_CATALOG`, `BINDING_RULES` and the name tables (`PARAMETERIZED_VALIDATOR_NAMES`, `SQUAD_GLOBAL_PARAM_MINIMUM`, `REQUIRED_PARAM_VALIDATOR_NAMES`, `DEFAULT_VALIDATOR_LEVEL`, `VALIDATOR_LEVEL_FLOOR`, `SELECTABLE_SQUAD_GLOBAL_NAMES`, `DEFAULT_SQUAD_GLOBAL_LEVEL`), with no stored list of rules. Today that is 69 breach declarations, 7 param cases and 34 level cases.
4. **The guard** in `tests/meta`, built like the `covers` guard: reads every `breaches` marker under `tests/check/` with `ast`, counting only collected tests that run; fails on a required declaration no test makes and on a stale one.
5. **Register `breaches`** under `[tool.pytest.ini_options] markers`.
6. **`tests/check/test_baseline.py`**: `test_the_baseline_squad_reports_no_issue`, the `minimal` squad under the bundled spec reports `[]` with exit 0.

## Acceptance

- The guard passes on the tree and fails on a seeded missing, stale or undeclared rule, param or level (each shown red once, recorded in the handback).
- A test declaring `breaches` without `check_json` fails; a declaration no run honours fails that test at teardown (shown with seeded tests that are then removed).
- The guard and the teardown stay valid under `-k`, `--lf` and xdist.
- `tests/meta` keeps passing, including the naming and ticket-reference guards.

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

_Add with `sq task 1203 add-subtask "<title>"`; track with `sq task 1203 subtask <n> update --status <Status>`._

<!-- sq:subtasks -->

<!-- sq:subtask:ST1 -->
### ST1 — check_json, select_validators and teardown

<!-- sq:subtask:ST1:body -->
In `tests/check/conftest.py`: `check_json` runs `sq check --json` through `invoke` and records the reported (rule, level) pairs; `select_validators` writes the minimal override with splat references and records what it selected; the `breaches` teardown fails an unhonoured `rule`, `rule@<level>` or `rule:param` declaration, and a `breaches` test without `check_json`.
<!-- sq:subtask:ST1:body:end -->

#### Discussion

<!-- sq:subtask:ST1:discussion -->
<!-- sq:subtask:ST1:discussion:end -->
<!-- sq:subtask:ST1:end -->

<!-- sq:subtask:ST2 -->
### ST2 — Check surface derivation and breaches guard

<!-- sq:subtask:ST2:body -->
`tests/_check_surface.py` derives the required breach, param and level declarations from the three rule tables and the name tables, with no stored rule list. The `tests/meta` guard reads `breaches` markers under `tests/check/` with `ast`, fails on missing and stale declarations. Register the `breaches` marker.
<!-- sq:subtask:ST2:body:end -->

#### Discussion

<!-- sq:subtask:ST2:discussion -->
<!-- sq:subtask:ST2:discussion:end -->
<!-- sq:subtask:ST2:end -->

<!-- sq:subtask:ST3 -->
### ST3 — Baseline test

<!-- sq:subtask:ST3:body -->
`tests/check/test_baseline.py`: `test_the_baseline_squad_reports_no_issue` asserts the `minimal` squad under the bundled spec reports `[]` with exit 0.
<!-- sq:subtask:ST3:body:end -->

#### Discussion

<!-- sq:subtask:ST3:discussion -->
<!-- sq:subtask:ST3:discussion:end -->
<!-- sq:subtask:ST3:end -->

<!-- sq:subtask:ST4 -->
### ST4 — Show the guard and teardown red

<!-- sq:subtask:ST4:body -->
Seed a missing, a stale and an undeclared rule, param and level, and a test whose declaration no run honours; show each red, remove the seeds, and confirm the guard and teardown hold under `-k`, `--lf` and xdist. Record each in the handback.
<!-- sq:subtask:ST4:body:end -->

#### Discussion

<!-- sq:subtask:ST4:discussion -->
<!-- sq:subtask:ST4:discussion:end -->
<!-- sq:subtask:ST4:end -->
<!-- sq:subtasks:end -->

## Discussion

<!-- sq:discussion -->
- [2026-10-28T08:46:10Z] `python-dev` Elias Python:
  - Built: tests/check/conftest.py (check_json, select_validators, observed record, breaches teardown, breaches-without-check_json failure), tests/_check_surface.py (69 breach, 7 param, 34 level declarations derived from the tables), tests/_marker_ast.py (marker reading shared with the covers guard), the breaches guard in tests/meta with a PENDING list of all 110 declarations, the registered marker, and tests/check/test_baseline.py. Falsifications run red once and removed; tests/check + tests/meta green (651 passed).
<!-- sq:discussion:end -->
