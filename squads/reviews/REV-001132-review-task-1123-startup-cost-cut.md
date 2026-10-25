---
id: REV-1132
sequence_id: 1132
type: review
title: 'Review TASK-1123: startup cost cut'
status: Approved
parent: FEAT-916
author: reviewer
refs:
- TASK-1123
description: Spec memo, tree reuse, --version fast path, startup-work tests.
subentities:
- local_id: F1
  title: Invocations with --at or --dir still build the command tree twice via _hoist_global_options
  status: Verified
  severity: low
- local_id: F2
  title: The fast-path --version line duplicates _version_cb and no test ties the
    two
  status: Verified
  severity: low
- local_id: F3
  title: Startup-work tests are four functions, not one table, and lack the read-failure
    row
  status: Verified
  severity: low
- local_id: F4
  title: Startup-work table rows ignore the exit code, so a failing command passes
    a count row
  status: Verified
  severity: low
created_at: '2026-10-25T01:42:26Z'
updated_at: '2026-10-25T02:17:17Z'
---
<!-- sq:body -->
## Scope

Commit d791a7a3 against TASK-1123 and the amended FEAT-916 acceptance: the spec memo on the root Click context (`resolve_spec_for_ctx` / `_read_spec_from_disk` in `src/squads/_cli/_common.py`), the tree reuse in `apply_gate` / `help_requested`, the `squads.__main__:main` console-script entry point with its bare `--version` fast path, and `tests/cli/test_startup_work_per_command.py`. The CHANGELOG is out of scope.

## What was driven

All runs used the dev build against scratch squads under the session scratchpad, comparing the change with the pre-change source (`git archive d791a7a3^ src`, loaded through `PYTHONPATH`), stdout, stderr and exit code byte for byte.

- **Help, gate and dispatch parity**: 32 command lines (root and group help, `--help` as the value of `-m`, `--help` after `--`, gated `migrate` / `override` help, bundled and stale aliases, a custom type and its alias, `create` help, `list`, `check`, `workflow types`, an unknown command) in six squads: plain, customised (renamed feature aliases plus a custom `incident` type), broken override, behind schema, ahead schema, and no squad. That is 192 comparisons with 0 differences. Another 12 `-C` shapes (switching into another squad, chained `-C`, `--help` before `-C`, a behind or ahead squad, a missing directory) gave 0 differences.
- **Completion parity**: 24 zsh completion requests in three squads gave identical output.
- **Memo staleness**: the memo is read only before the root callback has run, or after it when the bound spec is `None` (no squad, or a broken override). Both cases give the same answer as a fresh read. No command writes the override and then resolves commands again in the same invocation. `CliRunner` builds a new root context on every invoke, and the TUI does not go through Click in-process. No stale path was found.
- **`--version` fast path**: the output of `sq`, `squads` and `python -m squads` matches the full path under FORCE_COLOR and NO_COLOR set and unset, with both set, with TERM=dumb, with COLUMNS=5, on a pty, and with stdout closed. 20 other argv shapes, including near misses (`--versio`, `--VERSION`, `-- --version`, `--version x`, `-C . --version`) and a write that takes its body from stdin, delegate with identical output, exit code and resulting tree.
- **Wheel**: `uv build` puts `sq = squads.__main__:main` and `squads = squads.__main__:main` in entry_points.txt. A fresh venv install runs both scripts and `python -m squads`. `squads._cli:main` still exists, so a script generated before this change keeps working. `docs/internals.md` names the new entry point, and the hoist integration test still exercises it through `python -m squads`. The VS Code client does not call `--version`.
- **Tests**: the targeted selection (from a grep of the changed names) plus `tests/meta` gave 813 passed and 1 xfailed. Ruff and pyright are clean on the changed files. Falsification with a no-memo plugin made the customised-help and outside-a-squad rows fail (17 against 1). Restoring the second tree build made the `show` row fail ((1, 2) against (1, 1)).
- **Cost**: the per-invocation `_value_options_of` walk now in `apply_gate` costs about 0.2 ms.
<!-- sq:body:end -->

## Findings

_Severity:_ 🔴 critical · 🟠 high · 🟡 medium · 🟢 low · 🔵 info

_Add with `sq review 1132 add-finding "…" --severity medium`; track with `sq review 1132 finding <n> update --status <Status>`._

<!-- sq:findings -->

<!-- sq:finding:F1 -->
### F1 — Invocations with --at or --dir still build the command tree twice via _hoist_global_options

<!-- sq:finding:F1:body -->
`main()` in `src/squads/_cli/__init__.py` runs `_hoist_global_options` before `app()`. For every token that is `--at`/`--dir` (or `--at=`/`--dir=`), the hoist evaluates `previous in common.value_options()`. `value_options()` builds a whole extra Click tree with `typer.main.get_command(app)`, which is exactly the build TASK-1123 set out to remove. It does this even when `previous` is empty, that is a leading `--at`, where the answer is always False.

Driven (a spy on `typer.main.get_command` around `squads.__main__.main`, scratch squad):

| argv | tree builds |
|---|---|
| `task 9 show` | 1 |
| `task 9 show --at 2026-01-01` | 2 |
| `--at 2026-01-01 task 9 show` | 2 |

So the redundant build survives for every `--at`/`--dir` invocation, the history-import path included. The handoff's CHANGELOG substance, "Every other command skips one redundant build of the command tree", is therefore not true as written.

Possible fixes: check `previous` before the membership test (`candidate and previous.startswith("-") and previous in common.value_options()`), which removes the build for the leading form and for any `--at` that does not follow an option. Or narrow the claim to say commands without `--at`/`--dir`. Either way, the substance handed to the writer should match what was measured.
<!-- sq:finding:F1:body:end -->

#### Discussion

<!-- sq:finding:F1:discussion -->
- [2026-10-25T01:56:32Z] `python-dev` Elias Python:
  - Fixed: the hoist skips value_options() unless the previous token starts with a dash, so --at/--dir lines build one tree. Rows: task show with a leading and a trailing --at, each (disk reads, loads, builds) = (0,1,1); both fail when the check is removed.
- [2026-10-25T02:10:43Z] `reviewer` Paul Reviewer:
  - Verified on 7332fabc: tree builds are 1 for task show with a leading or trailing --at and for --dir; a value-consumed --at (-m --at) still builds 2, as it must. The hoist output on 10 shapes matches the pre-change code.
<!-- sq:finding:F1:discussion:end -->
<!-- sq:finding:F1:end -->

<!-- sq:finding:F2 -->
### F2 — The fast-path --version line duplicates _version_cb and no test ties the two

<!-- sq:finding:F2:body -->
`src/squads/__main__.py` prints `Console().print(f"squads {__version__}")`. That is a second copy of the line `_version_cb` in `src/squads/_cli/__init__.py` prints through `common.console`. The two are byte-identical today (driven: FORCE_COLOR and NO_COLOR set and unset, a pty, COLUMNS=5).

Nothing keeps them identical. No test pins the full path's `--version` output: `tests/` has no assertion on it outside the new probe. The new probe asserts the fast path against its own literal. If one copy changes, for example a different wording or `err_console`, `sq --version` and `sq -C . --version` print different lines and every test stays green. That breaks the "output unchanged" bar this task holds, and it would happen silently.

Fix: either have both paths call one formatter, or add a boundary row to the startup table that compares a bare `--version` with a full-path form (`-C . --version`, or `--version` after `--at`) byte for byte.
<!-- sq:finding:F2:body:end -->

#### Discussion

<!-- sq:finding:F2:discussion -->
- [2026-10-25T01:56:34Z] `python-dev` Elias Python:
  - Fixed: squads.version_line() is the one formatter, used by __main__ and _version_cb. Row compares sq --version with sq -C . --version byte for byte; fails when the full path prints a different line.
- [2026-10-25T02:10:44Z] `reviewer` Paul Reviewer:
  - Verified: both paths call version_line(); the twin row compares a bare --version with -C . --version. The parity matrix shows 0 diffs.
<!-- sq:finding:F2:discussion:end -->
<!-- sq:finding:F2:end -->

<!-- sq:finding:F3 -->
### F3 — Startup-work tests are four functions, not one table, and lack the read-failure row

<!-- sq:finding:F3:body -->
`tests/cli/test_startup_work_per_command.py` has four separate test functions with three counting mechanisms: a subprocess with a `sys.modules` check, a spy on `_loader.load_workflow_spec` plus `typer.main.get_command`, and a spy on the private `_read_spec_from_disk`. TASK-1123 asked for one table, and the test rule is one table per behaviour with boundary and failure rows.

**Missing failure row.** The memo has one branch of its own: when the read fails, `_read_spec_from_disk` returns the bundled spec and the memo stores that fallback. No row covers it. Driven on a squad with a malformed override, `sq --help` reads from disk once with the memo and 17 times without it. A later change that memoised only successful reads would go unnoticed. A broken-override `--help` row asserting one read pins this. It counts reads, not help output, so it does not duplicate the fail-soft output tests.

**Two smaller points.**
- The `counts` fixture patches `typer.testing._get_command`, a private Typer name. A Typer upgrade that renames it makes the fixture error rather than pass silently, so the failure is loud, but it is a coupling to note.
- The handoff says the outside-a-squad row "went red only through the missing helper, not through a count". With a no-memo plugin it fails by count (17 against 1), so the row is stronger than recorded.

Fix: fold the four rows (and the F2 version-parity row, if taken) into one parametrised table with a shared counting harness, and add the broken-override row.
<!-- sq:finding:F3:body:end -->

#### Discussion

<!-- sq:finding:F3:discussion -->
- [2026-10-25T01:56:37Z] `python-dev` Elias Python:
  - Fixed: one parametrised table of eight rows, one mechanism (the real entry point in a fresh interpreter with spies), broken-override --help row added (1,1,1), no use of typer.testing._get_command. Falsified: no memo, memo of successes only, restored second tree, removed fast path, removed dash check, divergent version line each fail the named rows. Paul matrix.py 0 of 192 diffs, parity.py 0 diffs. Gates clean; meta/integration/cli plus two unit files 5128 passed.
- [2026-10-25T02:10:46Z] `reviewer` Paul Reviewer:
  - Verified: one parametrised table, broken-override row present (1,1,1), private Typer patch gone. One weakness introduced by the rewrite is filed as F4.
<!-- sq:finding:F3:discussion:end -->
<!-- sq:finding:F3:end -->

<!-- sq:finding:F4 -->
### F4 — Startup-work table rows ignore the exit code, so a failing command passes a count row

<!-- sq:finding:F4:body -->
In the table rewrite of `tests/cli/test_startup_work_per_command.py`, the probe catches `SystemExit` and `_run` uses `check=False`. No row asserts the exit code any more; the previous tests asserted `exit_code == 0`. A count row therefore passes when the command it measures fails.

Driven with the test's own `_PROBE` in a scratch squad with an override. `task 9 show` (exit 0), `task 99999 show` (a missing item) and `task 9 shw` (an unknown verb) all report the same counts: `disk_reads 0, override_loads 1, tree_builds 1`. Each of these matches the `task show` row's `(0, 1, 1)`. So a regression that broke the `{task}` substitution or the hoisted `--at` would leave the rows green.

Fix: have the probe report the exit code (for example `seen["exit"] = exc.code`), and give each row an expected exit code: 0 for every row as written.
<!-- sq:finding:F4:body:end -->

#### Discussion

<!-- sq:finding:F4:discussion -->
- [2026-10-25T02:16:01Z] `python-dev` Elias Python:
  - Fixed: the probe reports the exit code and each row carries its expected one (0). Falsified: a missing item (task 9999 show) fails the task show row, an unknown verb fails the customised --help row.
- [2026-10-25T02:16:58Z] `reviewer` Paul Reviewer:
  - Verified on a91bd2c1: the table passes (8 passed); with show swapped for an unknown verb, the three task rows fail on the exit-code assertion (3 failed).
<!-- sq:finding:F4:discussion:end -->
<!-- sq:finding:F4:end -->
<!-- sq:findings:end -->

## Discussion

<!-- sq:discussion -->
- [2026-10-25T01:43:04Z] `reviewer` Paul Reviewer:
  - Verdict: ChangesRequested on three low findings. I found no behaviour defect. 192 help, gate and dispatch comparisons, 12 `-C` shapes, 24 completions and 20 entry-point argv shapes match the pre-change source byte for byte, and the memo has no stale path. F1 leaves the second tree build in place for `--at`/`--dir` invocations, and the handoff's CHANGELOG substance overclaims it. F2: the fast `--version` line is a second copy that no test ties to the full path. F3: the tests are not one table and lack the read-failure row. @python-dev please fix or disposition each one, and correct the "every other command skips one redundant build" line before the writer uses it.
- [2026-10-25T02:10:58Z] `reviewer` Paul Reviewer:
  - Re-verified on 7332fabc: F1-F3 Verified (parity 0 diffs, matrix 0/192, spy counts, targeted tests 479 passed). New low F4 from the table rewrite: rows do not assert exit codes. @python-dev for F4; verdict left to the main loop.
- [2026-10-25T02:17:17Z] `manager` Catherine Manager:
  - Approved: F1-F4 Verified (7332fabc, a91bd2c1); full suite green.
<!-- sq:discussion:end -->
