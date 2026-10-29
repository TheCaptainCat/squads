---
id: TASK-1243
sequence_id: 1243
type: task
title: Upgrade runtime and dev dependencies, raise lower bounds
status: Draft
parent: FEAT-1242
author: tech-lead
priority: high
refs:
- ADR-1172
- BUG-1192:fixes
description: Lock typer 0.27, filelock 4, pydantic 2.14, anyio 4.15, ruff 0.17, pyright,
  pytest; bounds raised to the versions the suite runs
subentities:
- local_id: ST1
  title: 'typer 0.27: help tree and usage errors match what adopters see'
  status: Todo
  story: US1
- local_id: ST2
  title: 'filelock 4: index lock tests, release on process death'
  status: Todo
  story: US1
- local_id: ST3
  title: pydantic 2.14 and anyio 4.15 locked, suite green
  status: Todo
  story: US1
- local_id: ST4
  title: Runtime lower bounds raised to the tested versions
  status: Todo
  story: US1
- local_id: ST5
  title: ruff 0.17, pyright, pytest locked; gates clean
  status: Todo
  story: US2
- local_id: ST6
  title: Report adopter-visible changes for the changelog
  status: Todo
  story: US1
- local_id: ST7
  title: Surface test for the unknown-option suggestion (BUG-1192)
  status: Todo
  story: US1
created_at: '2026-10-29T16:23:49Z'
updated_at: '2026-10-29T16:43:09Z'
---
<!-- sq:body -->
## Goal

The lock file and the declared bounds name the versions an adopter actually gets. Today they do not: the released 0.18.0 installed as a uv tool on the reference host already resolves typer 0.27.3, filelock 4.2.4, pydantic 2.14.1 and anyio 4.15.1, while this repository's lock and suite run typer 0.26.7, filelock 3.29.1, pydantic 2.13.4 and anyio 4.14.0. This task upgrades the lock to current releases, brings the code and tests clean under them, and raises every lower bound to the version the suite runs.

## Versions (measured 2026-10-29 with `uv lock --upgrade --dry-run` and `uv pip list --outdated`)

| Package | Declared bound | Locked | Latest | New bound |
|---|---|---|---|---|
| typer | >=0.12 | 0.26.7 | 0.27.3 | >=0.27.3 |
| filelock | >=3.13 | 3.29.1 | 4.2.4 | >=4.2.4 |
| pydantic | >=2.6 | 2.13.4 (core 2.46.4) | 2.14.1 (core 2.50.1) | >=2.14.1 |
| anyio | >=4 | 4.14.0 | 4.15.1 | >=4.15.1 |
| jinja2 | >=3.1 | 3.1.6 | 3.1.6 | >=3.1.6 |
| rich | >=13.7 | 15.0.0 | 15.0.0 | >=15.0.0 |
| pyyaml | >=6.0 | 6.0.3 | 6.0.3 | >=6.0.3 |
| babel | >=2.18 | 2.18.0 | 2.18.0 | >=2.18.0 |
| textual (tui extra) | >=0.29.0 | 8.2.8 | 8.2.8 | >=8.2.8 |
| ruff (dev) | >=0.6 | 0.15.16 | 0.17.3 | >=0.17.3 |
| pyright (dev) | >=1.1.380 | 1.1.410 | 1.1.414 | >=1.1.414 |
| pytest (dev) | >=8.0 | 9.0.3 | 9.2.0 | >=9.2.0 |
| pytest-cov (dev) | >=5.0 | 7.1.0 | 7.1.0 | >=7.1.0 |
| pytest-xdist (dev) | >=3.8.0 | 3.8.0 | 3.8.0 | >=3.8.0 |
| freezegun (dev) | >=1.4 | 1.5.5 | 1.5.5 | >=1.5.5 |
| anyio[trio] (dev) | >=4.14.0 | trio 0.33.0 | trio 0.34.0 | anyio[trio]>=4.15.1 |
| vulture (dev) | >=2.16 | 2.16 | 2.16 | unchanged |

Transitive moves in the same upgrade: python-dateutil 2.9.0.post0 to 3.0.0 (a major, pulled by freezegun), tzdata 2026.6 added, uc-micro-py removed, plus patch-level moves (annotated-types, coverage, platformdirs, pluggy, pygments, typing-extensions, typing-inspection, packaging, idna, markupsafe). If a bound cannot reach the latest release, the bound is the version the suite ran and the reason goes in the subtask discussion.

Not in scope here: the daemon's server dependencies. `starlette` and `uvicorn` are not in `pyproject.toml` today; the daemon process task adds them to `[project] dependencies`, and their lower bounds are set there to the versions it locks (latest on 2026-10-29: starlette 1.10.0, uvicorn 0.54.0; httpx 0.28.1 if its tests use a test client).

## What is already known

**typer 0.27** (probed by running the CLI under both versions; not yet an exhaustive diff):
- Argument metavars in usage lines change from upper case to braced lower case: `sq create task [OPTIONS] TITLE` becomes `{title}`, and the item group line `sq task [OPTIONS] N COMMAND` becomes `{N} COMMAND`.
- The missing-argument error names the parameter differently: `Missing argument 'TITLE'.` becomes `Missing argument 'title'.`
- Unchanged in the probes: `No such option`, `No such command ... Did you mean`, `Got unexpected extra argument(s)`, `Missing command.`, exit code 2.

**filelock 4** (probed): `FileLock(path, timeout=..., thread_local=False)`, `acquire(timeout=...)` and `Timeout` keep their shape, so `_index/_store.py` imports and runs unchanged. Two new defaults matter for the index lock:
- `fallback_to_soft=True`: where the OS lock is unavailable, filelock silently falls back to a soft lock, which is a file whose existence is the lock and which is not released when its holder dies. The store must not take that path silently; pass `fallback_to_soft=False` so an unusable lock fails loudly, unless the subtask finds a reason not to.
- `preserve_lock_file=False`: the lock file is removed after release. The squad's `.gitignore` entry for `.squads.json.lock` stays harmless; confirm nothing reads the lock file's presence.
- No test in `tests/` exercises the index lock today, so this task adds them.

**ruff 0.17**: `ruff check .` is clean as configured (0 findings measured). `ruff format --check` now also formats Python code blocks inside Markdown and fails on 14 files: 13 sq-managed item files under `squads/` and `docs/backends.md`. Item files are never hand-edited or reformatted, so `squads/` is excluded from ruff; `docs/backends.md` is either formatted or excluded, with the choice explained in one line beside the setting. The `[tool.ruff.lint]` comment that names ruff 0.15.16 for the preview-behaviour measurement is re-measured and updated to the version actually run.

**pyright 1.1.414**: 0 errors, 0 warnings measured with `--all-extras`.

## Test approach

Per ADR-1172: behaviours are observed through `sq` itself, one case per behaviour plus its boundary refusal, no shape tables. Expected new tests: 4 (the index lock cases in the filelock subtask). The typer subtask changes existing assertions where the wording moves and adds none unless a usage error has no surface test at all. Every new lock test is falsified by hand before handoff: break the lock (for instance, a no-op acquire), watch the test go red, restore, watch it go green, and report both.

## Done when

- `uv.lock` holds the versions in the table; `pyproject.toml` declares the new bounds.
- `uv run --all-extras pyright`, `ruff check .`, `ruff format --check .`, the full suite and `sq check` pass, on Linux locally and on the CI matrix (Linux, macOS, native Windows); CI keeps `uv sync --frozen`, so it runs the locked versions.
- Every adopter-visible change an upgrade causes is either kept identical or reported for the changelog.
<!-- sq:body:end -->

## Subtasks

_Add with `sq task 1243 add-subtask "<title>"`; track with `sq task 1243 subtask <n> update --status <Status>`._

<!-- sq:subtasks -->

<!-- sq:subtask:ST1 -->
### ST1 — typer 0.27: help tree and usage errors match what adopters see

<!-- sq:subtask:ST1:body -->
Lock typer 0.27.3 and bring the CLI's printed surface in line.

- Upgrade, then compare the whole help tree and the usage errors under 0.26.7 and 0.27.3 (the help-tree helper in `tests/_help_tree.py` walks every command), not only the cases already probed.
- Known changes: argument metavars print braced lower case (`{title}` for `TITLE`, `{N}` for `N` on the item group line), and `Missing argument 'TITLE'.` becomes `Missing argument 'title'.`. Decide per change whether to keep the old text (an explicit `metavar=` on the argument is the likely lever) or accept the new one; either way the surface tests assert the text adopters see, and accepted changes go to the changelog report.
- Usage errors keep exit code 2.
- Run tests/cli, tests/meta and the golden and help-tree tests: this changes rendered output that tests hold frozen copies of.
<!-- sq:subtask:ST1:body:end -->

#### Discussion

<!-- sq:subtask:ST1:discussion -->
<!-- sq:subtask:ST1:discussion:end -->
<!-- sq:subtask:ST1:end -->

<!-- sq:subtask:ST2 -->
### ST2 — filelock 4: index lock tests, release on process death

<!-- sq:subtask:ST2:body -->
Lock filelock 4.2.4 and prove the index lock under it through `sq`.

- `_index/_store.py` runs unchanged against the 4.x API (probed). Pass `fallback_to_soft=False` to the `FileLock` so the store never silently degrades to a soft lock that survives its holder's death; if that turns out wrong on a CI platform, record why in the discussion. Confirm nothing depends on the lock file staying on disk now that `preserve_lock_file` defaults to False.
- Add the four index-lock cases, observed through `sq` (ADR-1172), each falsified by hand:
  1. two concurrent writers serialise: both creates succeed with distinct IDs and the index stays valid;
  2. a writer that finds the lock held prints `waiting for the index lock` on stderr after about a second, then proceeds when the holder releases;
  3. a lock held past the 10-second timeout makes the command fail with the locked error and exit 1, with nothing written;
  4. a holder process killed hard (SIGKILL; `TerminateProcess` on Windows) releases the lock: the next `sq` write proceeds without waiting.
- The holder in cases 2 to 4 is a helper process taking the same `FileLock` on the squad's `.squads.json.lock`. Case 3 costs the full timeout; keep it the only slow one and do not mark it skipped by default.
<!-- sq:subtask:ST2:body:end -->

#### Discussion

<!-- sq:subtask:ST2:discussion -->
<!-- sq:subtask:ST2:discussion:end -->
<!-- sq:subtask:ST2:end -->

<!-- sq:subtask:ST3 -->
### ST3 — pydantic 2.14 and anyio 4.15 locked, suite green

<!-- sq:subtask:ST3:body -->
Lock pydantic 2.14.1 (pydantic-core 2.50.1) and anyio 4.15.1 (trio 0.34.0 for the trio-backed tests), with the transitive refresh the upgrade brings.

- Run the full suite under the upgraded lock; fix any model, serialisation or validation-message change in code. A validation message that reaches the user and changes wording goes to the changelog report.
- anyio carries the store's per-loop locks and the thread bridge; the async tests run on both backends.
- freezegun now pulls python-dateutil 3.0.0 (a major) and tzdata: confirm the `frozen_time` fixture and every time-frozen test still pass.
<!-- sq:subtask:ST3:body:end -->

#### Discussion

<!-- sq:subtask:ST3:discussion -->
<!-- sq:subtask:ST3:discussion:end -->
<!-- sq:subtask:ST3:end -->

<!-- sq:subtask:ST4 -->
### ST4 — Runtime lower bounds raised to the tested versions

<!-- sq:subtask:ST4:body -->
Raise every runtime lower bound in `[project] dependencies` and the `tui` extra to the version the suite ran, per the table in the task body: typer>=0.27.3, filelock>=4.2.4, pydantic>=2.14.1, anyio>=4.15.1, jinja2>=3.1.6, rich>=15.0.0, pyyaml>=6.0.3, babel>=2.18.0, textual>=8.2.8.

- No upper bounds.
- Re-lock and confirm `uv lock --check` passes and the locked versions equal the declared minimums for the direct runtime dependencies.
- The daemon's server dependencies (`starlette`, `uvicorn`) are not declared yet; they get their bounds where they are added.
<!-- sq:subtask:ST4:body:end -->

#### Discussion

<!-- sq:subtask:ST4:discussion -->
<!-- sq:subtask:ST4:discussion:end -->
<!-- sq:subtask:ST4:end -->

<!-- sq:subtask:ST5 -->
### ST5 — ruff 0.17, pyright, pytest locked; gates clean

<!-- sq:subtask:ST5:body -->
Lock ruff 0.17.3, pyright 1.1.414, pytest 9.2.0 with its plugins (pytest-cov 7.1.0, pytest-xdist 3.8.0, freezegun 1.5.5, anyio[trio]), and raise the `[dependency-groups] dev` bounds to them.

- ruff check is clean as configured (measured). ruff format now formats Python blocks inside Markdown and flags 14 files: 13 sq-managed item files under `squads/` and `docs/backends.md`. Exclude `squads/` from ruff; format or exclude `docs/backends.md`, with a one-line reason beside the setting.
- Re-measure the preview-behaviour note in `[tool.ruff.lint]` (it names 0.15.16) under 0.17.3 and update it to the version actually run.
- pyright reports 0 errors at 1.1.414 (measured); keep it so.
- Any newly reported issue is fixed in code, not silenced, unless the suppression carries a one-line reason.
- CI runs `uv sync --frozen`, so it picks up the lock; check the workflow invokes no tool at a version outside the lock.
<!-- sq:subtask:ST5:body:end -->

#### Discussion

<!-- sq:subtask:ST5:discussion -->
<!-- sq:subtask:ST5:discussion:end -->
<!-- sq:subtask:ST5:end -->

<!-- sq:subtask:ST6 -->
### ST6 — Report adopter-visible changes for the changelog

<!-- sq:subtask:ST6:body -->
Report every adopter-visible change the upgrades cause to the technical writer, who writes the changelog entries under the unreleased section; the developer does not edit CHANGELOG.md.

- The report lists, per change, the old and new text and where an adopter sees it: usage-line metavars and the missing-argument parameter name from typer 0.27, any validation message from pydantic 2.14, any lock-file behaviour from filelock 4.
- Also report the raised minimum versions, since an adopter pinning an older typer, filelock or pydantic can no longer install.
- A change kept identical by code is not reported.
<!-- sq:subtask:ST6:body:end -->

#### Discussion

<!-- sq:subtask:ST6:discussion -->
<!-- sq:subtask:ST6:discussion:end -->
<!-- sq:subtask:ST6:end -->

<!-- sq:subtask:ST7 -->
### ST7 — Surface test for the unknown-option suggestion (BUG-1192)

<!-- sq:subtask:ST7:body -->
An unknown option on a command prints the suggestion as plain text (No such option: --slug (Possible options: --as)), not a Python tuple. typer 0.27.3 fixes the rendering; add a CLI surface test pinning the message and exit code 2, and check it fails under typer 0.26.7.
<!-- sq:subtask:ST7:body:end -->

#### Discussion

<!-- sq:subtask:ST7:discussion -->
<!-- sq:subtask:ST7:discussion:end -->
<!-- sq:subtask:ST7:end -->
<!-- sq:subtasks:end -->

## Discussion

<!-- sq:discussion -->
- [2026-10-29T16:24:43Z] `tech-lead` Olivia Lead:
  - Planned 2026-10-29: one task, six subtasks (ST1-ST4, ST6 on US1; ST5 on US2), left Draft. Versions measured with uv lock --upgrade --dry-run; typer, filelock and ruff changes probed under both versions. The released 0.18.0 uv tool on the reference host already resolves typer 0.27.3, filelock 4.2.4, pydantic 2.14.1, anyio 4.15.1. Expected new tests: 4 (index lock). TASK-1218 now depends on this task.
- [2026-10-29T16:42:45Z] `op-pierre` Pierre Chat:
  - 2026-10-29: accept the new messages and usage text the upgraded dependencies print (typer 0.27 included); no metavar= workarounds to keep the old wording. List each change for the changelog. This task also carries the BUG-1192 surface test.
<!-- sq:discussion:end -->
