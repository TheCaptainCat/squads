---
id: TASK-1175
sequence_id: 1175
type: task
title: 'CLI tests: root options'
status: Done
parent: FEAT-1173
author: tech-lead
assignee: python-dev
refs:
- TASK-1174:depends-on
subentities:
- local_id: ST1
  title: Root options module
  status: Done
  maps_to: US2
created_at: '2026-10-27T21:35:08Z'
updated_at: '2026-10-28T01:02:39Z'
---
<!-- sq:body -->
## Scope

FEAT-1173 US2: the root callback's parameters, key `""`, in `tests/cli/test_root_options.py`, each covered once on one ordinary command (ADR-1172 "Root and shared options"):

- `-C` (repeatable, relative to the previous `-C`), refused on a missing path;
- `--at`, its effect read back through `show --json`, refused on a malformed time;
- `--version`;
- the hidden removed `--dir`, with its refusal (hidden parameters count, each with a refusal test).

`--install-completion` and `--show-completion` are the guard's only exclusions and get no test.

## Acceptance

- Every root-callback parameter is declared under the empty key.
- Each refusal asserts the exit code and the whole error line.

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

_Add with `sq task 1175 add-subtask "<title>"`; track with `sq task 1175 subtask <n> update --status <Status>`._

<!-- sq:subtasks -->

<!-- sq:subtask:ST1 -->
### ST1 — Root options module

<!-- sq:subtask:ST1:body -->
test_root_options.py: -C, --at, --version and the hidden --dir, once each on one ordinary command, each with its refusal.
<!-- sq:subtask:ST1:body:end -->

#### Discussion

<!-- sq:subtask:ST1:discussion -->
<!-- sq:subtask:ST1:discussion:end -->
<!-- sq:subtask:ST1:end -->
<!-- sq:subtasks:end -->

## Discussion

<!-- sq:discussion -->
- [2026-10-27T21:57:23Z] `python-dev` Elias Python:
  - - Handback: ST1 Done, gate green. Commit 6ae5a3fa on branch worktree-agent-af9bdb51a2c8c0730 (worktree /home/pchat/projects/squads/.claude/worktrees/agent-af9bdb51a2c8c0730, rebased onto release/0.17 tip e44859ac, as it started 254 commits behind). No src diff, nothing pushed.
    - Files: tests/cli/test_root_options.py (8 tests: -C x4, --at x2, --version, --dir); the "" entry removed from PENDING.
    - Gate: pytest tests/meta tests/cli -n 3 gives `591 passed in 22.06s`; pyright 0 errors; ruff check and format clean; sq check clean.
    - Mutation proofs (each restored): -C ignored (4 red); -C values not relative (3 red); -C check removed (missing-path refusal red); client_cwd_chosen forced False (no-squad message red); --at parse returns prior clock (stamp and refusal red); --at refusal returns instead of exit 2 (refusal red); --version print removed (red); --dir refusal removed (red).
    - Bugs found: none.
    @manager ready for review.
<!-- sq:discussion:end -->
