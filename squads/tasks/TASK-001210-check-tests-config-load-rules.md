---
id: TASK-1210
sequence_id: 1210
type: task
title: 'Check tests: config load rules'
status: Done
parent: FEAT-1202
author: tech-lead
refs:
- TASK-1203:depends-on
subentities:
- local_id: ST1
  title: Override check tests
  status: Done
  story: US8
- local_id: ST2
  title: Config load tests
  status: Done
  story: US8
- local_id: ST3
  title: Empty the pending list
  status: Done
  story: US8
- local_id: ST4
  title: Falsify each test two ways
  status: Done
  story: US8
created_at: '2026-10-28T08:38:04Z'
updated_at: '2026-10-28T10:41:13Z'
---
<!-- sq:body -->
## Scope

FEAT-1202 US8: breach tests in `tests/check/test_config_load_rules.py` for 6 `BINDING_RULES`, and the guard green on the whole tree.

- Override checks: `override_stamped`, `override_current`, `override_loads`.
- Config load: `workflow_loads`, `playbook_loads`, `corpus_scans`.

`workflow_loads`, `playbook_loads` and `override_loads` each get one malformed override, reported; why a spec or override is refused at load is out of scope (ADR-1201 Scope). `corpus_scans` is arranged where the fallback spec cannot load the index: both overrides broken, or a workflow override dropping a type with live items.

## Cases

- 6 breach cases.
- No param or level case: binding rules cannot be selected.

## Acceptance

- Each of the 6 rules has a breach test with its clean pre-state.
- The guard is green on the full tree, with no missing or stale declaration.
- The full local run stays in the order of 25 s; record the measured time in the handback.

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

_Add with `sq task 1210 add-subtask "<title>"`; track with `sq task 1210 subtask <n> update --status <Status>`._

<!-- sq:subtasks -->

<!-- sq:subtask:ST1 -->
### ST1 — Override check tests

<!-- sq:subtask:ST1:body -->
In `tests/check/test_config_load_rules.py`: breach tests for `override_stamped`, `override_current` and `override_loads`, the last with one malformed override.
<!-- sq:subtask:ST1:body:end -->

#### Discussion

<!-- sq:subtask:ST1:discussion -->
<!-- sq:subtask:ST1:discussion:end -->
<!-- sq:subtask:ST1:end -->

<!-- sq:subtask:ST2 -->
### ST2 — Config load tests

<!-- sq:subtask:ST2:body -->
In the same module: breach tests for `workflow_loads` and `playbook_loads`, one malformed override each, and `corpus_scans` where the fallback spec cannot load the index.
<!-- sq:subtask:ST2:body:end -->

#### Discussion

<!-- sq:subtask:ST2:discussion -->
<!-- sq:subtask:ST2:discussion:end -->
<!-- sq:subtask:ST2:end -->

<!-- sq:subtask:ST3 -->
### ST3 — Empty the pending list

<!-- sq:subtask:ST3:body -->
Remove the guard's pending list once every rule is declared; confirm the guard is green on the full tree with no stale declaration, and record the full local run time in the handback.
<!-- sq:subtask:ST3:body:end -->

#### Discussion

<!-- sq:subtask:ST3:discussion -->
<!-- sq:subtask:ST3:discussion:end -->
<!-- sq:subtask:ST3:end -->

<!-- sq:subtask:ST4 -->
### ST4 — Falsify each test two ways

<!-- sq:subtask:ST4:body -->
No param or level case applies, so each test is shown red on breach (emission removed) and on clean (reported unconditionally). Restore and record each edit in the handback.
<!-- sq:subtask:ST4:body:end -->

#### Discussion

<!-- sq:subtask:ST4:discussion -->
<!-- sq:subtask:ST4:discussion:end -->
<!-- sq:subtask:ST4:end -->
<!-- sq:subtasks:end -->

## Discussion

<!-- sq:discussion -->
- [2026-10-28T09:59:05Z] `python-dev` Elias Python:
  - Implemented in a5769f0d: tests/check/test_config_load_rules.py (6 rules); _arrange gains write_override_as_is and stale_base. PENDING now holds only the corpus integrity declarations; it is removed when that task lands. Each rule falsified breach+clean, src restored.
- [2026-10-28T10:02:24Z] `python-dev` Elias Python:
  - ST3 done: PENDING and its logic/self-tests removed from the breaches guard; red on a seeded undeclared workflow_loads, green restored; gates clean.
<!-- sq:discussion:end -->
