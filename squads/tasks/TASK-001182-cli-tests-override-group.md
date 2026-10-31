---
id: TASK-1182
sequence_id: 1182
type: task
title: 'CLI tests: override group'
status: Done
parent: FEAT-1173
author: tech-lead
assignee: python-dev
refs:
- TASK-1174:depends-on
subentities:
- local_id: ST1
  title: Override module
  status: Done
  maps_to: US9
created_at: '2026-10-27T21:35:15Z'
updated_at: '2026-10-28T01:02:46Z'
---
<!-- sq:body -->
## Scope

FEAT-1173 US9: the `override` group in `tests/cli/test_override.py`: `scaffold`, `list`, `diff`, `update`, every parameter of each, including the hidden `scaffold --new` with its refusal test. Run on the bundled spec in a copied squad; vocabulary customisation through an override stays out of scope (ADR-1172 "Scope: bundled spec only"), only the command surface is tested.

## Acceptance

- Every `override` pair is declared.
- Refusals for an unknown target and for an override file that does not load, whole error line asserted.

## Ground rules (every CLI surface task)

- Rulebook: ADR-1172. Read it before starting; the rules are cited here, not restated.
- In-process only: Typer `CliRunner` through the `runner`/`invoke` fixtures, on a squad copied per test (`copy_squad` and the builders in `tests/_squads.py`), under the frozen clock. No subprocess (ADR-1172 rule 4).
- One case per (command, parameter) pair where the value takes effect, plus its boundary refusals; combinations only for a genuine interaction, named for the interaction (rule 1). No cross-product or per-type parametrised tables (rules 1-2).
- Assert the exit code and the whole message line or JSON object, never a substring. Read state back through the CLI (`sq <type> <n> show --json` or the command's `--json` form); never open an item file or `.squads.json` (rule 5).
- Declare coverage with `@pytest.mark.covers("<key>", "<param>", ...)`, literal strings, keyed as ADR-1172 rule 3 says; an option is named by its first long flag, so `-m` is declared as `--message`. Hidden parameters are pairs too, each with a refusal test; `--as` is covered on every write command and `--json` on every command that declares it (op-pierre ruling on ADR-1172).
- Mutation-check each test when written: break the parameter's effect, see the test red, restore it. Record in the handback which effect you broke for each test.
- Names state the behaviour; no ticket IDs or process vocabulary in module, function or fixture names (the naming guards in `tests/meta` apply). Docstrings 1-2 sentences, present tense, no versions or history.

## Gate

`uv run --all-extras pyright`, `uv run --all-extras ruff check .` and `uv run --all-extras ruff format --check .` clean; `uv run --all-extras pytest tests/meta tests/cli -n 4` green; `~/.local/bin/sq check` clean for this task. The full suite is run by the main loop.
<!-- sq:body:end -->

## Subtasks

_Add with `sq task 1182 add-subtask "<title>"`; track with `sq task 1182 subtask <n> update --status <Status>`._

<!-- sq:subtasks -->

<!-- sq:subtask:ST1 -->
### ST1 — Override module

<!-- sq:subtask:ST1:body -->
test_override.py: scaffold, list, diff and update with every parameter, the hidden scaffold --new with its refusal, refusals for an unknown target and an override file that does not load.
<!-- sq:subtask:ST1:body:end -->

#### Discussion

<!-- sq:subtask:ST1:discussion -->
<!-- sq:subtask:ST1:discussion:end -->
<!-- sq:subtask:ST1:end -->
<!-- sq:subtasks:end -->

## Discussion

<!-- sq:discussion -->
- [2026-10-27T23:04:03Z] `python-dev` Elias Python:
  - Handback: override group tests committed on branch worktree-agent-aa516a6ac9f618168, commit f1031744 (tests/cli/test_override.py, 39 tests; override removed from PENDING). All 19 override pairs declared. Gates: pyright 0 errors, ruff check and format clean, pytest tests/meta tests/cli -n 3: 1217 passed. Every test mutation-checked, src restored, no src diff. No product bugs found. @manager ready for review.
<!-- sq:discussion:end -->
