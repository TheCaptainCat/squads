---
id: TASK-1179
sequence_id: 1179
type: task
title: 'CLI tests: roster and notebook groups'
status: Done
parent: FEAT-1173
author: tech-lead
assignee: python-dev
refs:
- TASK-1174:depends-on
subentities:
- local_id: ST1
  title: role group module
  status: Done
  maps_to: US6
- local_id: ST2
  title: dev group module
  status: Done
  maps_to: US6
- local_id: ST3
  title: operator group module
  status: Done
  maps_to: US6
- local_id: ST4
  title: skill group module
  status: Done
  maps_to: US6
- local_id: ST5
  title: memory group module
  status: Done
  maps_to: US6
- local_id: ST6
  title: board group module
  status: Done
  maps_to: US6
created_at: '2026-10-27T21:35:12Z'
updated_at: '2026-10-28T01:02:43Z'
---
<!-- sq:body -->
## Scope

FEAT-1173 US6: the roster and notebook groups, one module each in `tests/cli/`: `role`, `dev`, `operator`, `skill`, `memory`, `board`. Every leaf and parameter of each group, including the addressed verbs (`role <slug> update`, `skill <slug> ref add`, `operator <slug> status`, ...), role activate/catalog/set-default/regen, skill link-role/unlink-role, memory add/show/search/forget, board post/list/clear. The roster groups are not folded (ADR-1172 rule 3), so each group's pairs are covered on that group. Their comment groups belong to the comment verbs task.

Rules that bite:
- Rule 5: where a command writes generated agent-facing files (`.claude/` pointers, managed `CLAUDE.md`/`AGENTS.md` regions), read them directly; everything else through the group's `show --json` / `list --json`.
- `test_roster_body_verbs_share_one_registration` keeps holding the shared body verbs; still declare `body` pairs on each group, as the coverage guard requires.

## Acceptance

- Every (command, parameter) pair of the six groups is declared.
- Refusals cover an unknown slug, a duplicate add and a missing required value on each group where they apply.

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

_Add with `sq task 1179 add-subtask "<title>"`; track with `sq task 1179 subtask <n> update --status <Status>`._

<!-- sq:subtasks -->

<!-- sq:subtask:ST1 -->
### ST1 — role group module

<!-- sq:subtask:ST1:body -->
test_role.py: every leaf and parameter of the role group, read back through its --json forms (generated agent-facing files read directly where the command writes them), with refusals for an unknown slug, a duplicate add and a missing required value where they apply.
<!-- sq:subtask:ST1:body:end -->

#### Discussion

<!-- sq:subtask:ST1:discussion -->
<!-- sq:subtask:ST1:discussion:end -->
<!-- sq:subtask:ST1:end -->

<!-- sq:subtask:ST2 -->
### ST2 — dev group module

<!-- sq:subtask:ST2:body -->
test_dev.py: every leaf and parameter of the dev group, read back through its --json forms (generated agent-facing files read directly where the command writes them), with refusals for an unknown slug, a duplicate add and a missing required value where they apply.
<!-- sq:subtask:ST2:body:end -->

#### Discussion

<!-- sq:subtask:ST2:discussion -->
<!-- sq:subtask:ST2:discussion:end -->
<!-- sq:subtask:ST2:end -->

<!-- sq:subtask:ST3 -->
### ST3 — operator group module

<!-- sq:subtask:ST3:body -->
test_operator.py: every leaf and parameter of the operator group, read back through its --json forms (generated agent-facing files read directly where the command writes them), with refusals for an unknown slug, a duplicate add and a missing required value where they apply.
<!-- sq:subtask:ST3:body:end -->

#### Discussion

<!-- sq:subtask:ST3:discussion -->
<!-- sq:subtask:ST3:discussion:end -->
<!-- sq:subtask:ST3:end -->

<!-- sq:subtask:ST4 -->
### ST4 — skill group module

<!-- sq:subtask:ST4:body -->
test_skill.py: every leaf and parameter of the skill group, read back through its --json forms (generated agent-facing files read directly where the command writes them), with refusals for an unknown slug, a duplicate add and a missing required value where they apply.
<!-- sq:subtask:ST4:body:end -->

#### Discussion

<!-- sq:subtask:ST4:discussion -->
<!-- sq:subtask:ST4:discussion:end -->
<!-- sq:subtask:ST4:end -->

<!-- sq:subtask:ST5 -->
### ST5 — memory group module

<!-- sq:subtask:ST5:body -->
test_memory.py: every leaf and parameter of the memory group, read back through its --json forms (generated agent-facing files read directly where the command writes them), with refusals for an unknown slug, a duplicate add and a missing required value where they apply.
<!-- sq:subtask:ST5:body:end -->

#### Discussion

<!-- sq:subtask:ST5:discussion -->
<!-- sq:subtask:ST5:discussion:end -->
<!-- sq:subtask:ST5:end -->

<!-- sq:subtask:ST6 -->
### ST6 — board group module

<!-- sq:subtask:ST6:body -->
test_board.py: every leaf and parameter of the board group, read back through its --json forms (generated agent-facing files read directly where the command writes them), with refusals for an unknown slug, a duplicate add and a missing required value where they apply.
<!-- sq:subtask:ST6:body:end -->

#### Discussion

<!-- sq:subtask:ST6:discussion -->
<!-- sq:subtask:ST6:discussion:end -->
<!-- sq:subtask:ST6:end -->
<!-- sq:subtasks:end -->

## Discussion

<!-- sq:discussion -->
- [2026-10-27T22:51:12Z] `python-dev` Elias Python:
  - Handback: commit 451cd47c on branch worktree-agent-a894e6fe2ce166fb2 (worktree /home/pchat/projects/squads/.claude/worktrees/agent-a894e6fe2ce166fb2).
    
    - Files: tests/cli/test_role.py, test_dev.py, test_operator.py, test_skill.py, test_memory.py, test_board.py, tests/cli/_roster.py (shared read-backs), and the six keys removed from PENDING.
    - Gates: pytest tests/meta tests/cli: 888 passed; pyright 0 errors; ruff check and format clean; sq check clean. No src diff.
    - 273 tests; each was red under at least one source mutation aimed at its parameter (refusals: the raise neutralised; effects: the argument dropped or altered; --as: apply_edit_actor removed).
    
    Findings (not fixed):
    - Roster `status --force` has no observable effect: the lifecycle is Active/Archived and same-state moves pass. Tested as not lifting an invalid status.
    - `role <slug> view add|disable --as` only reaches a refusal under the bundled spec (the declared view blocks every edit), so the --as effect is tested through the unknown-slug refusal.
    - `skill <slug> ref rm <n>` for a ref the skill does not carry prints "removed" and succeeds.
    - `sq role activate --slug x` prints "No such option: --slug ('(Possible options: --as)',)" (tuple repr leaks into the message).
    
    @manager
<!-- sq:discussion:end -->
