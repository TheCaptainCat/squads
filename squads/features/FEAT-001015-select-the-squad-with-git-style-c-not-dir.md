---
id: FEAT-1015
sequence_id: 1015
type: feature
title: Select the squad with git-style -C, not --dir
status: InProgress
author: product-owner
refs:
- ADR-1009:implements
- MILE-934:targets
- BUG-1008:fixes
- TASK-954:depends-on
description: -C runs sq as if started in PATH; --dir is refused naming -C; BUG-1008
  closed
subentities:
- local_id: US1
  title: As an adopter, I want git-style -C to pick where sq runs
  status: InProgress
- local_id: US2
  title: As an adopter, I want -C threaded, never a chdir
  status: InProgress
- local_id: US3
  title: As an adopter, I want init and adopt to honour -C
  status: InProgress
- local_id: US4
  title: As an adopter, I want --dir refused and one resolver left
  status: InProgress
- local_id: US5
  title: As a maintainer, I want -C proven equal to cd
  status: InProgress
- local_id: US6
  title: As an adopter, I want the docs and changelog to say -C
  status: InProgress
created_at: '2026-10-15T20:12:57Z'
updated_at: '2026-10-15T20:20:36Z'
---
<!-- sq:body -->
Implements the accepted decision on selecting the squad with a git-style `-C <path>`. The decision is the spec; the stories cite its numbered sections and add acceptance only. It replaces the global `--dir` and closes the `sq init` defect that ignored it.

## Scope

- The `-C` root option: meaning, repeatability, position, error handling (sections 1 and 2).
- Threading the effective directory through `RequestContext.client_cwd`, never `os.chdir` (section 2).
- `init` and `adopt` creating at the effective directory (section 2).
- Refusing `--dir`, naming `-C` (section 3).
- Removing the backwards inference from `_paths.py` and the TASK-954 refusal that it makes redundant (section 4).
- The gate guarantee and its differential proof (section 5).
- Docs, help text, changelog and the dated notes on three ADRs (sections 6 and 7).

## Out of scope

A long form of `-C`; hoisting `-C` to any position; an alias for `--dir`. All three are rejected in the decision.

## Sequencing

No schema and no bundled-file change, so the version bump does not gate it. It follows the reconcile-path task whose temporary refusal it deletes and precedes the comment-header feature in the main stream. It can run in its own worktree and merge before the bump.
<!-- sq:body:end -->

## User Stories

_Add with `sq feature 1015 add-story "As a <role>, I want … so that …"`; track with `sq feature 1015 story <n> update --status <Status>`._

<!-- sq:stories -->

<!-- sq:story:US1 -->
### US1 — As an adopter, I want git-style -C to pick where sq runs

<!-- sq:story:US1:body -->
Acceptance (decision sections 1 and 2):
- `sq -C <path> <command>` behaves as `cd <path> && sq <command>`, including the walk-up to the first `.squads.toml`.
- `-C` is repeatable: a relative value is taken against the previous one, an absolute value replaces everything before it, an empty value changes nothing. The effective directory is resolved physically. Table-driven tests cover relative, absolute, empty, `..` after a symlink, and chains of three.
- `-C` is accepted only before the command. `sq list -C x` is Click's own "no such option" refusal; `-m -C` as an option value is never read as the flag. There is no long form.
- A `-C` whose effective directory does not exist or is not a directory exits 2 on a message naming the resolved path, before any command or custom-type lookup (`-C /nonexistent widget` reports the `-C` error, not "no such command").
- A directory in no squad gives the not-initialised error, whose message names the effective directory whenever `-C` was given.
- Root help reads `Run as if sq was started in PATH (repeatable; relative to the previous -C).` with metavar `PATH`.
<!-- sq:story:US1:body:end -->

#### Discussion

<!-- sq:story:US1:discussion -->
<!-- sq:story:US1:discussion:end -->
<!-- sq:story:US1:end -->

<!-- sq:story:US2 -->
### US2 — As an adopter, I want -C threaded, never a chdir

<!-- sq:story:US2:body -->
Acceptance (decision section 2):
- One helper computes the effective directory from the root group's parsed `-C` values and the process directory, and it becomes `RequestContext.client_cwd`. No `os.chdir` anywhere; two in-process `CliRunner` invocations with different `-C` values do not leak into each other.
- The two spec lookups that run before the root callback call the same helper on `ctx.params`, never the bound context's `client_cwd`. A test with a custom type declared only in the `-C` squad, run from a directory outside it, resolves the type.
- Relative path arguments follow `-C`: `--file` bodies and comments, and the `sq import` event file. `-` (stdin) is unaffected. A test runs each from a directory other than the `-C` target and finds the file relative to the target.
<!-- sq:story:US2:body:end -->

#### Discussion

<!-- sq:story:US2:discussion -->
<!-- sq:story:US2:discussion:end -->
<!-- sq:story:US2:end -->

<!-- sq:story:US3 -->
### US3 — As an adopter, I want init and adopt to honour -C

<!-- sq:story:US3:body -->
Acceptance (decision section 2; closes the defect where `sq init` ignored the directory option):
- `sq -C X init` creates `X/.squads.toml` and `X/squads/`; `--squad-dir` names the folder inside `X`; the `[init.names]` read uses the same root. The result equals `cd X && sq init` file for file.
- `sq -C X adopt` creates at `X` the same way.
- `X` must exist; `-C` never creates a directory, and a missing `X` exits 2.
- A test reproduces the original report (`sq init` with a relative sub-folder from an empty folder) and finds the project at the sub-folder and nothing in the working directory.
<!-- sq:story:US3:body:end -->

#### Discussion

<!-- sq:story:US3:discussion -->
<!-- sq:story:US3:discussion:end -->
<!-- sq:story:US3:end -->

<!-- sq:story:US4 -->
### US4 — As an adopter, I want --dir refused and one resolver left

<!-- sq:story:US4:body -->
Acceptance (decision sections 3 and 4):
- `--dir`, written anywhere a hoisted global option can be written, exits 2 with `--dir is no longer supported; use -C <path> to run sq as if started in <path> (the project directory, or any folder inside it)`. It writes nothing and never reaches a command.
- `resolve()` is the walk-up from `client_cwd` and nothing else; `client_cwd` defaults to the process directory for non-CLI callers. The `dir_override` parameter, the config-names-folder check, the squad-data refusal, the synthesised default configuration, `RequestContext.active_dir` and `set_active_dir` are gone, and `open_service` loses `dir_override`.
- The temporary refusal for a squad folder outside its project tree is deleted with them. A mistyped `-C` no longer runs on a phantom squad: it is refused.
- A squad kept outside its project tree (`squad_dir = "../shared"`, or an absolute path) is reached with `-C <project>`; a test covers both spellings.
<!-- sq:story:US4:body:end -->

#### Discussion

<!-- sq:story:US4:discussion -->
<!-- sq:story:US4:discussion:end -->
<!-- sq:story:US4:end -->

<!-- sq:story:US5 -->
### US5 — As a maintainer, I want -C proven equal to cd

<!-- sq:story:US5:body -->
Acceptance (decision section 5): the schema gate sees exactly the configuration it would see from the effective directory.
- Differential test over the layout family: project root with `"."` and `"./"`, nested, renamed, two-level, outside the tree with `"../shared"` and an absolute path, a nested project under another squad, and symlinked folders. For each layout and each gate direction (squad behind the package, squad ahead of it), `sq -C <folder> <command>` run from elsewhere equals `cd <folder> && sq <command>` in exit code, stdout, stderr and the digest of every file under the project.
- `-C` at the squad folder, at the project root and at a subfolder of the squad each refuse a behind squad, and `migrate up` migrates it rather than reporting nothing to do.
- A guard in `tests/meta` fails when any squad-resolution call site reads the process working directory; the only read is where the CLI computes the effective directory.
- Falsification: pointing the gate's `resolve` at the process directory turns the differential test red for every `-C` row. The run is recorded in the review.
<!-- sq:story:US5:body:end -->

#### Discussion

<!-- sq:story:US5:discussion -->
<!-- sq:story:US5:discussion:end -->
<!-- sq:story:US5:end -->

<!-- sq:story:US6 -->
### US6 — As an adopter, I want the docs and changelog to say -C

<!-- sq:story:US6:body -->
Acceptance (decisions 6 and 7):
- Every `--dir` mention listed in the decision is updated, with no leftover found by a grep that excludes `--direction`: README, the docs pages, CLAUDE.md outside the managed region, the VS Code client's resolver comment, and the error and store comments. The two faq entries for the old refusals are replaced by entries for the `-C` and `--dir` refusals; `docs/migration.md` gains a 0.16 upgrade note on the break.
- The unreleased CHANGELOG entry for the old gate refusal is replaced by one breaking-change entry for `-C`; released entries are untouched. The tech writer authors the prose.
- Dated notes on three earlier decisions: the lookup that now reads `-C`, the usual selector renamed, and the former global that became a context field. Each carries a related ref back.
- The board notice about scratch squads and the contributor guide paragraph no longer name the old option.
- The existing tests that use the old option are rewritten for `-C`.
<!-- sq:story:US6:body:end -->

#### Discussion

<!-- sq:story:US6:discussion -->
<!-- sq:story:US6:discussion:end -->
<!-- sq:story:US6:end -->
<!-- sq:stories:end -->

## Discussion

<!-- sq:discussion -->
- [2026-10-15T20:13:58Z] Nina Product:
  - 2026-10-15: drafted from the accepted -C decision. Six stories; no tasks yet. Ref kind fixes on BUG-1008 was accepted from a feature. depends-on TASK-954 is already satisfied; it records that the temporary refusal it deletes must land first. @manager: sequencing is right after the reconcile-path task and before FEAT-980, in its own worktree if the stream is busy.
- [2026-10-15T20:19:55Z] Olivia Lead:
  - 2026-10-15: broken down into TASK-1018, one task with six subtasks mapped one-to-one onto US1 to US6. ST1 to ST5 go to one python-dev in a single pass, in order, because they share `_cli/__init__.py`, `_cli/_common.py`, `_paths.py` and the gate table. ST6 (docs, changelog, contributor prose) goes to tech-writer after ST4 fixes the help text and refusal messages. It checks the architect's dated notes on ADR-263, ADR-622 and ADR-534 but does not write them.
  - Refs: fixes BUG-1008, addresses REV-995 (F28 is closed because the heuristic is deleted, not widened), implements ADR-1009. The REV-995 layout rows stay in the gate table and run with -C. Each row expects what cd into the folder does, and ST5's differential test generalises them.
  - Two calls not spelled out in the ADR. (1) The library keeps one process-directory default in `_paths.py`, shared by `resolve()`, `init` and `adopt`, so the many tests that call `service.init()` without a root keep working; the tests/meta guard allowlists that default and the CLI helper and nothing else. (2) A bare trailing `--dir` gets the same refusal as `--dir X`.
  - @manager: TASK-1018 is Draft with no task-level assignee. Promote it to Ready when you dispatch. Board notice 21 still says scratch squads are addressed with --dir; ST6 drafts the new wording and hands it to you.
<!-- sq:discussion:end -->
