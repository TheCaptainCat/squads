---
id: TASK-1018
sequence_id: 1018
type: task
title: Replace --dir with git-style -C and one resolver
status: Done
parent: FEAT-1015
author: tech-lead
assignee: python-dev
refs:
- BUG-1008:fixes
- REV-995:addresses
- ADR-1009:implements
- MILE-934:targets
description: Root -C threaded as client_cwd; --dir refused naming -C; resolve() is
  the walk-up only; init/adopt honour -C
subentities:
- local_id: ST1
  title: Root -C option and the effective-directory helper
  status: Done
  assignee: python-dev
  story: US1
- local_id: ST2
  title: Thread -C into client_cwd, pre-callback lookups and --file
  status: Done
  assignee: python-dev
  story: US2
- local_id: ST3
  title: init and adopt create at the -C directory
  status: Done
  assignee: python-dev
  story: US3
- local_id: ST4
  title: Refuse --dir and delete the backwards inference
  status: Done
  assignee: python-dev
  story: US4
- local_id: ST5
  title: Differential -C vs cd test and the process-cwd guard
  status: Done
  assignee: python-dev
  story: US5
- local_id: ST6
  title: Docs, changelog and contributor prose say -C
  status: Done
  assignee: tech-writer
  story: US6
created_at: '2026-10-15T20:19:04Z'
updated_at: '2026-10-15T21:35:47Z'
---
<!-- sq:body -->
Implements ADR-1009 for FEAT-1015: the root `-C <path>` option replaces `--dir`, the effective directory is threaded as `RequestContext.client_cwd`, `--dir` is refused naming `-C`, and `_paths.resolve()` becomes the walk-up and nothing else. Closes BUG-1008. Gives REV-995 F28 its home (the `_holds_squad_data` heuristic is deleted, not widened).

The decision is the spec. Each subtask body carries the acceptance for one story; the code claims below were read at `86f3f7f6`.

## Build order and ownership

One python-dev, one pass, in this order: ST1, ST2, ST3, ST4, ST5. They all edit `_cli/__init__.py`, `_cli/_common.py`, `_paths.py` and the gate table, so splitting them across developers would collide. ST6 (docs) goes to the tech writer once ST1 to ST4 have fixed the help text and the two refusal messages.

## Files in play

`src/squads/_paths.py`, `src/squads/_context.py`, `src/squads/_cli/__init__.py`, `src/squads/_cli/_common.py`, `src/squads/_cli/_main.py` (init, adopt, line 1572), `src/squads/_cli/_role.py`, `src/squads/_cli/_workflow_cmd.py`, `src/squads/_cli/_import.py`, `src/squads/_services/_service.py`, `src/squads/_errors.py`, `src/squads/_index/_store.py` comment, and the tests that use `--dir`, `dir_override`, `active_dir` or `set_active_dir` (listed in ST4).

## Developer brief

- Comments and docstrings: one or two sentences, saying what the code does and why. No ticket IDs, no release versions, no history ("used to", "now", "no longer").
- Type aliases use PEP 695 `type X = ...`.
- A new module-level dict, list or set must be allowlisted in `tests/meta/test_no_unallowlisted_module_level_mutable_state.py` as a code constant; run `tests/meta` whenever you add a module constant.
- Tests are named by behaviour, never by ticket, and are table-driven over layout x command x direction where the subtask says so. Every new test must go red when its fix is reverted: break the fix, watch it go red, restore, watch it go green, and report both runs per subtask on the task.
- Gates: `uv run --all-extras pyright`, `uv run --all-extras ruff check .`, `uv run --all-extras ruff format --check .`, and the targeted tests. Because this changes `_cli/`, also run `tests/meta`, `tests/integration` and `tests/cli` in full. The main loop runs the full suite.
- Board operations through `~/.local/bin/sq`; probe new behaviour with `uv run sq` only in a scratch squad outside any project tree.
<!-- sq:body:end -->

## Subtasks

_Add with `sq task 1018 add-subtask "<title>"`; track with `sq task 1018 subtask <n> update --status <Status>`._

<!-- sq:subtasks -->

<!-- sq:subtask:ST1 -->
### ST1 — Root -C option and the effective-directory helper

<!-- sq:subtask:ST1:body -->
Add `-C` to the root command and one helper that computes the effective directory (ADR-1009 sections 1 and 2).

## Change

- `src/squads/_cli/__init__.py`, `main_callback`: a repeatable option `-C`, short form only, metavar `PATH`, help `Run as if sq was started in PATH (repeatable; relative to the previous -C).` It is **not** added to `_GLOBAL_VALUE_OPTS` and is never hoisted.
- One helper, in `src/squads/_cli/_common.py`, takes the parsed `-C` values and the process directory and returns the effective directory: the process directory joined with every value in order (an absolute value replaces what came before, an empty value changes nothing), then resolved physically with `Path.resolve()`. This helper is the one place in `src/squads` allowed to read `Path.cwd()` for the CLI (ST5's guard enforces it).
- The option's callback refuses with exit 2 when the effective directory does not exist or is not a directory, naming the resolved path, in the same style as an invalid `--at`. It runs during root parsing, so it fires before any subcommand or custom-type lookup.
- `NotInitializedError` raised from a directory in no squad names the effective directory when `-C` was given. Without `-C` the message text is unchanged.

## Acceptance tests

Unit table over the helper (`tests/unit`), rows:

| values | expected |
|---|---|
| `[]` | the process directory |
| `["a"]` | `cwd/a` |
| `["/abs"]` | `/abs` |
| `["a", "/abs", "b"]` | `/abs/b` (absolute resets) |
| `["a", "", "b"]` | `cwd/a/b` (empty changes nothing) |
| `["a", "b", "c"]` | `cwd/a/b/c` (chain of three) |
| `["link", ".."]` and `["link/.."]` | the parent of the symlink target, not `cwd` |
| `["a/./b/"]` | `cwd/a/b` |

CLI table (`tests/cli`), each run from a directory other than the target:

| argv | expected |
|---|---|
| `-C <squad> list` | the squad's list, same as `cd <squad> && sq list` |
| `-C <subfolder of project> list` | walks up to the project's `.squads.toml` |
| `-C /nonexistent list` | exit 2, message names `/nonexistent`, nothing written |
| `-C <a regular file> list` | exit 2, names the file |
| `-C /nonexistent widget` | exit 2 on the `-C` message, not "No such command" |
| `-C <dir in no squad> list` | exit 1, not-initialised message naming that directory |
| `list -C <squad>` | Click's "No such option" from `list`, exit 2 |
| `task 3 comment --as manager -m -C` | the comment text is `-C`; `-C` is not read as the option |
| `--help` | root help shows `-C PATH` with the exact help text and no long form |

Also a `help_requested` row: `["-C", "--help", "list"]` is not a help request, since `-C` consumes the next token.

Falsify: make an empty value reset to the process directory, and make the helper skip `resolve()`; the matching rows go red.
<!-- sq:subtask:ST1:body:end -->

#### Discussion

<!-- sq:subtask:ST1:discussion -->
- [2026-10-15T20:30:37Z] Elias Python:
  - Driven: tests/unit/test_change_dir_effective_directory.py (15) + tests/cli/test_c_selects_where_sq_runs.py (12) pass. Falsified: empty value reset to the process dir -> 1 red; helper without resolve() -> 4 red; both restored -> 27 green.
<!-- sq:subtask:ST1:discussion:end -->
<!-- sq:subtask:ST1:end -->

<!-- sq:subtask:ST2 -->
### ST2 — Thread -C into client_cwd, pre-callback lookups and --file

<!-- sq:subtask:ST2:body -->
Thread the effective directory into `RequestContext.client_cwd` and every place that reads a relative path (ADR-1009 sections 1 and 2). No `os.chdir` anywhere in `src`.

## Change

- `main_callback` sets `client_cwd` to the ST1 helper's result instead of `Path.cwd()`. The gate (`apply_gate`), `version_notice`, `bind_active_spec`, `get_service`, `_build_bypass_fallback_service`, `_main.py:1572`, `_role.py:94` and `_workflow_cmd.py:1030` already read `client_cwd`, so they follow it.
- The two pre-callback lookups, `resolve_spec_for_ctx` and `_pending_spec_error` in `_cli/_common.py`, call the same helper on the **root** context's parsed `-C` values (`ctx.find_root().params`, since `_CustomCreateGroup` passes the `create` group's context). They must not read `get_context().client_cwd` there: before the callback runs it holds the previous invocation's value.
- Relative path arguments are resolved against `client_cwd`: `_common._read_source_file` (every `--file` for bodies, comments, board, skill, memory, create) and `_import._read_import_text` (the `sq import` event file). `-` keeps reading stdin; an absolute path is unchanged.

## Acceptance tests

- **Custom type through `-C`** (`tests/cli`): a squad whose `.overrides/workflow.toml` declares `widget`; from a directory outside it, `sq -C <squad> widget 1 show`, `sq -C <squad> create widget --help` and `sq -C <squad> --help` (lists `widget`) all resolve the type. Revert the pre-callback lookups to `get_context().client_cwd` and the first row goes red.
- **No leak between in-process invocations**, one `CliRunner`, same process, table of pairs: (`-C A widget 1 show`, then `-C B widget 1 show`) where only B declares `widget` resolves in the second run; where only A declares it, the second run refuses. Also a `-C A list` followed by a bare `list` from B's directory lists B. If the class-level `_custom_cmd_cache` in `_CustomTypeGroup` is what turns a row red, record it on the task and stop, rather than widening this change.
- **Relative files follow `-C`**, table over source x location: `body --file`, `comment --file`, `create --file`, `board post --file`, `import <file>`, each with the file at `<target>/notes.md` named as `notes.md`, run from a directory that has no such file. Rows: the file is found; `--file -` still reads stdin; an absolute path still works. Revert `_read_source_file` and `_read_import_text` to bare `Path(file)` and the relative rows go red.
- `rg 'os\.chdir' src` is empty (ST5's guard enforces it).
<!-- sq:subtask:ST2:body:end -->

#### Discussion

<!-- sq:subtask:ST2:discussion -->
- [2026-10-15T20:33:38Z] Elias Python:
  - Driven: tests/cli/test_c_threads_into_spec_lookups_and_file_arguments.py (27) green. Falsified, each restored to green: resolve_spec_for_ctx reading bound client_cwd -> 2 red; _pending_spec_error reading it -> 1 red; trusting a stale bound context (root-callback marker forced true) -> 1 red; _read_source_file bare Path -> 4 red; import reader bare Path -> 2 red. Note: -C is eager so it is parsed before --help; without that, sq -C X --help did not list X custom types.
<!-- sq:subtask:ST2:discussion:end -->
<!-- sq:subtask:ST2:end -->

<!-- sq:subtask:ST3 -->
### ST3 — init and adopt create at the -C directory

<!-- sq:subtask:ST3:body -->
`sq -C X init` and `sq -C X adopt` create at X (ADR-1009 section 2). Fixes BUG-1008.

## Change

- `src/squads/_cli/_main.py`, `init`: pass `root=get_context().client_cwd` to `svc_init`, and read `[init.names]` from `client_cwd / CONFIG_FILENAME` instead of `Path.cwd()` (line 333). `--squad-dir` stays relative to that root.
- `adopt`: pass the same root to `svc_adopt`.
- `src/squads/_services/_service.py`, `init` and `adopt`: `root` stays optional for non-CLI callers (many test call sites rely on it), but the `Path.cwd()` reads at lines 137 and 212 go. The default comes from one function in `_paths.py` that `resolve()` also uses, so the library has a single process-directory default. The CLI always passes `client_cwd`.
- `-C` never creates a directory: a missing X is ST1's exit 2.

## Acceptance tests (`tests/cli`)

- **Differential, file for file**, table over command x options: `init --default-names --backend none`, `init --default-names --squad-dir team`, `init --default-names` with a pre-placed `X/.squads.toml` carrying `[init.names]` and `--force`, and `adopt` over a folder of squads-native markdown. Each runs `sq -C X <cmd>` from a sibling directory and `cd X && sq <cmd>` on an identical copy; the relative tree listing and the content digest of every file under X are equal, the sibling directory is untouched, and the exit codes match.
- **The BUG-1008 report**: from an empty folder, `mkdir sub && sq -C sub init --default-names` creates `sub/.squads.toml` and `sub/squads/`, and the working directory holds nothing but `sub`.
- `sq -C missing init` exits 2 and creates nothing.
- Revert `init`'s root to the process directory: the differential and the BUG-1008 rows go red. Revert only the `[init.names]` read: the `[init.names]` row goes red.

When this lands, comment on BUG-1008 with the commit and the test names and move it to Fixed; QA verifies.
<!-- sq:subtask:ST3:body:end -->

#### Discussion

<!-- sq:subtask:ST3:discussion -->
- [2026-10-15T20:34:45Z] Elias Python:
  - Driven: tests/cli/test_c_init_and_adopt_create_at_the_directory.py (8) green. Falsified, each restored to green: init root back to the process dir -> 5 red; only the [init.names] read back to the process dir -> 2 red; adopt root back to the process dir -> 1 red.
<!-- sq:subtask:ST3:discussion:end -->
<!-- sq:subtask:ST3:end -->

<!-- sq:subtask:ST4 -->
### ST4 — Refuse --dir and delete the backwards inference

<!-- sq:subtask:ST4:body -->
Refuse `--dir` and leave one resolver: delete the backwards inference and the temporary refusals added for REV-995 F23 and F26 (ADR-1009 sections 3 and 4).

## Change

- `src/squads/_cli/__init__.py`: remove the `dir` option from `main_callback`. Add a hidden `--dir` whose callback exits 2 with exactly: `--dir is no longer supported; use -C <path> to run sq as if started in <path> (the project directory, or any folder inside it)`. Keep `--dir` in `_GLOBAL_VALUE_OPTS` and the `--dir=` prefix in `_hoist_global_options`, and make a bare trailing `--dir` (no value) reach the same refusal. The refusal writes nothing and never reaches a command or the gate.
- `src/squads/_paths.py`: `resolve(*, client_cwd: Path | None = None)` is the walk-up from `client_cwd` and nothing else, `client_cwd` defaulting to the process directory for non-CLI callers through the shared `_paths.py` default (ST3). Delete the `dir_override` parameter, the config-names-folder check and its refusal, `_holds_squad_data` and its refusal, and the synthesised `SquadsConfig(squad_dir=...)`. `find_config` takes its start as a required argument. Rewrite the module docstring to the one rule.
- `src/squads/_context.py`: delete `RequestContext.active_dir`. `src/squads/_cli/_common.py`: delete `set_active_dir`; `bind_active_spec` loses `dir_override`. `src/squads/_services/_service.py`: `open_service` loses `dir_override`. Update every call site (`_common.py`, `_main.py`, `_role.py`, `_workflow_cmd.py`).
- The `src` comments that name `--dir` describe `-C` or the walk-up: `_errors.py:9`, `_index/_store.py:434`, the `_cli/__init__.py` comments at 297 and 377, and the `resolve_spec_for_ctx` docstring.
- Rewrite the tests that use the old option or the removed names for `-C` or `client_cwd`: `tests/unit/test_hoist_global_options.py`, `tests/integration/test_hoist_global_options_end_to_end.py`, `tests/unit/test_index_allocation.py`, `tests/cli/test_cli_plumbing_misc.py`, `tests/cli/test_check_confirms_cross_source_claims_cli.py`, `tests/cli/test_undecodable_squad_files_fail_cleanly.py`, `tests/cli/test_workflow_cross_check_once_per_invocation.py`, `tests/integration/test_check_distinguishes_playbook_and_workflow_config_errors.py`, `tests/integration/test_playbook_guide_dropped_for_a_non_live_role_is_reported.py`, `tests/integration/test_playbook_guide_for_a_project_defined_role.py`, `tests/integration/test_migrate_up_checks_the_corpus_before_the_runners.py`, and the `tests/service` files that bind `active_dir` (`test_context_spec_and_dir_isolation.py`, `test_multi_squad_concurrent_request_isolation.py`, `test_backend_reconciled_per_entry_pointers.py`, `test_dropped_type_skill_orphan_is_withdrawn_and_flagged.py`, `test_init_and_adopt_scaffold_against_a_preexisting_override.py`), plus `tests/CONVENTIONS.md`. Afterwards `rg -e '--dir\b' src tests` matches only the refusal, its hoisting and the tests of the refusal.

## The REV-995 layout rows stay green

`tests/cli/test_the_gate_lets_past_by_command_and_direction.py` keeps every layout in `_LAYOUTS` and `_NOT_THE_SQUAD` and every command x direction, invoked with `-C` instead of `--dir`. What each row expects is what `cd <folder> && sq <command>` does:

| layout, `-C` at | expected |
|---|---|
| nested, root `"."`, `"./"`, multi-level, renamed, symlinked; the squad folder | behind or ahead refused by the gate unless granted, nothing written |
| at-the-project-root, at-a-sibling-folder | resolves the enclosing squad; gated the same way, nothing written |
| outside-relative, outside-absolute; the squad folder | not initialised, exit 1, nothing written |
| outside-relative, outside-absolute; the project root | resolves the squad; gated, nothing written |
| a lone folder in no squad | not initialised, names the folder, never given a squad's stamp |

ST5's differential test generalises these rows; this table stays as the readable instance set.

## Acceptance tests for the refusal (`tests/cli`)

Table over position x form x squad direction (current, behind, ahead): `--dir X list`, `list --dir X`, `task 3 show --dir X`, `--dir=X list`, `list --dir=X`, `init --dir X`, `migrate up --dir X`, `list --dir`. Each exits 2 with the exact message on stderr, and the digest of the working tree is unchanged.

- **A mistyped `-C` is refused**: `-C <a folder with no config above it>` is not initialised and writes nothing, where `--dir` used to synthesise a squad there.
- **A squad outside its project tree is reached with `-C <project>`**, for `squad_dir = "../shared"` and for its absolute path: `list` runs on a current squad and `migrate up` migrates a behind one.
- Falsify: restore the synthesised config branch in `resolve()` and the mistyped-`-C` row goes red; drop the hidden option and the refusal rows go red.
<!-- sq:subtask:ST4:body:end -->

#### Discussion

<!-- sq:subtask:ST4:discussion -->
- [2026-10-15T20:36:57Z] Elias Python:
  - Driven: tests/cli/test_dir_is_refused_naming_c.py (32), the gate table tests/cli/test_the_gate_lets_past_by_command_and_direction.py (rewritten for -C, layout helpers moved to tests/_gate_layouts.py) and the hoist unit rows green. Falsified, each restored to green: synthesised squad restored in resolve() -> 29 red across those two files (323 run); hidden --dir refusal dropped -> 24 red; trailing --dir not hoisted -> 3 red.
<!-- sq:subtask:ST4:discussion:end -->
<!-- sq:subtask:ST4:end -->

<!-- sq:subtask:ST5 -->
### ST5 — Differential -C vs cd test and the process-cwd guard

<!-- sq:subtask:ST5:body -->
Prove that `sq -C <folder> <command>` equals `cd <folder> && sq <command>`, and guard the single read of the process directory (ADR-1009 section 5).

## Differential test (`tests/cli`)

A test named for the property, for example `test_c_runs_exactly_as_cd_into_the_folder_would`, parametrised over:

- **layout**: project root with `squad_dir = "."` and `"./"`; nested `"squads"`; renamed `"team"`; two-level `"work/squad"`; outside the tree with `"../shared"` and with its absolute path; a nested project inside another squad's folder (outer behind and inner current, and the reverse); a symlinked squad folder; a project reached through a symlinked path.
- **target**: the squad folder, the project root, a subfolder of the squad (`<squad>/tasks`).
- **command**: `list`, `repair`, `migrate repad 7`, `migrate up`.
- **direction**: behind, ahead, equal.

Each row builds the layout, snapshots it, runs `sq -C <target> <command>` from an unrelated directory, restores the snapshot, then runs `sq <command>` with the working directory set to the target. Exit code, stdout, stderr and the digest of every file under the scratch root are equal. Run both against the same path (restore between them) so printed paths compare byte for byte. Build each direction's template squad once per module and copy it per row. If the module goes over the fast budget, mark it `slow` and keep a fast canary row set, which `tests/meta/test_slow_marked_modules_always_keep_a_fast_canary.py` requires.

## Gate rows (`tests/cli`)

`-C` at the squad folder, at the project root and at a subfolder of the squad each refuse `list` and `repair` on a behind squad with the behind message, nothing written; and `sq -C <each> migrate up` migrates it (schema stamp advances, exit 0) rather than reporting nothing to do.

## Guard (`tests/meta`)

A guard modelled on `test_wall_clock_time_is_only_read_through_the_clock_module.py`: an AST scan of `src/squads` for `Path.cwd()`, `os.getcwd()`, `os.getcwdb()` and `os.chdir()`. The allowlist is exactly two sites: the ST1 effective-directory helper and the one `_paths.py` default for non-CLI callers, which `resolve()`, `init` and `adopt` share. `os.chdir` has no allowlist entry. Prove the scan works against a known positive: run it against the tree before ST3 (`_main.py:333` and `_service.py:137` read `Path.cwd()`) and it goes red.

## Falsification, recorded on the task for the review

- Point `apply_gate`'s `resolve` at the process directory (`client_cwd=Path.cwd()`): the differential test goes red for every behind and ahead row the gate refuses (equal rows legitimately stay green). Report the red count against that row count.
- Point the root callback's `client_cwd` back at `Path.cwd()`: the differential and the ST1 CLI rows go red.
- Add a stray `Path.cwd()` to `version_notice`: the guard goes red.
Restore each and report the green run.
<!-- sq:subtask:ST5:body:end -->

#### Discussion

<!-- sq:subtask:ST5:discussion -->
- [2026-10-15T20:41:55Z] Elias Python:
  - Driven: tests/cli/test_c_runs_exactly_as_cd_into_the_folder_would.py (477 rows: 13 layouts x 3 targets x 4 commands x 3 directions, plus 9 gate rows) and tests/meta/test_the_process_directory_is_only_read_at_two_sites.py (4) green, 3 stable runs. Falsified, each restored to green: apply_gate resolving at the process dir -> 251 red (245 differential rows where cd is gate-refused + the 6 gate rows); root callback client_cwd back at the process dir -> 481 red across the differential and ST1 files; stray Path.cwd() in version_notice -> guard red. Guard known positive: scanning the pre-change tree (git archive HEAD) reports 6 reads, including _main.py:333 and _service.py:137.
<!-- sq:subtask:ST5:discussion:end -->
<!-- sq:subtask:ST5:end -->

<!-- sq:subtask:ST6 -->
### ST6 — Docs, changelog and contributor prose say -C

<!-- sq:subtask:ST6:body -->
Docs, changelog and contributor prose say `-C` (ADR-1009 sections 6 and 7). Starts once ST1 to ST4 have fixed the help text and both refusal messages; quote them from the code, not from this body.

## Change

- Adopter docs: `README.md:168` and `:287`; `docs/README.md:68`; `docs/faq.md:9` and `:99`; `docs/migration.md:63`; `docs/internals.md:49`, `:62`, `:64`, `:380`, `:396`; `docs/overrides.md:2106`.
- `docs/faq.md`: the two entries for the old refusals (around lines 12 to 19, "is not the squad folder" and "holds squad data") are replaced by one entry for the `-C` refusal (a path that does not exist or is not a directory) and one for the `--dir` refusal.
- `docs/migration.md`: a 0.16 upgrade note on the break: `--dir` is refused, what `-C` means, that `-C <squad folder>` still works for an in-tree squad, and that a squad kept outside its project tree is reached with `-C <project>`.
- `CHANGELOG.md`: the unreleased `--dir` gate entry (line 34) is replaced by one breaking-change entry for `-C`, which also covers `sq init` and `sq adopt` honouring it. Released entries (1141, 1212) stay.
- Contributor prose: `CLAUDE.md:37` and `:102`, outside the managed region; GUIDE-79's CLI paragraph, through `sq guide 79 body`; the `clients/vscode/src/domain/squadDir.ts:131` doc comment (prose only, no code).
- Board notice 21 on scratch squads says "addressed with `--dir`": draft the reworded notice and hand it to @manager, who owns it.

## Check, do not write

The dated notes on ADR-263, ADR-622 and ADR-534 are the architect's. Confirm each exists, says what ADR-1009 section 7 asks (ADR-263: the lookup reads `-C` through the shared helper; ADR-622: the usual selector is `-C`; ADR-534: `active_dir` is removed and `client_cwd` carries the effective directory), and carries a related ref back to ADR-1009. Report any gap to @architect on FEAT-1015 instead of writing it.

## Acceptance

- `rg -n -e '--dir\b' README.md docs CLAUDE.md clients/vscode/src` returns nothing outside released CHANGELOG entries, the migration note and the faq entry that describe the refusal. Validate the pattern on a known positive first, and remember a line-wrapped `--dir` is missed by a line grep: read each touched paragraph.
- `tests/meta/test_documented_commands_resolve_against_cli.py` stays green: every `sq -C ...` example resolves against the live command tree.
- No ticket IDs or repository process in adopter docs.
<!-- sq:subtask:ST6:body:end -->

#### Discussion

<!-- sq:subtask:ST6:discussion -->
<!-- sq:subtask:ST6:discussion:end -->
<!-- sq:subtask:ST6:end -->
<!-- sq:subtasks:end -->

## Discussion

<!-- sq:discussion -->
- [2026-10-15T20:20:39Z] Catherine Manager:
  - Dispatched to @python-dev for ST1-ST5 in the main tree; ST6 goes to @tech-writer after. Operator delegation of 2026-10-11 on MILE-934.
- [2026-10-15T20:44:31Z] Elias Python:
  - @manager ST1 to ST5 are done in the main tree, uncommitted. ST6 (docs) is open for @tech-writer.
    
    **What was driven.** Tests were run, and each subtask's new tests were reverted-then-restored (counts on each subtask). Final run: `tests/meta tests/cli tests/integration tests/unit tests/service` = 9732 passed, 11 skipped, 1 xfailed, 0 FAILED. Not run: the full suite with the slow tests, and `tests/tui`. pyright 0 errors, `ruff check` and `ruff format --check` clean, `sq check` clean. No stray folders in the repo root.
    
    **What was read or inferred, not driven.** The `squads/.overrides` and VS Code client are untouched. The `_custom_cmd_cache` leak below was driven with a scratch probe, not a committed test.
    
    **Finding to decide on (not fixed, per the brief).** `_CustomTypeGroup._custom_cmd_cache` leaks between in-process runs. Probe: squad A declares `widget` with alias `wa`, squad B declares `widget` with alias `wb`. In one process, `-C A wa 2 show` exits 0, then `-C B wb 2 show` exits 2 ("No such command"), because the cached `widget` command was built from A's spec and only A's aliases were registered. It cannot happen in a one-shot `sq`; it matters for tests and a future server handler. The new tests only use rows where it cannot show.
    
    **Judgment calls that differ from the subtask bodies.**
    - `-C` is `is_eager`. Without it Click ran `--help` first, so `sq -C X --help` did not list X's custom types. Consequence: `sq -C /nonexistent --help` is refused (exit 2) instead of printing help.
    - The two pre-callback lookups use a per-invocation marker on the Click context (`mark_root_callback_ran`) to know whether the bound `RequestContext` is this invocation's. Without it the "no leak between in-process invocations" rows go red (the bound spec was the previous run's). Added a `RequestContext.client_cwd_chosen` flag so the not-initialised message can name the directory only when `-C` was given.
    - `NotInitializedError` now takes the searched path and exposes `describe(named=...)`; `_common.error_text` picks the form. Both error printers use it.
    - `_paths.process_dir()` is the shared non-CLI default; `_common.effective_dir` is the CLI read. These are the two guard allowlist entries.
    - The differential test normalises exactly one deliberate difference: with `-C`, the not-initialised error names the directory.
    - Test helpers for layouts moved to `tests/_gate_layouts.py` (shared by the gate table, the refusal tests and the differential).
    - BUG-1008 is commented with the test names and moved to Fixed (via InProgress); commit is still pending, so @qa verifies after it lands.
    
    **Adopter-visible messages and behaviour for ST6.** Quote these from the code.
    1. Root help line (root `--help`, `-C PATH`, no long form): `Run as if sq was started in PATH (repeatable; relative to the previous -C).`
    2. `-C` semantics: `sq -C X <command>` behaves as `cd X && sq <command>`. Repeatable; a relative value is taken against the previous one, an absolute value replaces everything before it, an empty value changes nothing; resolved physically (`link/..` is the target's parent). It must come before the command; `sq list -C x` is Click's own "No such option" (exit 2). `-m -C` as an option value is text, not the flag.
    3. Refusal, bad `-C` (exit 2, nothing written, before any command lookup): `error: -C <resolved path> does not exist` or `error: -C <resolved path> is not a directory`. `-C /nonexistent widget` reports this, not "No such command".
    4. Refusal, `--dir` (exit 2, writes nothing, wherever written, including a trailing `--dir` with no value): `--dir is no longer supported; use -C <path> to run sq as if started in <path> (the project directory, or any folder inside it)`.
    5. Not-initialised: with `-C`: `no .squads.toml found in <effective dir> or any parent directory — run `sq init``. Without `-C` the text is unchanged: `no .squads.toml found in this or any parent directory — run `sq init``. Exit 1.
    6. Behaviour change (breaking): `--dir <squad folder>` is gone. For an in-tree squad `-C <squad folder>` still works. A squad kept outside its project tree (`squad_dir = "../shared"` or an absolute path) is reached with `-C <project>`; `-C <that squad folder>` is not initialised (no `.squads.toml` on the walk-up). A mistyped `-C` no longer runs on an invented squad: a folder with no config above it is refused as not initialised.
    7. `-C` into a subfolder of the project resolves the enclosing squad, like `cd`. So a scratch squad inside a real project tree reaches the real squad (relevant to board notice 21).
    8. `sq -C X init` creates `X/.squads.toml` and `X/squads/` (`--squad-dir` names the folder inside X; the `[init.names]` read uses X's config); `sq -C X adopt` creates at X. `X` must exist; `-C` never creates a directory (missing X exits 2). This closes the old `sq init` ignoring the directory option.
    9. Relative `--file` paths (bodies, comments, board, create, skill, memory) and the `sq import` event file are resolved against the `-C` directory; `-` still reads stdin, absolute paths unchanged.
    10. The schema gate sees the same configuration as `cd X && sq`: `-C` at the squad folder, the project root or a subfolder each refuse a behind squad (`Run sq migrate up to upgrade it`) and `sq -C <each> migrate up` migrates it.
    11. Source comments naming the old option are reworded in `_errors.py` and `_index/_store.py`. Contributor prose still to change in ST6: `CLAUDE.md:37` and `:102`, GUIDE-79, `clients/vscode/src/domain/squadDir.ts:131`, board notice 21.
- [2026-10-15T20:50:07Z] Theo Writer:
  - @manager ST6 done in the main tree, uncommitted: README.md, docs/README.md, docs/faq.md, docs/migration.md, docs/internals.md, docs/overrides.md, CHANGELOG.md, CLAUDE.md (outside the managed region), and the GUIDE-79 CLI paragraph.
    
    - **Driven** in a scratch squad under the session scratchpad with `uv run --project <repo> sq -C …`. The quoted messages come from that run: the root help line, `-C <path> does not exist` and `is not a directory` (exit 2), the `--dir` refusal both leading and trailing (exit 2), the not-initialised message with and without `-C` (exit 1), `-C <outside-tree squad folder>` not initialised while `-C <project>` works, `list -C` giving "No such option", `-C missing init` exit 2 creating nothing, `-C X adopt` creating at X, and a relative `create --file` read from the `-C` directory. The gate claim is taken from the differential tests in ST5, not driven again here.
    - **CHANGELOG 0.16.0**: removed the unreleased `--dir` gate entry under Fixed and added one `BREAKING — -C <path> replaces --dir` entry under Changed. It covers the refusal, how to update a script (for an in-tree squad and an outside-tree one), and init/adopt creating the project at `<path>` (BUG-1008). Released entries are unchanged.
    - **faq**: the two old refusal entries are replaced by one for the `-C` errors and one for the `--dir` refusal. **migration.md**: new section "Upgrading to 0.16: `-C` replaces `--dir`".
    - **Acceptance**: `rg -n -e '--dir\b' README.md docs CLAUDE.md clients/vscode/src` now matches only the faq refusal entry, the migration note, the released CHANGELOG entries and `squadDir.ts:131`. I checked the pattern still matches by running it before the edit (the known positive), and read each touched paragraph for wrapped mentions. `tests/meta/test_documented_commands_resolve_against_cli.py` is green; it caught a deliberately wrong `sq list -C` example, which I reworded as prose. `sq check` is clean.
    - **ADR notes (checked, not written)**: ADR-263, ADR-622 and ADR-534 each have a 2026-10-15 note saying what ADR-1009 section 7 asks, and each refs ADR-1009. No gap to raise with @architect.
    - **For you, not edited (TypeScript)**: `clients/vscode/src/domain/squadDir.ts:129-131` doc comment. Proposed: `Resolve the active squad directory for workspaceRoot, or undefined when no .squads.toml is found (mirrors _paths.py::resolve, the .squads.toml walk-up).` This drops the clause about the `--dir`-override and default-on-init branches, since neither exists any more.
    - **Board notice 21, draft for you to post**: "Run board operations on this repo's squad through the released tool, `~/.local/bin/sq`, never a bare `sq` (which resolves to the dev tree's `.venv/bin/sq`) and never `uv run sq`. The dev tree is mid-edit, so a board write through it runs unreleased code against the live corpus. Use the dev tree only to exercise a feature under development, as `uv run --project <repo> sq -C <scratch project> …`, on a scratch squad outside any project tree (the session scratchpad under /tmp). `-C` walks up like `cd`, so a scratch folder inside this repository resolves to the live squad."
- [2026-10-15T21:14:34Z] Elias Python:
  - @manager REV-1023 F2 to F6 are fixed and marked Fixed, each with its own comment and red-then-green counts. F7: the test docstring is rewritten; the `-C` after `--help`/`--version` behaviour is unchanged. Nothing is committed.
    
    **Driven.** `tests/meta tests/cli tests/integration tests/unit tests/service`: 9755 passed, 11 skipped, 1 xfailed, 0 FAILED. pyright 0 errors, ruff check and format clean, `sq check` clean. New rows: `tests/cli/test_c_refuses_what_cd_refuses.py`, extended `tests/unit/test_hoist_global_options.py` and the rewritten guard `tests/meta/test_the_process_directory_is_only_read_at_two_sites.py`. Not run: `tests/tui` and the slow tests.
    
    **Adopter-visible changes for the writer.**
    1. `-C` now enters each component as `cd` does. A missing, non-directory or non-searchable component is refused (exit 2) at the first bad one, even if a later `..` would undo it. Messages: `error: -C <path> does not exist`, `error: -C <path> is not a directory`, `error: -C <path> cannot be entered: permission denied` (other OS errors use their reason in place of "permission denied"). `<path>` is now the component that failed, joined to the directory reached so far, not the final resolved target.
    2. `--dir` or `--at` is only treated as a global option when it is an option of its own: not as another option's value (`-m --dir` is comment text again) and not after `--`.
    3. `sq -C <folder in no squad> workflow lint` now names the folder, like every other command.
    4. Shell completion no longer prints the `-C` or `--dir` refusals.
    5. `-C` must come first: after `--help` or `--version` it is ignored (unchanged, for ST6).
    
    The `--dir` refusal text, the `-C` help line and the not-initialised wording are unchanged. `_value_options` in `_cli/_common.py` is renamed `value_options` (internal).
- [2026-10-15T21:16:06Z] Theo Writer:
  - @manager The docs now reflect the REV-1023 fixes. Nothing is committed.
    
    - **faq.md**: the `-C` entry now covers all three refusals. `sq` enters the path one component at a time, as `cd` does, and the message names the first component that fails. The `--dir` entry now says the refusal applies to `--dir` written as an option.
    - **CHANGELOG 0.16.0** (the BREAKING `-C` entry): the three component-level messages; `-m --dir` read as plain text; "Shell completion prints neither refusal"; and that `-C` goes before the command and before `--help`/`--version`, and is ignored after them.
    - **README.md**, the `-C PATH` line, and **migration.md**, the upgrade note, each gained the sentence about `-C` going before `--help`/`--version`. The upgrade note also has the component-level refusal and the `-m --dir` text change.
    - **Driven** in the scratch squad with the dev tree:
      - `-C nope/../proj` reports `…/nope does not exist` (exit 2).
      - `-C afile/x` reports `…/afile is not a directory` (exit 2).
      - `-C <chmod 000 dir>` reports `cannot be entered: permission denied` (exit 2).
      - `task 9 comment -m --dir` stores `--dir` as the comment text.
      - `--help -C nope` and `--version -C nope` exit 0 and ignore `-C`.
      - zsh completion with `-C nope` and with `--dir x` lists the commands and prints no refusal.
    - The docs-command meta test and the bundled-docs test are green, and `sq check` is clean.
- [2026-10-15T21:33:05Z] Elias Python:
  - @manager REV-1023 F8 and F9 are fixed and marked Fixed. Nothing is committed. No adopter-visible message or behaviour changed.
    
    **F9.** `value_options()` is now `functools.cache`d: it reads only the static command tree, built from the bundled spec, so it cannot vary by squad or active spec and cannot go stale across in-process runs (custom types are resolved lazily and never appear in it). The hoister also now consults it only when a `--dir`/`--at` token follows another token, so most invocations never build it. Measured with 10 subprocess runs of `.venv/bin/sq` in a scratch squad, median: before `--version` 0.677s and `list` 0.826s; after 0.649s and 0.674s (a second run gave 0.644s and 0.727s). Run-to-run noise is about 50 ms, so read it as roughly the one 47 ms call saved on `--version` and the two on `list`. A tracked-files-stashed baseline gave 0.715s and 0.747s. New row asserts the table is built once; reverting the cache turns it red.
    
    **F8.** The guard now flags a relative string literal under `Path(...).resolve/absolute`, `PosixPath`/`WindowsPath` `.cwd`, `Path.cwd`/`os.getcwd` bound without a call, `from os import environ` with a PWD read, and argument-less `os.listdir`/`os.scandir`. Each new shape is in the injection table (injected into a copy of the real tree, so it goes red where the real tree is clean), and disabling each branch turns 2 to 4 rows red. The docstring states what it cannot see: dynamic `getattr`, relative-path I/O (`open`, `read_text`, `glob`) and a subprocess's inherited cwd.
    
    **Driven.** `tests/meta tests/cli tests/integration tests/unit tests/service`: 9756 passed, 11 skipped, 1 xfailed, 0 FAILED. pyright 0 errors, ruff clean, `sq check` clean. Not run: `tests/tui` and the slow tests.
- [2026-10-15T21:35:47Z] Catherine Manager:
  - Done: REV-1023 approved after two passes (F1 WontFix, home BUG-1021); full suite 9830 passed, 0 failed; pyright, ruff and sq check clean.
<!-- sq:discussion:end -->
