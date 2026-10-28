---
id: TASK-1180
sequence_id: 1180
type: task
title: 'CLI tests: squad-wide commands'
status: Done
parent: FEAT-1173
author: tech-lead
assignee: python-dev
refs:
- TASK-1174:depends-on
subentities:
- local_id: ST1
  title: init and adopt
  status: Done
  story: US7
- local_id: ST2
  title: sync, repair, renumber, check
  status: Done
  story: US7
- local_id: ST3
  title: import
  status: Done
  story: US7
- local_id: ST4
  title: migrate group
  status: Done
  story: US7
created_at: '2026-10-27T21:35:13Z'
updated_at: '2026-10-28T01:02:44Z'
---
<!-- sq:body -->
## Scope

FEAT-1173 US7: the squad-wide commands, one module per command or close pair in `tests/cli/`: `init`, `adopt`, `sync`, `repair`, `renumber`, `check`, `import`, and the `migrate` group (`up`, `help`, `chlog`, `rename-status`, `rename-type`, `repad`). Hidden `init --no-seed-skills` is a pair, with its refusal test.

Rules that bite:
- Rule 5: `init` and `sync` read the generated `.claude/` pointers and the managed `CLAUDE.md`/`AGENTS.md` regions directly, the only files a CLI test reads. `repair` asserts the rebuilt index through the CLI (`list --json` / `show --json`), never `.squads.json`.
- Rule 1 interaction: `renumber --onto` with `--by`, its own named test.
- Rule 4: every destructive command runs on a copied squad only; `init`/`adopt` start from an empty or prepared test directory, never a walk-up into a real squad.

## Acceptance

- Every pair of these commands is declared.
- `import` asserts single-transaction behaviour on a refusal: a failing event leaves no earlier event applied, read back through the CLI.
- `migrate up` on a current squad and `chlog` with a malformed range each assert the whole output line.

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

_Add with `sq task 1180 add-subtask "<title>"`; track with `sq task 1180 subtask <n> update --status <Status>`._

<!-- sq:subtasks -->

<!-- sq:subtask:ST1 -->
### ST1 — init and adopt

<!-- sq:subtask:ST1:body -->
Every init and adopt parameter, including the hidden --no-seed-skills with its refusal; assert the generated .claude pointers and managed CLAUDE.md and AGENTS.md regions directly.
<!-- sq:subtask:ST1:body:end -->

#### Discussion

<!-- sq:subtask:ST1:discussion -->
<!-- sq:subtask:ST1:discussion:end -->
<!-- sq:subtask:ST1:end -->

<!-- sq:subtask:ST2 -->
### ST2 — sync, repair, renumber, check

<!-- sq:subtask:ST2:body -->
sync asserts regenerated files; repair asserts a rebuilt index through list --json and show --json; renumber with the named --onto with --by test; check --json on a clean and a dirty copied squad.
<!-- sq:subtask:ST2:body:end -->

#### Discussion

<!-- sq:subtask:ST2:discussion -->
<!-- sq:subtask:ST2:discussion:end -->
<!-- sq:subtask:ST2:end -->

<!-- sq:subtask:ST3 -->
### ST3 — import

<!-- sq:subtask:ST3:body -->
Every import parameter (FILE, --dry-run, --as, --json); a refused event leaves no earlier event applied, read back through the CLI.
<!-- sq:subtask:ST3:body:end -->

#### Discussion

<!-- sq:subtask:ST3:discussion -->
<!-- sq:subtask:ST3:discussion:end -->
<!-- sq:subtask:ST3:end -->

<!-- sq:subtask:ST4 -->
### ST4 — migrate group

<!-- sq:subtask:ST4:body -->
up on a current squad, help, chlog with a valid and a malformed range, rename-status, rename-type and repad with their refusals, all on copied squads.
<!-- sq:subtask:ST4:body:end -->

#### Discussion

<!-- sq:subtask:ST4:discussion -->
<!-- sq:subtask:ST4:discussion:end -->
<!-- sq:subtask:ST4:end -->
<!-- sq:subtasks:end -->

## Discussion

<!-- sq:discussion -->
- [2026-10-27T22:48:47Z] `python-dev` Elias Python:
  - Handback: ST1-ST4 Done; nothing committed; `git diff src/` empty.
    
    Files (tests/cli/): _squadwide.py (helpers: flat, agent_files, region, listed), test_init.py (20), test_adopt.py (8), test_sync.py (3), test_repair.py (5), test_renumber.py (9), test_check.py (5), test_import.py (13), test_migrate.py (20). PENDING in tests/meta/test_every_cli_parameter_is_declared_by_a_covering_test.py: removed adopt, check, import, init, migrate, renumber, repair, sync (the guard passes).
    
    Pairs: every pair of the 8 owners is declared, including hidden init --no-seed-skills (effect test plus a refusal test that takes no value) and the key-only leaves sync, migrate up, migrate help. renumber --onto with --by: test_onto_refuses_by. import single transaction: a refused pre-pass leaves the earlier valid create unapplied, and a body-twice event refused while applying leaves the earlier create undone, both read back with list. migrate up and chlog assert whole lines (current squad, malformed range).
    
    Gates: pyright 0 errors; ruff check and format --check clean on tests and src (a repo-wide `ruff check .` also scans .claude/worktrees, which is the other dev's tree, not mine); `pytest tests/meta tests/cli -n 3`: `905 passed in 27.09s` (28s wall); sq check clean.
    
    Mutation proofs (each broken in src, red, restored):
    - init: squad_dir fixed to "squads"; roles_spec fixed to "minimal"; no_claude=False; _skip_skill_seed=False; force=False; names=None (--name and prompt tests); interactive=_is_tty() (--default-names); interactive=False (prompt tests); `if slug in combined_names` -> False (name spares prompt); _parse_backend_option returning [] / ["claude_code"] / skipping the none-combination check.
    - adopt: squad_dir fixed; roles_spec fixed to core; no_claude=False; backends forced to claude_code.
    - sync: sync() result skipped; the "changed" test dropped from the currency report.
    - repair: svc.repair(renumber=False); `await self._renumber()` removed; same-id renumber disabled; previous_counter=0; missing_ids=[]. The lost-index rebuild test was proven by output only.
    - renumber: from_seq+1; onto/by swapped or dropped; exactly-one check removed; rewrite_ids removed (refs test).
    - check: --json branch disabled; JSON exit 3 removed; human exit 3 removed; only first issue printed.
    - import: stdin branch off; default_as=None; dry_run=False; json branch off; json refusal exit 1 removed; pre-pass gate (`if dry_run` only); swallow SquadsError while applying.
    - migrate: rename_status old/new swapped and old fixed; rename_type swapped; repad width+1; applied=[]; chlog upper/lower bound off-by-one; `if not sep` off; help order reversed.
    
    Product findings (not fixed):
    1. `init --backend bogus` (and `adopt --backend bogus`) validates the backend after writing .squads.toml, squads/.squads.json and .gitignore. The refusal exits 1, but `sq list` then reports "no items" and a valid retry fails with ".squads.toml already exists (use --force)"; for adopt a valid retry fails with "unknown backend 'bogus'". Expected: nothing written on a refusal (`init --roles bogus` does write nothing).
    2. `init --squad-dir /abs/path` and `--squad-dir ''` crash with an unhandled PermissionError / exit 1 and an empty message (traceback in result.exception); .squads.toml and .gitignore are already written. `--squad-dir ../up` writes the squad outside the project. Expected: a clean error.
    3. `migrate up`: the "newer than this squads ... upgrade the squads package" branch is unreachable; the root schema gate refuses first with "Upgrade the squads package." (mutating the in-command check leaves every test green).
    4. `migrate chlog a..b` and a reversed range (`v0.17.0..v0.1.0`) are accepted: "no manual steps for va..vb". Only a range with no `..` is refused.
    5. `migrate rename-status task Nope Draft` (OLD status not in the lifecycle) exits 0 with "0 item(s) renamed". `migrate repad 99` is accepted and renames files to a 99-digit width. Observations, not asserted.
    6. `repair` without --renumber on two files sharing a number silently keeps one in the index (the other item vanishes from `list`) and exits 0 with "rebuilt index: 4 items"; only `sq check` reports it. Tested as such.
    
    Notes: adopt's --backend/--no-claude tests read the generated agent files (same files as init); there is no CLI view of them. migrate up on an older squad copies the existing tests/fixtures/corpus/v0_14 into tmp_path and asserts only version-independent lines. @manager
<!-- sq:discussion:end -->
