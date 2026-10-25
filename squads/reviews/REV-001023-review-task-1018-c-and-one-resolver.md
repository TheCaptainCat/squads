---
id: REV-1023
sequence_id: 1023
type: review
title: 'Review TASK-1018: -C and one resolver'
status: Approved
author: reviewer
assignee: reviewer
refs:
- TASK-1018:addresses
- FEAT-1015:addresses
- MILE-934:targets
- BUG-1021
description: Shape attack on the -C option, the --dir refusal, the gate through -C,
  init/adopt and the cwd guard
subentities:
- local_id: F1
  title: Custom-type command cache leaks between in-process runs (driven)
  status: WontFix
  severity: low
- local_id: F2
  title: Bare --dir hoist captures an option value or a token after -- (driven)
  status: Verified
  severity: low
- local_id: F3
  title: workflow lint omits the -C directory from not-initialised (driven)
  status: Verified
  severity: low
- local_id: F4
  title: cwd guard misses imported, implicit and environment reads (driven)
  status: Verified
  severity: low
- local_id: F5
  title: Shell completion prints the -C and --dir refusals to stderr (driven)
  status: Verified
  severity: low
- local_id: F6
  title: '-C resolves paths that cd refuses: missing hop, no search bit (driven)'
  status: Verified
  severity: low
- local_id: F7
  title: -C after --help or --version is ignored (driven)
  status: Verified
  severity: info
- local_id: F8
  title: cwd guard still misses relative literals, aliases and implicit reads (driven)
  status: Verified
  severity: low
- local_id: F9
  title: value_options rebuilds the command tree twice per run (driven)
  status: Verified
  severity: info
created_at: '2026-10-15T21:03:20Z'
updated_at: '2026-10-25T19:28:34Z'
---
<!-- sq:body -->
Review of TASK-1018 ST1 to ST5 (FEAT-1015, ADR-1009): the root `-C` option, the `--dir` refusal, `resolve()` as the walk-up only, `init`/`adopt` at the `-C` directory, the differential test and the process-directory guard. Reviewed as the uncommitted diff in the main tree over `953a07ae`, with the new test files. Every probe ran with the dev tree in scratch squads outside any project, addressed with `-C`.

Claims are marked **driven** (run and observed), **read** (source read) or **inferred**.

## What holds

- **The gate through `-C` (driven).** My own differential, separate from the dev's test: every REV-995 layout (nested, `"."`, `"./"`, two-level, renamed, symlinked, at the project root, at a sibling folder, `"../shared"`, absolute) x target (squad folder, `<squad>/tasks`, project root) x `list`, `repair`, `migrate repad 7`, `migrate up` x behind/ahead/equal, run one-shot through the real entry point. That is 336 rows, with `sq -C <t>` from elsewhere compared against `cd <t> && sq` on exit code, first output line and whether any file changed. Result: 0 differ and 0 gate bypasses. Spot rows confirm the comparison has teeth: a behind `"."` squad's `repair` is refused, writes nothing; `-C <outside squad folder>` is not initialised; `-C <project> migrate up` migrates.
- **One resolver (read).** `_holds_squad_data`, the synthesised config, `dir_override`, `active_dir` and `set_active_dir` are gone from `src` and `tests`. Every `resolve()` call passes `client_cwd`. The only process-directory reads are `effective_dir` and `process_dir`. There is no `os.chdir`, no `subprocess`, and no `Path(".")`, `abspath` or `.absolute()` in `src`. The one unanchored `Path(file)` is the fallback in `client_path`, used only when no context is bound.
- **`-C` parsing (driven).** Chains (`-C .. -C A`, absolute reset, `-C /nonexistent -C /abs`), `-Cpath`, `-C ''`, a unicode path, and a path containing markup brackets (escaped in both messages) all behave as ADR-1009 section 1 states. `list -C x` gives Click's "No such option". `-m -C` stores `-C` as the comment text. A regular file, a symlink loop and a missing path each exit 2 naming the resolved path.
- **Relative files follow `-C` (driven).** `body --file notes.md` and a chained `-C A/squads -C tasks comment --file ../../notes.md` read the target's file, not the process directory's.
- **`init`/`adopt` against BUG-1008 (driven).** `sq -C sub init --default-names` writes only under `sub`. It is identical to `cd sub && sq init` apart from timestamps (22 files differ only in `created_at`/`updated_at`). Re-init refuses, `--squad-dir team` lands at `sub/team`, `-C ad adopt` imports and lists, and `-C missing init` exits 2 with the working directory left empty.
- **`--dir` refusal (driven).** Every form exits 2 with the exact message and writes nothing in an empty directory: before and after the command, `=`, bare, trailing, `--dir=`, inside `init`/`migrate up`/`migrate --dir X up`, after `-C`, and with `list ... --help`. It is hidden from root help.
- **Stale context between in-process runs (driven + falsified).** In one process, `-C W wid 2 show` followed by bare `--help` and `list` from A's directory shows A, not W. Forcing `_root_callback_ran` to `True` in a scratch copy turns `test_a_broken_override_in_the_c_squad_is_reported_not_called_an_unknown_command` red, which reproduces the dev's count. `ctx.meta` is shared down the Click context chain, so the marker set on the root is seen by `create`'s group (read).
- ruff check and format are clean (driven). I did not run pyright or the full suite, as the brief asked.

## Findings

Seven findings, none blocking: five low, two info. They are filed as sub-entities below.

**Recommended verdict:** approve. The gate guarantee of ADR-1009 section 5 holds on every layout I drove. Each finding is either a narrow message or edge-case gap, or a pre-existing, in-process-only leak.
<!-- sq:body:end -->

## Findings

_Severity:_ 🔴 critical · 🟠 high · 🟡 medium · 🟢 low · 🔵 info

_Add with `sq review 1023 add-finding "…" --severity medium`; track with `sq review 1023 finding <n> update --status <Status>`._

<!-- sq:findings -->

<!-- sq:finding:F1 -->
### F1 — Custom-type command cache leaks between in-process runs (driven)

<!-- sq:finding:F1:body -->
**What (driven).** `_CustomTypeGroup._custom_cmd_cache` (`_cli/__init__.py`) and `_CustomCreateGroup._custom_cmd_cache` (`_cli/_create.py`) are `ClassVar` dicts keyed by type name and alias. A custom-type command built from one squad's spec is reused for every later invocation in the same process.

In one process (`CliRunner`), with squads W2 (`widget`, alias `wb`) and W (`widget`, alias `wid`):

- `-C W2 wb 2 show` exits 0.
- `-C W wid 2 show` then exits 2 with "No such command": `widget` is already cached and only W2's aliases were registered.
- `-C W widget 2 show` exits 0, but it runs the command object built from W2's spec.

**Scope (read + inferred).** The cache predates this change: it came with lazy custom-type dispatch and leaked the same way across `--dir` runs. A one-shot `sq` cannot reach it. Nothing in `src` re-invokes the app in process (no `CliRunner`, `standalone_mode` or `app(` call outside `_cli/__init__.py`), and within one invocation the pre-callback and post-callback lookups resolve the same squad. A one-shot run of `-C W wid 2 show` exits 0. So this is out of scope for TASK-1018. It does matter for two callers: the suite, where the new tests avoid the shape, and the in-process server handler that ADR-1009 and `resolve()`'s docstring name as a future `client_cwd` caller.

**What would fix it.** Key the cache by the spec it was built from (or by the resolved squad folder), or drop it and rebuild per invocation. Its stated purpose is stable objects within one invocation, which `ctx.meta` would also give. Give it a home before any server handler lands.
<!-- sq:finding:F1:body:end -->

#### Discussion

<!-- sq:finding:F1:discussion -->
- [2026-10-15T21:05:41Z] `reviewer` Paul Reviewer:
  - QA filed this leak as BUG-1021 at the same time. That bug is the home for the fix. My extra evidence: _CustomCreateGroup has the same ClassVar cache, and the leak predates -C (it leaked the same way across --dir runs).
- [2026-10-15T21:06:18Z] `manager` Catherine Manager:
  - Home: BUG-1021 (pre-existing; unreachable from one-shot sq). Must be fixed before any in-process server handler.
<!-- sq:finding:F1:discussion:end -->
<!-- sq:finding:F1:end -->

<!-- sq:finding:F2 -->
### F2 — Bare --dir hoist captures an option value or a token after -- (driven)

<!-- sq:finding:F2:body -->
**What (driven).** `_hoist_global_options` now rewrites a bare `--dir` with no following token to `--dir=` and hoists it. The trailing-`--dir` refusal works, but the token is captured wherever it sits, including as an option's value or after `--`:

- `sq -C A task 9 comment --as manager -m --dir` exits 2 with the `--dir` refusal. Before this change a terminal `--dir` was left alone (read, from the diff), so the comment text was `--dir`.
- `sq -C A task 9 comment --as manager -- --dir` is refused too. The hoister ignores the `--` end-of-options marker.
- `-C` is not hoisted, but its value is still scanned. A directory named `--dir` or `--at` is captured as the global option: `sq -C --at list` turns into `--at list -C` (inferred from the code).

The `-m --dir X` capture (with a following token) is older. REV-995 F21 found the same token shape for `--help`.

**Severity.** Low. The capture fails loudly and writes nothing, and the inputs are contrived. Still, `-m --dir` was accepted before this change and is refused after it.

**What would fix it.** Stop hoisting at `--`. Hoist a bare trailing `--dir` only when it is not the value of the option before it. Simpler still: since `--dir` is only refused now, scan for it without moving it, refusing it at any position except after `--` or as an option's value.
<!-- sq:finding:F2:body:end -->

#### Discussion

<!-- sq:finding:F2:discussion -->
- [2026-10-15T21:14:29Z] `python-dev` Elias Python:
  - Fixed: the hoister leaves a token that is the value of the option before it, or follows --, where it is. Rows in tests/unit/test_hoist_global_options.py; reverting either check turns 5 and 4 red.
- [2026-10-15T21:18:10Z] `reviewer` Paul Reviewer:
  - Verified, driven: -m --dir, --message --dir and -m --dir -m tail are stored as comment text, and so is -m --dir on a custom type (wid). -- --dir now reaches the command as an extra argument and is not hoisted. A real --dir (list --dir, list --dir=x, show --json --dir x, refs --out --dir x, -m x --dir A) is still refused. -C --dir is read as a folder named --dir. One residual: in -m -m --dir, the second -m is the value, so --dir is a real option, but the hoister skips it and Click prints No such option: --dir. That is exit 2 with nothing written, just not the refusal text. Info only, no action needed.
<!-- sq:finding:F2:discussion:end -->
<!-- sq:finding:F2:end -->

<!-- sq:finding:F3 -->
### F3 — workflow lint omits the -C directory from not-initialised (driven)

<!-- sq:finding:F3:body -->
**What (driven).** ST1 acceptance says the not-initialised error names the effective directory whenever `-C` was given. `sq -C <lone folder> workflow lint` prints the unnamed form, `no .squads.toml found in this or any parent directory`. `check`, `check --json`, `list --json`, `migrate up`, `role list`, `board list`, `sync` and `ui` all print the named form.

**Why (read).** `_cli/_workflow_cmd.py:1031-1032` catches `SquadsError` and prints `e(str(exc))` itself, bypassing `common.error_text`. It is the only `SquadsError` printer in `_cli` that does this.

**What would fix it.** Print `common.error_text(exc)` there, and add the row to the ST1 CLI table.
<!-- sq:finding:F3:body:end -->

#### Discussion

<!-- sq:finding:F3:discussion -->
- [2026-10-15T21:14:30Z] `python-dev` Elias Python:
  - Fixed: workflow lint prints common.error_text. Row in tests/cli/test_c_refuses_what_cd_refuses.py; reverted -> 1 red.
- [2026-10-15T21:18:12Z] `reviewer` Paul Reviewer:
  - Verified, driven: sq -C <lone folder> workflow lint now names the folder (_workflow_cmd.py uses common.error_text).
<!-- sq:finding:F3:discussion:end -->
<!-- sq:finding:F3:end -->

<!-- sq:finding:F4 -->
### F4 — cwd guard misses imported, implicit and environment reads (driven)

<!-- sq:finding:F4:body -->
**What (driven).** `tests/meta/test_the_process_directory_is_only_read_at_two_sites.py` matches only the `<owner>.<attr>()` call shape, with owner `Path` or `os`. I ran its `_scan` on a scratch copy of `src/squads` with five extra functions appended to `_aio.py`:

1. `from os import getcwd as _g; _g()`
2. `Path(".").resolve()`
3. `os.path.abspath("x")`
4. `os.environ.get("PWD")`
5. `Path.cwd()`

It reported one hit, the last. The first four each read the process directory and pass. `from os import chdir; chdir(x)` would evade the `os.chdir` ban the same way.

**Severity.** Low. No such read exists in `src` today (read: grep for `abspath`, `realpath`, `absolute()`, `Path()`, `Path(".")`, `from os import` and `subprocess` finds none on a resolution path). But the guard is the only thing that keeps it that way, and its docstring promises the process directory is read at exactly two places.

**What would fix it.** Resolve imported names: flag a bare-name call whose name was imported from `os` as `getcwd`, `getcwdb` or `chdir`, and a `Path.cwd` reached through an alias. Add `os.path.abspath` and `os.path.realpath`, and `Path(...).resolve()`/`.absolute()` on a relative literal. Put the shapes in a known-positive table like the existing pre-change scan.
<!-- sq:finding:F4:body:end -->

#### Discussion

<!-- sq:finding:F4:discussion -->
- [2026-10-15T21:14:31Z] `python-dev` Elias Python:
  - Fixed: the guard resolves os/Path imports and aliases and flags os.path.abspath/realpath, Path()/Path("")/Path(".") resolved or absolute, and PWD reads. 23 shapes each proven red when injected into a copy of the real tree; disabling the import, os.path, Path-literal or PWD branch turns 2 red each.
- [2026-10-15T21:18:14Z] `reviewer` Paul Reviewer:
  - Verified for every shape this finding reported, driven: an imported or aliased getcwd, Path(".").resolve(), os.path.abspath, os.environ PWD and from os import chdir are all in the _SHAPES table and caught. A further attack found more shapes the scan misses. Those are filed as their own finding (F8), so this one closes.
<!-- sq:finding:F4:discussion:end -->
<!-- sq:finding:F4:end -->

<!-- sq:finding:F5 -->
### F5 — Shell completion prints the -C and --dir refusals to stderr (driven)

<!-- sq:finding:F5:body -->
**What (driven).** Shell completion parses the root options, so the `-C` and `--dir` option callbacks run and print their refusal to stderr. Completion then carries on:

- `_SQ_COMPLETE=complete_bash COMP_WORDS="sq -C /bad li" COMP_CWORD=3 sq` prints `error: -C /bad does not exist` on stderr and `list` on stdout, exit 0.

The completion script captures stdout only, so the error line lands in the middle of the user's prompt on TAB. Completion through a good `-C` works: `sq -C ../W wi<TAB>` offers `widget`, the squad's custom type.

**Why (read).** `check_change_dir` and `refuse_dir_option` print before raising `typer.Exit(2)`. Under `ctx.resilient_parsing` Click swallows the exception but not the print. An invalid `--at` follows the same pattern.

**What would fix it.** Return early from both callbacks when `ctx.resilient_parsing` is set, or raise a `click.BadParameter`/`UsageError` carrying the message, which completion suppresses, instead of printing first.
<!-- sq:finding:F5:body:end -->

#### Discussion

<!-- sq:finding:F5:discussion -->
- [2026-10-15T21:14:32Z] `python-dev` Elias Python:
  - Fixed: both callbacks return silently under ctx.resilient_parsing. Subprocess completion rows assert empty stderr; reverting the -C guard -> 2 red, the --dir guard -> 1 red.
- [2026-10-15T21:18:16Z] `reviewer` Paul Reviewer:
  - Verified, driven: completion with -C /bad or --dir x prints only the candidates (list), and nothing on stderr. Completion through a good -C still offers the squad custom type (widget). Both callbacks return early under ctx.resilient_parsing.
<!-- sq:finding:F5:discussion:end -->
<!-- sq:finding:F5:end -->

<!-- sq:finding:F6 -->
### F6 — -C resolves paths that cd refuses: missing hop, no search bit (driven)

<!-- sq:finding:F6:body -->
**What (driven).** `effective_dir` joins every value and then calls `Path.resolve()`, which is non-strict. `check_change_dir` checks only the final directory with `is_dir()`. Some inputs that `cd` or `git -C` reject therefore resolve:

- `-C nonexist -C .. -C ../A list` and `-C afile -C .. -C ../A list` list A. `cd nonexist` fails, and git stops at the first `-C` it cannot enter.
- A directory with no search permission (`chmod 644`) inside squad A: `-C A/noexec list` lists A. `find_config`'s `is_file()` on `noexec/.squads.toml` swallows the `PermissionError` and the walk moves to the parent. `cd A/noexec` is "permission denied".
- `-C noperm/inner`, where `noperm` is mode 000, reports `does not exist`, although the real failure is permission.

ADR-1009 section 1 says resolved physically "as `chdir` does", and section 5 states the property as `sq -C X` equals `cd X && sq`. These shapes are outside it. None of them bypasses the gate: a missing hop or a non-searchable folder can only reach a squad that its parent folder would reach anyway (inferred).

**What would fix it.** Either check each hop and require search permission (`os.access(path, os.X_OK)`) on the target, wording the refusal from the actual `OSError`. Or record these as accepted deviations in ADR-1009, with the join-then-resolve semantics stated as the contract.
<!-- sq:finding:F6:body:end -->

#### Discussion

<!-- sq:finding:F6:discussion -->
- [2026-10-15T21:14:33Z] `python-dev` Elias Python:
  - Fixed: -C enters each component as chdir does (missing, non-directory, no search bit refused at the first bad component, even if a later .. undoes it) with its own message. Rows in test_c_refuses_what_cd_refuses.py; join-then-resolve restored -> 7 red, search check dropped -> 2 red.
- [2026-10-15T21:18:18Z] `reviewer` Paul Reviewer:
  - Verified, driven. effective_dir now enters each component in turn. A missing, non-directory or non-searchable hop is refused at the first bad component, even if a later .. would undo it: nonexist/.., afile/.., afile/, noperm/inner, noperm/.., A/noexec, A/noexec/.., a symlink to a file and a symlink loop (ELOOP reason) all exit 2 naming the failing component. Trailing and doubled slashes and ./ are accepted. Semantics are PHYSICAL: sl/toA/.. gives the parent of the link target and sl/lnk/.. gives sl/real, which matches cd -P, chdir(2) and git -C. The shell default cd -L would give sl. This agrees with ADR-1009 section 1 (links resolved before .., as chdir does). The dev differential runs cd as a process chdir, which is physical too.
<!-- sq:finding:F6:discussion:end -->
<!-- sq:finding:F6:end -->

<!-- sq:finding:F7 -->
### F7 — -C after --help or --version is ignored (driven)

<!-- sq:finding:F7:body -->
**What (driven).** Click processes eager options in the order they are written. `-C` is eager, so it is honoured before `--help` and `--version` but not after them:

- `sq --help -C W` lists no `widget`. The root help is built from the process directory's squad. `sq -C W --help` lists it.
- `sq --help -C /bad` and `sq --version -C /bad` exit 0, while `sq -C /bad --help` and `sq -C /bad --version` exit 2.
- `sq --dir X --help` and `sq --dir X --version` print help or the version and exit 0, without the `--dir` refusal. That is harmless because nothing runs, but it differs from every other `--dir` form.

Also, the `tests/cli/test_dir_is_refused_naming_c.py` module docstring says a mistyped `-C` is refused "instead of running on an invented squad". `-C` never did that; the old `--dir` did. Read as a stranger, it narrates the change rather than describing `-C`. It is a test docstring, so this is info only.

**Severity.** Info. git has the same order dependence, and ADR-1009 puts `-C` before the command. Worth one sentence in the ST6 docs: `-C` goes first.
<!-- sq:finding:F7:body:end -->

#### Discussion

<!-- sq:finding:F7:discussion -->
- [2026-10-15T21:18:36Z] `reviewer` Paul Reviewer:
  - Verified, read: the test_dir_is_refused_naming_c.py module docstring now describes -C and no longer narrates the change. The order dependence (-C ignored after --help or --version) stays by design, as in git. It is documented through ST6 (the dev handed it to the writer as item 5).
<!-- sq:finding:F7:discussion:end -->
<!-- sq:finding:F7:end -->

<!-- sq:finding:F8 -->
### F8 — cwd guard still misses relative literals, aliases and implicit reads (driven)

<!-- sq:finding:F8:body -->
**What (driven).** I ran the rewritten guard's `_hits_in` over 18 more single-function sources. It missed 15 of them:

- `Path("squads").resolve()` and `Path("x").absolute()`: only the literals `""` and `"."` are matched.
- `Path(".").expanduser().resolve()` and `(Path() / x).resolve()`: the receiver is not the bare literal.
- `PosixPath.cwd()`, `g = Path.cwd; g()` and `getattr(os, "getcwd")()`.
- `from os import environ; environ["PWD"]`.
- `os.listdir()` and `os.scandir()` with no argument, and one-argument `os.path.relpath(x)`. Each reads the process directory implicitly.
- `open("notes.md")`, `Path("notes.md").read_text()`, `glob.glob("*.md")`, and `subprocess.run` without `cwd`.

Caught: `import os.path` followed by `os.path.abspath`, and `P().resolve()` through an aliased `Path`.

**Severity.** Low. None of these shapes exists in `src` today (read). The relative-path I/O class (`open`, `read_text`, `glob`) cannot be closed by an AST scan. The risk is that the guard's docstring now says it "matches the shapes", which reads as complete.

**What would fix it.** Add the cheap ones to the scan and to `_SHAPES`: any relative string literal under `resolve`/`absolute`, `PosixPath`/`WindowsPath`, an attribute reference to `cwd`/`getcwd` without a call, a bare `environ`, no-argument `listdir`/`scandir`/`walk`, and one-argument `relpath`. Then make the docstring say what the scan cannot see: relative-path I/O and a subprocess's inherited cwd. Those stay a review item.
<!-- sq:finding:F8:body:end -->

#### Discussion

<!-- sq:finding:F8:discussion -->
- [2026-10-15T21:33:02Z] `python-dev` Elias Python:
  - Fixed: the guard now also flags a relative string literal under Path(...).resolve/absolute, PosixPath/WindowsPath .cwd, Path.cwd or os.getcwd bound without a call, from os import environ with PWD, and argument-less os.listdir/scandir. 10 new shapes proven red on injection into a copy of the real tree; disabling each branch turns 2 to 4 rows red. The docstring now names what it cannot see: dynamic getattr, relative-path I/O and an inherited subprocess cwd.
- [2026-10-25T19:28:34Z] `reviewer` Paul Reviewer:
  - Holds: tests/meta/test_the_process_directory_is_only_read_at_two_sites.py covers PosixPath, listdir/scandir, environ and resolve/absolute literals, and names what it cannot see.
<!-- sq:finding:F8:discussion:end -->
<!-- sq:finding:F8:end -->

<!-- sq:finding:F9 -->
### F9 — value_options rebuilds the command tree twice per run (driven)

<!-- sq:finding:F9:body -->
**What (driven).** `common.value_options()` rebuilds the whole Click command tree on every call (`typer.main.get_command(app)` plus a walk). That took 47 ms on each of two consecutive calls in one process: it is not cached. Each invocation calls it from `_hoist_global_options` (any argv with a non-global token) and again from `help_requested` in `apply_gate`, which adds about 90 ms to an `sq` run of about 0.6 s. Before this change only `help_requested` paid it.

**What would fix it.** Memoise it per process, for example with `functools.cache`; the static tree does not change within a process. Or compute it once in `main()` and pass it to both callers. Neither needs a module-level mutable global.
<!-- sq:finding:F9:body:end -->

#### Discussion

<!-- sq:finding:F9:discussion -->
- [2026-10-15T21:33:04Z] `python-dev` Elias Python:
  - Fixed: value_options is cached for the process (the static tree does not vary by squad or spec), and the hoister only consults it when a --dir/--at token follows another token. Startup, median of 10 on a scratch squad, dev tree: before sq --version 0.677s, sq list 0.826s; after 0.649s / 0.674s (second run 0.644s / 0.727s). Reverting the cache turns the new once-per-process row red.
- [2026-10-25T19:28:34Z] `reviewer` Paul Reviewer:
  - Holds: `_cli/_common.py::value_options` is `@functools.cache`d.
<!-- sq:finding:F9:discussion:end -->
<!-- sq:finding:F9:end -->
<!-- sq:findings:end -->

## Discussion

<!-- sq:discussion -->
- [2026-10-15T21:05:26Z] `reviewer` Paul Reviewer:
  - @manager REV-1023 is Approved on your instruction for TASK-1018 ST1-ST5, with 7 findings open and none blocking (6 low, 1 info). Each needs a disposition. My own one-shot differential (336 rows: every REV-995 layout x target x command x direction) showed 0 differences between -C and cd, and 0 gate bypasses (driven).
  - Confirmed driven: the -C parsing shapes, relative --file following -C, init/adopt per BUG-1008 (the same tree as cd apart from timestamps), every --dir refusal form writing nothing, and no stale RequestContext between in-process runs. Forcing the marker true turns the threading test red, as the dev reported. ruff is clean. I did not run pyright or the full suite.
  - F1 is the dev-reported _custom_cmd_cache leak. It is pre-existing (the same leak existed with --dir), in-process only, and out of scope for this task. It needs a home before a server handler lands. F3 (workflow lint prints the unnamed not-initialised message) misses ST1 acceptance and is a one-line fix. F2, F4, F5 and F6 are edge cases. F7 (put -C first) is worth a sentence in ST6 for @tech-writer.
- [2026-10-15T21:25:32Z] `reviewer` Paul Reviewer:
  - @manager Pass 2 of REV-1023 is done and the review stays Approved; nothing blocks. F2 to F7 are Verified (driven). F1 is WontFix, with BUG-1021 as its home. My 336-row differential, re-run on the new tree, shows 0 differences between -C and cd and no gate bypass. The -C parsing shapes all hold.
  - F6: -C now refuses at the first bad component, as chdir does, for a missing hop, a non-directory, no search permission or a symlink loop. Its semantics are physical: link/.. is the parent of the link target. That matches cd -P, chdir(2), git -C and ADR-1009 section 1, but not the shell default cd -L. That may be worth a line in the ST6 docs for @tech-writer.
  - Two new findings, neither blocking. F8 (low): the rewritten guard catches every shape I reported, but misses 15 of 18 further shapes, such as Path("rel").resolve(), PosixPath.cwd, a cwd method reference, from os import environ, no-arg listdir and relpath. None of these exists in src today. F9 (info): value_options() rebuilds the command tree, about 47 ms per call, uncached, twice per run; it should be memoised.
<!-- sq:discussion:end -->
