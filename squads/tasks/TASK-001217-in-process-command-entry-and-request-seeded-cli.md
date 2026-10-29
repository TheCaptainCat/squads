---
id: TASK-1217
sequence_id: 1217
type: task
title: In-process command entry and request-seeded CLI
status: InProgress
parent: FEAT-1140
author: tech-lead
assignee: python-dev
priority: high
refs:
- ADR-1052:implements
description: One argv-to-exit-code entry, per-invocation consoles, directory, attachments
  and context from the request; invisible in local mode
subentities:
- local_id: ST1
  title: One argv-to-exit-code entry
  status: Todo
  story: US10
- local_id: ST2
  title: Consoles built per invocation
  status: Todo
  story: US10
- local_id: ST3
  title: Directory, attachments and context from the request
  status: Todo
  story: US10
- local_id: ST4
  title: Prompt sites signal needs_terminal before any write
  status: Todo
  story: US1
created_at: '2026-10-28T14:08:40Z'
updated_at: '2026-10-28T18:23:37Z'
---
<!-- sq:body -->
## Goal

Make the CLI runnable as one in-process request, so the daemon can run any command exactly as one local invocation does (ADR-1052, Consequences, first bullet; point 12). Nothing here is visible in local mode: the full suite passes unchanged and no adopter-facing behaviour moves.

## What it builds

- **One argv-to-exit-code entry.** A function that takes the arguments after `sq` and returns the exit code, wrapping today's `_hoist_global_options` + `app()` in `src/squads/_cli/__init__.py::main` (exit codes from `SystemExit`, click's usage errors, `@handle_errors`). `squads.__main__:main` and the daemon both call it.
- **Consoles built per invocation.** `console` / `err_console` in `src/squads/_cli/_common.py` are module-level `Console()` objects built at import; they become per-invocation objects built from the current stdio and environment (`NO_COLOR`, `FORCE_COLOR`, `TERM`, `COLORTERM`, `COLUMNS`, `LINES`) and the terminal facts. Every call site keeps reaching them through one accessor. `--json` output through `print()`/`print_json_clean` keeps writing to the current `sys.stdout`.
- **Request-seeded context.** `RequestContext` (`src/squads/_context.py`) gains defaulted fields for the client directory the request starts from, the attachments (name to content, stdin included), the terminal facts and the documents loaded at daemon start. `effective_dir` stops reading `Path.cwd()` when the seeded context carries a client directory (`_paths.process_dir()` is its local-mode source); `-C` keeps resolving against it.
- **`client_path` serving attachments.** `_read_source_file` and the import-file read (`src/squads/_cli/_import.py`) read from the attachments when the context carries them, `-` included (today `sys.stdin.read()` in `_common.py` and `_import.py`); a path that is not attached is refused with a `SquadsError` naming it. Local mode keeps reading the filesystem.
- **Root callback derives from the seeded context.** `main_callback` builds the invocation's `RequestContext` from the seeded one (client directory, attachments, terminal facts, documents) instead of from defaults; with nothing seeded it behaves as today, including the clock override carried by `_resolve_clock_override`. `actor.session_from_env()` keeps reading the environment, which the daemon's scope sets per command.
- **Prompt sites signal instead of asking when no terminal is available to the request.** The four `typer.confirm` / `typer.prompt` sites (item and sub-entity removal in `_cli/_items.py`, comment removal in `_cli/_common.py`, `init` in `_cli/_main.py`) go through one helper that, in a request that carries no client terminal, raises a dedicated signal the daemon turns into `needs_terminal`. Each site asks before it writes; a test pins that ordering per site.

## Acceptance

- US10, first bullet: one entry, consoles per invocation, directory from the request (`-C` included), attachments served from the request, root callback deriving from the request; nothing from one command visible to the next (clock, actor, context, environment, output).
- US1: a file the command names is read from the attachments; an unattached path is refused with a clear error.
- Local mode unchanged: full suite green with no golden or test expectation edited.
- `tests/meta` guards still pass (mutable-state inventory: removing the import-time consoles shrinks it; the import-edge table records any new edge).

## Test approach

- Table-driven isolation test: run pairs of commands through the entry in one process, the first setting each carried value (`--at`, `--as`/actor, `-C`, an env variable, a console width, a written `--json` document) and the second asserting none of it leaks. Falsify by keeping one module-level console and one carried field, and watch the matching rows go red.
- Attachments table: `--file` relative / absolute / `-` / unattached / attached-but-different-path, for each command that reads a file (body, comment, import); falsify by letting `client_path` fall through to the filesystem.
- Prompt ordering: one row per prompting site asserting no write precedes the prompt.
- Derive the extra test selection from the diff (template/console names grep across `tests/`) and run the `_cli/` floor: `tests/meta`, `tests/integration`, `tests/cli`.
<!-- sq:body:end -->

## Subtasks

_Add with `sq task 1217 add-subtask "<title>"`; track with `sq task 1217 subtask <n> update --status <Status>`._

<!-- sq:subtasks -->

<!-- sq:subtask:ST1 -->
### ST1 — One argv-to-exit-code entry

<!-- sq:subtask:ST1:body -->
Wrap `_hoist_global_options` + `app()` from `_cli/__init__.py::main` in one function from argv to an exit code (SystemExit, click usage errors, `@handle_errors`), called by `squads.__main__:main` and later by the daemon. Local exit codes unchanged on the whole suite.
<!-- sq:subtask:ST1:body:end -->

#### Discussion

<!-- sq:subtask:ST1:discussion -->
<!-- sq:subtask:ST1:discussion:end -->
<!-- sq:subtask:ST1:end -->

<!-- sq:subtask:ST2 -->
### ST2 — Consoles built per invocation

<!-- sq:subtask:ST2:body -->
Replace the import-time `console`/`err_console` in `_cli/_common.py` with per-invocation consoles built from the current stdio, the listed env variables and the terminal facts, reached through one accessor. Shrinks the mutable-state inventory in `tests/meta`. Falsify with one console left at import: the width/colour isolation rows go red.
<!-- sq:subtask:ST2:body:end -->

#### Discussion

<!-- sq:subtask:ST2:discussion -->
<!-- sq:subtask:ST2:discussion:end -->
<!-- sq:subtask:ST2:end -->

<!-- sq:subtask:ST3 -->
### ST3 — Directory, attachments and context from the request

<!-- sq:subtask:ST3:body -->
Defaulted `RequestContext` fields for client directory, attachments, terminal facts and preloaded documents; `effective_dir` starts from the seeded directory; `client_path`/`_read_source_file`/the import read serve attachments (stdin included) and refuse an unattached path; `main_callback` derives its context from the seeded one. Table over file-reading commands x path shapes; isolation pairs over clock, actor, `-C`, env, output.
<!-- sq:subtask:ST3:body:end -->

#### Discussion

<!-- sq:subtask:ST3:discussion -->
<!-- sq:subtask:ST3:discussion:end -->
<!-- sq:subtask:ST3:end -->

<!-- sq:subtask:ST4 -->
### ST4 — Prompt sites signal needs_terminal before any write

<!-- sq:subtask:ST4:body -->
Route the four `typer.confirm`/`typer.prompt` sites (item, sub-entity and comment removal, `init`) through one helper that raises a dedicated signal when the request carries no client terminal. One test row per site pins that the prompt comes before any write.
<!-- sq:subtask:ST4:body:end -->

#### Discussion

<!-- sq:subtask:ST4:discussion -->
<!-- sq:subtask:ST4:discussion:end -->
<!-- sq:subtask:ST4:end -->
<!-- sq:subtasks:end -->

## Discussion

<!-- sq:discussion -->
<!-- sq:discussion:end -->
