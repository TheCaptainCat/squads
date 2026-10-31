---
id: TASK-1178
sequence_id: 1178
type: task
title: 'CLI tests: create'
status: Done
parent: FEAT-1173
author: tech-lead
assignee: python-dev
refs:
- TASK-1174:depends-on
subentities:
- local_id: ST1
  title: Create module
  status: Done
  maps_to: US5
created_at: '2026-10-27T21:35:11Z'
updated_at: '2026-10-28T01:02:42Z'
---
<!-- sq:body -->
## Scope

FEAT-1173 US5: `sq create <type>` in `tests/cli/test_create.py`, tested on `task` (ADR-1172 rule 2): `TITLE`, `--author` (required), `--parent` and the parent rule, `--desc`, `--label`, `--ref` parsed with and without a kind, `--assignee`, `--priority`, `-m`, `--file`, `--json`. `--tag` and `--tech` on `guide`, the only type that carries them. The created item is read back through `show --json`.

## Acceptance

- Every `create` pair is declared; a type-specific option is covered on a type that carries it.
- The exclusion of `-m` with `--file` has its own named test.
- Refusals: missing `--author`, a parent the rule refuses, a malformed `--ref`, an out-of-set `--priority`.

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

_Add with `sq task 1178 add-subtask "<title>"`; track with `sq task 1178 subtask <n> update --status <Status>`._

<!-- sq:subtasks -->

<!-- sq:subtask:ST1 -->
### ST1 — Create module

<!-- sq:subtask:ST1:body -->
test_create.py: every sq create option on task, --tag and --tech on guide, the required author, the parent rule, --ref with and without a kind, and the named -m with --file exclusion test.
<!-- sq:subtask:ST1:body:end -->

#### Discussion

<!-- sq:subtask:ST1:discussion -->
<!-- sq:subtask:ST1:discussion:end -->
<!-- sq:subtask:ST1:end -->
<!-- sq:subtasks:end -->

## Discussion

<!-- sq:discussion -->
- [2026-10-27T22:03:20Z] `python-dev` Elias Python:
  - @manager create CLI tests done: commit 428c9650 on branch worktree-agent-a3bfa1b45570eddfa (worktree /home/pchat/projects/squads/.claude/worktrees/agent-a3bfa1b45570eddfa). tests/cli/test_create.py has 24 tests; PENDING loses only create. Every test was mutation-checked (effect broken in src, red, restored). Gates: pyright 0 errors, ruff check and format clean, pytest tests/meta tests/cli 615 passed, sq check clean. Confirmed: the guide type declares a priority field but sq create guide has no --priority (No such option, exit 2). Also: --ref 2: (empty kind) is accepted as a bare ref.
<!-- sq:discussion:end -->
