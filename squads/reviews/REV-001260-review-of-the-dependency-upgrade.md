---
id: REV-1260
sequence_id: 1260
type: review
title: Review of the dependency upgrade
status: ChangesRequested
author: reviewer
refs:
- FEAT-1242
- TASK-1243
- BUG-1192
subentities:
- local_id: F1
  title: Ruff exclude 'squads' also drops src/squads from check and format
  status: Verified
  severity: high
- local_id: F2
  title: Index lock tests are cross-process cases in the surface suite
  status: Verified
  severity: medium
- local_id: F3
  title: No-flock filesystem ends in a traceback, not a SquadsError
  status: Verified
  severity: medium
- local_id: F4
  title: Killed-holder case bounds wall-clock time; holder docstring wrong
  status: Verified
  severity: low
- local_id: F5
  title: BUG-1192 case duplicates four existing unknown-option cases
  status: Verified
  severity: low
- local_id: F6
  title: ADR-1172 argument-name clause describes the pre-0.27 usage line
  status: Verified
  severity: low
- local_id: F7
  title: Usage lines mix upper and lower argument names (operator call)
  status: Open
  severity: info
- local_id: F8
  title: CHANGELOG lists none of the upgrade's adopter-visible changes
  status: Verified
  severity: medium
- local_id: F9
  title: Lock error message claims nothing was written; sq init has
  status: Fixed
  severity: low
- local_id: F10
  title: Cross-process CI job gets 15 min on Windows; ADR-1172 says 10
  status: Fixed
  severity: low
created_at: '2026-10-30T00:20:29Z'
updated_at: '2026-10-30T06:29:25Z'
---
<!-- sq:body -->
## Scope

TASK-1243 under FEAT-1242, and the BUG-1192 surface test it carries. Commits on release/0.19: 388b285d (lock, bounds, ruff excludes), 1a56857a (index lock), 8e881f55 (typer 0.27 surface tests and the BUG-1192 test). The handback is the last comment on TASK-1243. The operator's ruling on TASK-1243 (accept the typer 0.27 text, no `metavar=` workarounds) is taken as given.

## Method

- Bounds: every direct runtime and dev bound in `pyproject.toml` compared with its `uv.lock` entry; `uv lock --check`.
- Index lock: `_index/_store.py` read against filelock 4.2.4's own `_unix.py` (the soft-lock fallback path); a filesystem without flock simulated by making `fcntl.flock` raise `ENOSYS` in a scratch squad.
- Lock tests: read; run on a scratch export of HEAD (4 passed, 12.9 s, the timeout case 10.07 s); the concurrent-writers case falsified by making `_acquire_file_lock` a no-op (red 3 of 3 runs, "Item 1..3" lost), then restored and green.
- Ruff: `ruff check --show-files .` grouped by top-level directory; the exclude patterns tried on the export.
- typer 0.27: argument keys listed through `tests/_help_tree.command_nodes()` (`human_readable_name`) and compared with usage lines driven on a scratch squad; ADR-1172's covers grammar read.
- BUG-1192: the new test run under `--with typer==0.26.7` (red, tuple repr) and 0.27.3 (green).

## Results that hold

- Bounds equal the locked versions for every direct dependency (typer 0.27.3, pydantic 2.14.2, filelock 4.2.4, jinja2 3.1.6, rich 15.0.0, pyyaml 6.0.3, anyio 4.15.1, babel 2.18(.0), textual 8.2.8; dev pytest 9.2.0, pytest-cov 7.1.0, freezegun 1.5.5, ruff 0.17.3, pyright 1.1.414, anyio[trio] 4.15.1, xdist 3.8.0, vulture 2.16). `uv lock --check` passes.
- `fallback_to_soft=False, preserve_lock_file=True` is right for the index: a soft lock outlives a killed holder, and unlinking a released flock file splits waiters across inodes. In filelock 4.2.4, `preserve_lock_file=True` alone already disables the soft fallback, so the pair is belt and braces, not a conflict.
- The four lock cases each fail when their subject breaks (the developer's falsification, and the no-op-lock run above).
- The 10 s timeout case is acceptable under ADR-1172's time bound: the bound is per CI job (10 min, 15 on Windows), and 10 s is about 1 to 2 percent of it. Making the timeout injectable to save it would add a setting for the test's sake.
- typer 0.27: no `metavar=` workaround was added (the commit touches tests only), per the ruling. The coverage guard still names an argument by `human_readable_name`, so the covers grammar holds in substance; only its wording and examples are stale (finding).
- BUG-1192: the test is red on typer 0.26.7 and green on 0.27.3.
- The `docs/backends.md` exclusion is acceptable: ruff would add three blank lines and wrap one signature in a protocol sketch kept compact on purpose.
<!-- sq:body:end -->

## Findings

_Severity:_ 🔴 critical · 🟠 high · 🟡 medium · 🟢 low · 🔵 info

_Add with `sq review 1260 add-finding "…" --severity medium`; track with `sq review 1260 finding <n> update --status <Status>`._

<!-- sq:findings -->

<!-- sq:finding:F1 -->
### F1 — Ruff exclude 'squads' also drops src/squads from check and format

<!-- sq:finding:F1:body -->
388b285d sets `extend-exclude = ["clients", "squads", "docs/backends.md"]` in `[tool.ruff]`. Ruff reads a bare name as "any directory of that name anywhere in the tree", so `"squads"` also excludes `src/squads/`: the whole package is out of `ruff check` and `ruff format --check`, locally and in CI.

Driven at HEAD: `ruff check --show-files .` lists 0 files under `src/squads/` (163 under `tests/`, 4 under `scripts/`, plus `conftest.py`). On a scratch export with the pattern anchored, `"./squads"` or `"squads/**"`, ruff reads all 230 files of `src/squads/` again and still skips the item files: `ruff check` passes and `ruff format --check` reports nothing to reformat. So nothing is hidden today; the gate is just not looking at the package any more.

Fix: anchor the pattern (`"./squads"`), keep the one-line reason, and check `ruff check --show-files . | grep -c src/squads/` is non-zero.
<!-- sq:finding:F1:body:end -->

#### Discussion

<!-- sq:finding:F1:discussion -->
<!-- sq:finding:F1:discussion:end -->
<!-- sq:finding:F1:end -->

<!-- sq:finding:F2 -->
### F2 — Index lock tests are cross-process cases in the surface suite

<!-- sq:finding:F2:body -->
The four cases in `tests/cli/test_index_lock.py` start a holder process, kill it, and run four `sq` processes at once. ADR-1172 "The cross-process set" names exactly that: a behaviour belongs there "only when no in-process test can observe it: it needs one process to start, find or outlive another, a signal". That set runs the real `sq` console script, carries no `covers` marker and runs in its own CI job on each OS.

In `tests/cli` the cases instead:
- declare pairs they only use: the concurrent-writers case declares `covers("list", "--type")` because it reads the result with `list --type`, and the other three declare `covers("create <type>", "--author")`. The coverage guard counts them as surface coverage of those pairs.
- run in both squad jobs (bundled and override), so the 13 s file runs twice, and inside the surface run's xdist workers, where the waiting-notice and killed-holder timings compete with the load.

Fix: move them to the cross-process set (a `tests/` directory of their own, outside the surface suite, without `covers` markers), run once per OS. If that set's CI job does not exist yet, this is where it starts; ask the tech lead if that belongs in the daemon work instead.
<!-- sq:finding:F2:body:end -->

#### Discussion

<!-- sq:finding:F2:discussion -->
<!-- sq:finding:F2:discussion:end -->
<!-- sq:finding:F2:end -->

<!-- sq:finding:F3 -->
### F3 — No-flock filesystem ends in a traceback, not a SquadsError

<!-- sq:finding:F3:body -->
`fallback_to_soft=False` means "fail loudly" where the filesystem has no flock (some network and FUSE mounts). Driven on a scratch squad with `fcntl.flock` made to raise `ENOSYS`: `sq create feature ...` ends in a Rich traceback through `filelock/_unix.py` and `OSError: [Errno 38] Function not implemented`. `handle_errors` catches only `SquadsError`, so nothing turns it into a message.

Before this change filelock fell back to a soft lock and the command worked. An adopter whose squad sits on such a mount now gets a traceback with no hint of the cause, and CLAUDE.md asks for user-facing errors as `SquadsError`.

Fix: catch the `OSError` from the lock acquire in `_index/_store.py` and raise a `SquadsError` that names the lock path and the reason (the filesystem does not support file locks, so `sq` cannot guard the index there). One surface case: patched flock, exit 1, the message.
<!-- sq:finding:F3:body:end -->

#### Discussion

<!-- sq:finding:F3:discussion -->
- [2026-10-30T00:38:53Z] `reviewer` Paul Reviewer:
  - - Reopened at 00f9abf7. The ENOSYS case holds: a patched `fcntl.flock` (the real filelock path, not a patched `acquire`) gives exit 1, the new message, nothing written, and reads still work; the surface case goes red without the fix.
    - But `except OSError` catches every lock-open error and labels it a file system without locks. Driven: a read-only `.squads.json.lock` (chmod 444) prints `cannot take the index lock …: Permission denied; this file system does not support file locks, so sq cannot guard the index there, move the squad to one that does`. Permission denied, a read-only mount or a missing directory get the wrong cause and the wrong remedy.
    - Fix: keep the "does not support file locks… move the squad" wording for `errno` ENOSYS (and ENOLCK/EOPNOTSUPP if you judge them the same case). Any other `OSError` gets a `SquadsError` that names the lock path and `strerror` with no claim about the file system. Add one surface case for the other branch (EACCES).
    - Marker: the case declares `covers("create <type>", "--author")`, but its subject is the refusal. As in F5, declare the bare key `covers("create <type>")`.
    - @python-dev
- [2026-10-30T00:57:34Z] `reviewer` Paul Reviewer:
  - - Verified at 32a8e94a (2a46569e), on a scratch export and scratch squads.
    - Both branches driven on the real filelock path. A read-only `.squads.json.lock` (chmod 444) with `sq create task`: exit 1, `cannot take the index lock …: Permission denied; nothing was written`, no task file. `fcntl.flock` raising ENOLCK: exit 1, the "does not support file locks… move the squad" wording.
    - Cases: both in tests/cli/test_repair.py with bare `covers("repair")`; the EACCES case also checks that `list --json` is unchanged. Both falsified: forcing the no-lock branch turns the EACCES case red, forcing the other branch turns the ENOSYS case red; restored, 2 passed.
    - The new clause "nothing was written" is not true for every caller. That is F9, filed apart from this finding.
<!-- sq:finding:F3:discussion:end -->
<!-- sq:finding:F3:end -->

<!-- sq:finding:F4 -->
### F4 — Killed-holder case bounds wall-clock time; holder docstring wrong

<!-- sq:finding:F4:body -->
`test_a_holder_killed_hard_releases_the_lock` asserts `time.monotonic() - started < 1.0` around an in-process `sq create`. The case's subject is already asserted without a clock: `waiting for the index lock` is absent, and the store prints it after one second of waiting. The wall-clock bound adds only a way to fail on a loaded runner (xdist workers, Windows CI) while the lock behaves.

Also, the `HOLDER` docstring says it "takes the squad's lock the way `sq` does", but it builds `FileLock(path, thread_local=False)` with filelock's defaults, not the store's `fallback_to_soft=False, preserve_lock_file=True`. Interop holds (both take flock on the same file); the sentence is what is wrong.

Fix: drop the `< 1.0` assertion; reword the docstring or pass the store's flags.
<!-- sq:finding:F4:body:end -->

#### Discussion

<!-- sq:finding:F4:discussion -->
<!-- sq:finding:F4:discussion:end -->
<!-- sq:finding:F4:end -->

<!-- sq:finding:F5 -->
### F5 — BUG-1192 case duplicates four existing unknown-option cases

<!-- sq:finding:F5:body -->
ST7 adds `test_post_names_the_options_close_to_an_unknown_one_as_plain_text` in `tests/cli/test_board.py`. The same commit updates the existing unknown-option assertions in `test_subentity_verbs.py`, `test_list.py`, `test_tree.py` and `test_item_verbs.py` from the tuple repr to the plain text, and the handback says they are red on typer 0.26.7 too. So BUG-1192 was already pinned by four surface cases (which until this commit pinned the bug itself); the new case adds no observation. ADR-1172 "Time bound": "review checks for cross products and duplicated cases".

Its marker is also off the refusal rule: it declares `covers("board post", "--message")`, a parameter the call passes, while the refusal is about an unknown option.

Fix: drop the new case and cite one of the existing ones on BUG-1192 as its surface test. If the operator wants a case of its own (his ruling asked for "the BUG-1192 surface test"), declare the bare key `covers("board post")` instead of `--message`.
<!-- sq:finding:F5:body:end -->

#### Discussion

<!-- sq:finding:F5:discussion -->
<!-- sq:finding:F5:discussion:end -->
<!-- sq:finding:F5:end -->

<!-- sq:finding:F6 -->
### F6 — ADR-1172 argument-name clause describes the pre-0.27 usage line

<!-- sq:finding:F6:body -->
ADR-1172 "Parameter name": "An argument is named as the usage line prints it (`N`, `TITLE`), which is Click's `human_readable_name`." Under typer 0.27 the usage line prints `{title}` and `{N}`, and `human_readable_name` is `title` (lower case, no braces) for an argument without a metavar and the metavar itself where one is set (`N`, `STATUS`, `LOCAL-ID`, `<slug|id|n>`). The coverage guard (`tests/_cli_surface.py`) uses `human_readable_name`, so the rule holds in substance and the markers are right; the sentence and its `TITLE` example now describe a different string from what an adopter sees.

Fix (architect): amend the clause to name the argument by `human_readable_name` alone, with current examples (`title`, `N`), and record the amendment in the ADR's discussion.
<!-- sq:finding:F6:body:end -->

#### Discussion

<!-- sq:finding:F6:discussion -->
- [2026-10-30T00:30:36Z] `architect` Robert Architect:
  - Fixed: ADR-1172 amended in place 2026-10-30. "Parameter name" states the key as `human_readable_name` (metavar, else parameter name: `N`, `title`) and notes the usage-line braces; the refusal example `TITLE` became `title`. No other upper-case argument example remains in the ADR.
<!-- sq:finding:F6:discussion:end -->
<!-- sq:finding:F6:end -->

<!-- sq:finding:F7 -->
### F7 — Usage lines mix upper and lower argument names (operator call)

<!-- sq:finding:F7:body -->
For the operator, under the ruling to accept typer 0.27's text. Usage lines now mix two casings, because typer lower-cases an argument without a metavar and squads still sets upper-case metavars on others. Driven or read from the help tree: `sq task {N} status [OPTIONS] {STATUS}`, `sq create task [OPTIONS] {title}`, `sq memory {role} add [OPTIONS] {fact}`, `sq board clear {n}` beside `sq task {N}`, `sq migrate rename-status [OPTIONS] {TYPE} {OLD_STATUS} {NEW_STATUS}` beside `sq record {N} retype [OPTIONS] {NEW-TYPE}`.

Dropping squads' own upper-case metavars would make them consistent with typer's default; that is not a workaround to keep the old wording, but it is a change of adopter-visible text, so it is the operator's call. No action if the mix is accepted.
<!-- sq:finding:F7:body:end -->

#### Discussion

<!-- sq:finding:F7:discussion -->
<!-- sq:finding:F7:discussion:end -->
<!-- sq:finding:F7:end -->

<!-- sq:finding:F8 -->
### F8 — CHANGELOG lists none of the upgrade's adopter-visible changes

<!-- sq:finding:F8:body -->
FEAT-1242 US1 asks that every adopter-visible change an upgrade causes is "listed in the changelog". The TASK-1243 handback reports them (braced usage-line names, lower-case missing-argument names, `not a valid int`, the plain-text suggestion, the `<str>`/`<int>` help column, the lock file now kept after every write, no soft-lock fallback, raised minimum versions). `CHANGELOG.md` at HEAD has none of them (no mention of typer, filelock, braced names or the lock file staying on disk).

Fix (tech writer): write the entries from the handback. If G3 lands, the no-flock entry says what the adopter sees then.
<!-- sq:finding:F8:body:end -->

#### Discussion

<!-- sq:finding:F8:discussion -->
- [2026-10-30T00:29:09Z] `tech-writer` Theo Writer:
  - Fixed in the working tree (uncommitted); each item was checked at HEAD on a scratch squad. CHANGELOG 0.19.0 Changed has a BREAKING entry for the Typer 0.27.3 wording (braced and lower-case usage names, `Missing argument 'title'.` with declared names such as STATUS kept, `is not a valid int.`, the `<str>`/`<int>` help column and the Arguments panel), an index-lock entry (the file stays on disk; no fallback where the filesystem has no lock) and the raised minimum versions. Fixed has the plain-text option suggestion. The existing 0.19 entry that quoted `Missing argument 'TITLE'.` and the two quotes of `--impact TEXT` (overrides.md and CHANGELOG) now show the new text, and the README `sq search TEXT` synopsis reads `<text>`. The lock entry does not quote a message for the no-lock case: until F3 lands it ends in a traceback.
<!-- sq:finding:F8:discussion:end -->
<!-- sq:finding:F8:end -->

<!-- sq:finding:F9 -->
### F9 — Lock error message claims nothing was written; sq init has

<!-- sq:finding:F9:body -->
The other-error branch of `IndexLockUnavailableError` (`_errors.py`) ends with "nothing was written". That holds for commands whose first write is inside the lock (create, repair), but not for every caller. Driven: `sq init` in an empty git repo with `FileLock.acquire` raising EACCES prints `cannot take the index lock …: Permission denied; nothing was written` and exits 1. It has already written `.squads.toml`, `.gitignore`, `squads/.squads.json`, `squads/.gitignore` and `.claude/settings.json`, because init takes the lock only when it seeds the skills. A rerun then finds a squad that the message said was never written.

The trigger is rare (the lock has to fail in a directory init has just written to), but the sentence is unconditional and the store cannot know what its caller has written before.

Fix: drop "; nothing was written" so the message names the lock path and the system text only, and keep the `list --json` check in the EACCES case. Optional, same lines: add `errno.ENOTSUP` to `_NO_FILE_LOCKS`. On Linux it is the same value as EOPNOTSUPP (95). On macOS they differ (45 and 102), and macOS flock(2) documents ENOTSUP. This is inferred from the man page and was not run on macOS.
<!-- sq:finding:F9:body:end -->

#### Discussion

<!-- sq:finding:F9:discussion -->
<!-- sq:finding:F9:discussion:end -->
<!-- sq:finding:F9:end -->

<!-- sq:finding:F10 -->
### F10 — Cross-process CI job gets 15 min on Windows; ADR-1172 says 10

<!-- sq:finding:F10:body -->
Commit 28999c46 gives the `cross-process` job `timeout-minutes: ${{ matrix.os == 'windows-latest' && 15 || 10 }}`. ADR-1172 "Time bound" (refined in 8e8abce4, after that commit) says the cross-process set is a CI test job under the same targets, and that "the 15-minute bound is only for the Windows job that runs the full suite". That job is `test`. The cross-process job on Windows is bounded at 10.

`test` (15 on Windows, 10 elsewhere), `override-squad` (10) and `lint` (10, not a test job) match the ADR.

Fix: `timeout-minutes: 10` on `cross-process`, with no per-OS expression.
<!-- sq:finding:F10:body:end -->

#### Discussion

<!-- sq:finding:F10:discussion -->
<!-- sq:finding:F10:discussion:end -->
<!-- sq:finding:F10:end -->
<!-- sq:findings:end -->

## Discussion

<!-- sq:discussion -->
- [2026-10-30T00:25:15Z] `reviewer` Paul Reviewer:
  - Review of TASK-1243. Holds: bounds equal the locked versions, uv lock --check passes, the lock flags are right, the four lock cases fail when their subject breaks (concurrent-writers falsified 3 of 3 with a no-op acquire), the 10 s timeout case is acceptable under the ADR-1172 job bound, no metavar workarounds, BUG-1192 case red on typer 0.26.7 and green on 0.27.3, the docs/backends.md exclude is fine.
  - Findings: F1 high (the squads exclude drops src/squads from ruff check and format, all 230 files; anchor it as ./squads), F2 medium (lock tests belong to the ADR-1172 cross-process set, not tests/cli with incidental covers), F3 medium (no-flock filesystem ends in a traceback), F8 medium (CHANGELOG lacks the upgrade entries), F4-F6 low, F7 info for the operator. Not verified: macOS and Windows CI.
  - Verdict: changes requested. @manager route F1-F5 to the TASK-1243 dev (F1 first, it is one line), F6 to @architect (ADR-1172 amendment), F7 to op-pierre, F8 to @tech-writer.
- [2026-10-30T00:32:24Z] `python-dev` Elias Python:
  - F1-F5 fixed on branch worktree-agent-aa7a974cd9f4254e2 (on top of origin/release/0.19 6e0c62f5): 018fccc5 (F1), fd31ecf3 (F3), 84d0e2ba (F2, F4, F5).
  - F1 exclude is now ./squads; ruff --show-files lists 230 src/squads files and no item file; fixed the over-long docstring line and two formatting hunks it found in src.
  - F2 lock tests moved to tests/cross_process (real sq script, no covers, own CI job per OS, ignored by the main pytest job); F3 new IndexLockUnavailableError plus one tests/cli case, red without the fix; F4 clock assertion dropped, holder uses the store flags; F5 duplicate case dropped, the existing unknown-option cases pin BUG-1192. Gates: pyright 0, ruff clean, pytest tests 1795 passed, --squad override tests/cli 813 passed.
- [2026-10-30T00:35:38Z] `devops` Hugo Ops:
  - @manager devops review of F2 CI (commit 9b542722, .github/workflows/test.yml): approve, one suggested diff.
    
    Read and checked:
    - SHA pins: all 12 `uses:` lines are the same three SHAs/versions as the existing jobs (checkout v7.0.1, setup-python v7.0.0, setup-uv v10.2.0); the new job adds no new action.
    - Matrix: cross-process runs on ubuntu/windows/macos with fail-fast false, identical to `test`. Checkout uses fetch-depth 0, as the other jobs do.
    - Reaching `sq`: no PATH reliance. The test resolves it with shutil.which("sq", path=<dir of sys.executable>), run under `uv run`, so it is the venv's console script. On Windows which() applies PATHEXT and finds Scripts/sq.exe (the uv/pip shim), on Linux and macOS bin/sq. An assert fails loudly if it is missing. Not run on Windows or macOS from here.
    - Hard kill: Popen.kill() is SIGKILL on POSIX and TerminateProcess on Windows, so the "holder killed hard" case is not skipped and needs no adaptation; there is no skip/skipif in the folder. The OS drops the lock handle on process death on every OS. Not run on Windows from here.
    - `test` job: `uv run pytest --ignore=tests/cross_process`, so the folder is not collected there. `override-squad` runs `tests/cli` only, so it never collected it. The new job runs `tests/cross_process` alone.
    - YAML: parses with pyyaml (jobs: lint, test, override-squad, cross-process). actionlint is not installed here, so not run.
    
    Findings (suggestions, none blocking):
    1. No `timeout-minutes` on any job. ADR-1172 sets 10 min (15 on Windows) as the time bound, and the lock tests hold a process for 60 s, so a hang would sit at the 6 h default. Suggested diff on cross-process (and later on the daemon jobs): `timeout-minutes: ${{ matrix.os == 'windows-latest' && 15 || 10 }}` under `runs-on`.
    2. `addopts` carries `-n auto`, so the timing-sensitive lock tests (2 s hold, concurrent writers) run in parallel xdist workers on 2-4 core runners. They are isolated in their own tmp squads, so it is probably fine, but `-n0` on that pytest line would remove a flake source for a 4-case set. Optional.
    3. Windows text decoding of the "…" in the waiting message relies on the test and sq using the same locale encoding on the pipe. Not verified; watch the first Windows run.
    
    TASK-1220: its planned daemon jobs fit this pattern (same four setup steps, one pytest line per job). Two points: the cross-process job there is already built, so ST1 only has to add the opt-in option if TASK-1219 still wants one (the folder is selected by path today and kept out of `test` by --ignore, not by an option); and the leak check plus `SQUADS_DAEMON=off` job env must be added to this job too, as well as to `test` and `override-squad`. Per-OS timeouts from finding 1 are the natural home for the 10/15 bound.
- [2026-10-30T00:38:55Z] `reviewer` Paul Reviewer:
  - - Second pass at 00f9abf7, on a scratch export (no full suite). Verified: F1, F2, F4, F5, F6, F8. Reopened: F3. F7 is still waiting for op-pierre.
    - F1: the exclude is `./squads`. `ruff check --show-files` lists 230 files under src/squads and none under the top-level squads/. `ruff check` passes and `ruff format --check` passes (460 files).
    - F2: the tests are in tests/cross_process. They run the real console script from the environment, carry no `covers`, have no conftest of their own, and assert whole stderr. The `test` job passes `--ignore=tests/cross_process`. The `cross-process` job runs on ubuntu, windows and macos. That matches ADR-1172 "The cross-process set". 4 passed in 15.7 s. With a no-op `_acquire_file_lock`, the concurrent-writers case was red on 2 of 3 runs (it depends on the race). Gap, not blocking: the ADR asks for whole output, but stdout is read only for fields (ids and title), or not at all in the killed-holder case. CI YAML not reviewed (devops).
    - F4: no wall-clock assertion is left, and the holder uses the store's flags.
    - F5: the case is dropped. `test_item_verbs.py::test_update_sets_and_clears_a_field_only_some_types_declare` and `test_subentity_verbs.py::test_a_required_field_has_no_clear_flag` fail on typer 0.26.7, which prints the tuple repr, and pass on 0.27.3. BUG-1192 still cites the dropped case (ced7f061); @manager, point it at one of these two.
    - F6: "Parameter name" now names `human_readable_name` (`N`, `HASH`, `<slug|id|n>`, `title`), no `TITLE` is left, and the amendment is recorded (676c718).
    - F8: spot-driven, all as written: `Missing argument 'title'.` / `'STATUS'.`, `'x' is not a valid int.`, `sq tree [OPTIONS] [root_id]`, `title <str>`, `sq memory {role} add [OPTIONS] {fact}`, `No such option: --slug (Possible options: --as)`. When F3 is fixed again, the lock entry can quote the no-lock message.
    - Verdict: changes requested. Only F3 is left (one branch narrowed, one case added). Once it is verified, and with F7 left to op-pierre, I recommend Approved.
- [2026-10-30T00:44:57Z] `python-dev` Elias Python:
  - F3 reopened and fixed in bb2ccde0: ENOSYS, ENOLCK and EOPNOTSUPP keep the file-system wording; any other OSError says cannot take the index lock PATH: SYSTEM TEXT; nothing was written. Cases moved to tests/cli/test_repair.py (repair takes the lock with no parameters, so the marker is the bare covers("repair"); a bare create key cannot be reached with a title), ENOSYS and EACCES, both falsified.
- [2026-10-30T00:57:38Z] `reviewer` Paul Reviewer:
  - - Third pass at 32a8e94a. F3 Verified (see its thread). Two new low findings: F9, "nothing was written" is false when `sq init` meets a lock error; F10, the cross-process job gets 15 min on Windows, but ADR-1172 keeps 15 for the full-suite Windows job only.
    - CI timeout commit 28999c46 otherwise matches ADR-1172: `test` 15 on Windows and 10 elsewhere, `override-squad` 10, cross-process run with `-n0`.
    - Verdict: changes requested on F9 and F10 only. Each is a one-line edit. When both are verified, and with F7 left to op-pierre, I recommend Approved. BUG-1192 stays Fixed until then. @python-dev
<!-- sq:discussion:end -->
