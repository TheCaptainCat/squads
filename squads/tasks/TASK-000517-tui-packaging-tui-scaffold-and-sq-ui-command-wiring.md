---
id: TASK-517
sequence_id: 517
type: task
title: TUI packaging, _tui scaffold, and sq ui command wiring
status: InReview
parent: FEAT-513
author: tech-lead
assignee: python-dev
subentities:
- local_id: ST1
  title: Launchable, cleanly-quitting sq ui shell + missing-extra guard
  status: Done
  story: US1
created_at: '2026-07-21T09:18:48Z'
updated_at: '2026-07-21T11:26:57Z'
---
<!-- sq:body -->
## Scope

Foundation for the whole `sq ui` increment: add the optional TUI dependency, create the
presentation package, and wire `sq ui` as a thin command that resolves the squad, guards the
missing extra, and launches a minimal full-screen app that quits cleanly. No tree, no reader
panel yet — just a launchable, quittable shell that later tasks fill in.

## What to build

1. **Optional `tui` extra** in `pyproject.toml` under `[project.optional-dependencies]`:
   declare Textual with a **floor pin, no ceiling** (`textual>=<floor>`). Set the exact floor
   to the lowest Textual release that ships the `Tree`, `TabbedContent`, and `Markdown` widgets
   this increment uses, verified against the version resolved in this repo — do not guess a
   round number. Textual stays out of core `dependencies`; `uv sync` (no extras) must not pull
   it, `uv sync --extra tui` must.

2. **New private package `squads/_tui/`** — a presentation layer that sits at the same level as
   `_cli` and consumes `_services`. For this task it holds the Textual `App` subclass (a minimal
   full-screen app with a quit binding and a placeholder body) plus the package `__init__`. It
   may import from `_services` / `_models` / `_rendering` only; nothing in `_services` or below
   may import it. `textual` is imported at the top of `_tui` modules (that is fine — the package
   is only ever imported from inside the command body, see below), never at CLI import time.

3. **`sq ui` command** in a new `squads/_cli/_ui.py`, registered from `_cli/__init__.py`
   alongside the other command wiring. It is a **plain synchronous** Typer command (NOT wrapped
   in the async `command` bridge — Textual's `App.run()` owns its own asyncio loop, so routing it
   through `anyio.run` would nest loops and fail). The body does, in order:
   - resolve the active squad synchronously (`squads._paths.resolve(...)` / the same
     squad-resolution the other commands use), letting the normal not-a-squad `SquadsError`
     surface;
   - run the **missing-extra guard**: attempt the lazy `import textual` (and the `squads._tui`
     import that pulls it) inside a `try`, and on `ModuleNotFoundError` raise a `SquadsError`
     with an actionable one-line install hint (e.g. *"the sq ui terminal UI needs the optional
     'tui' extra — install it with `pip install squads[tui]`"*);
   - wrap the synchronous validation in `try/except SquadsError` → print the clean `error: …`
     message and `typer.Exit(1)` (no traceback), matching the CLI's existing error bridge
     behaviour;
   - then construct the app and call its blocking `.run()` **outside** any `anyio.run`.
   All `textual` / `_tui` imports happen **inside** this function — never at module top of
   `_ui.py` or `_cli/__init__.py`. `sq --help` and CLI startup must be byte-unaffected whether or
   not the extra is installed.

## Constraints (from ADR-516 — binding)

- In-process read layer only; no `sq … --json` subprocess. (No data access in this task yet, but
  set the package up to take a `Service` / resolved squad dir, not to shell out.)
- Read-only increment: no mutating service calls anywhere in `_tui`.
- Keep the import graph acyclic and the module-privacy convention (leading-underscore) intact.

## Acceptance (what the reviewer/QA checks)

- `uv run sq ui` in a squad opens a full-screen terminal app and quits cleanly (terminal
  restored, no leftover state, no traceback on normal exit).
- `uv run sq ui` outside a squad prints the normal not-a-squad `error: …` line and exits 1.
- With the extra **absent**, `sq ui` prints the one-line install hint as `error: …` and exits 1
  — never an `ImportError`/`ModuleNotFoundError` traceback. Assertable in a normal service/CLI
  test by monkeypatching `textual` to be unimportable.
- `sq --help` output and CLI import time are unchanged whether or not `tui` is installed;
  importing `squads._cli` does not import `textual`.
- Nothing under `_services` or lower imports `_tui`; a grep for imports of `_tui` outside
  `_cli`/`_tui` is empty.
- `uv run pyright && uv run ruff check . && uv run ruff format --check .` clean; `uv sync` with
  no extras does not install Textual.

## Story mapping

Satisfies **FEAT-513 / US1 — "Launch and quit cleanly"** (the launchable, cleanly-quitting shell
plus the missing-extra failure path). Add one subtask mapped `--story US1`.
<!-- sq:body:end -->

## Subtasks

_Add with `sq task 517 add-subtask "<title>"`; track with `sq task 517 subtask <n> update --status <Status>`._

<!-- sq:summary -->
| Subtask | Status | Assignee | Title | Story |
| --- | --- | --- | --- | --- |
| ST1 | Done |  | Launchable, cleanly-quitting sq ui shell + missing-extra guard | US1 |
<!-- sq:summary:end -->

<!-- sq:subtasks -->

<!-- sq:subtask:ST1 -->
### ST1 — Launchable, cleanly-quitting sq ui shell + missing-extra guard

<!-- sq:subtask:ST1:head -->
**Status:** 🟢 Done
**Implements:** US1 — Launch and quit cleanly
<!-- sq:subtask:ST1:head:end -->

<!-- sq:subtask:ST1:body -->
Add the tui extra (floor-pinned Textual), the squads/_tui package with a minimal full-screen App (quit binding + placeholder), and the plain-sync sq ui command in _cli/_ui.py that resolves the squad, runs the missing-extra guard (ModuleNotFoundError -> SquadsError install hint), and calls App.run() outside anyio.run. Done: sq ui launches/quits cleanly, missing-extra prints a clean one-line error + exit 1, sq --help unaffected.
<!-- sq:subtask:ST1:body:end -->

#### Discussion

<!-- sq:subtask:ST1:discussion -->
<!-- sq:subtask:ST1:discussion:end -->
<!-- sq:subtask:ST1:end -->
<!-- sq:subtasks:end -->

## Discussion

<!-- sq:discussion -->
- [2026-07-21T09:56:43Z] Catherine Manager:
  - CI gap to close as part of this foundation (devops): the new `tui` optional extra means both jobs in test.yml run `uv sync --frozen` with no extras — the lint job's pyright then can't resolve textual in src/squads/_tui/ + the TUI tests and fails, and the test job silently skips the importorskip-guarded TUI tests (feature unexercised in CI). Fix: `uv sync --frozen --all-extras` in both jobs; keep the test's importorskip for lean local runs. To be done at integration, sequenced after the dev hands off.
- [2026-07-21T10:01:10Z] Elias Python:
  - Built: tui extra (textual>=0.16.0, floor-verified via changelog for Tree/TabbedContent/Markdown), squads/_tui package (SquadsApp with quit binding), sq ui as a plain-sync command in _cli/_ui.py with the missing-extra guard (ModuleNotFoundError -> SquadsError, clean exit 1).
  - Verified: sq --help byte-identical with/without the extra (subprocess test); missing-extra and outside-a-squad paths give clean 'error: ...' + exit 1, no traceback (manually and via tests/cli/test_ui_command.py); uv sync (no extras) does not install textual, uv sync --extra tui does.
- [2026-07-21T11:26:57Z] Catherine Manager:
  - CI gap resolved: test.yml's lint + test jobs now `uv sync --frozen --all-extras` so pyright resolves textual and the TUI tests actually run in CI (publish.yml untouched — core build needs no extra). tests/tui/ registered as a layer. Full-suite re-run in progress before commit.
<!-- sq:discussion:end -->
