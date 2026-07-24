---
id: TASK-639
sequence_id: 639
type: task
title: 'sq import CLI: --dry-run, --json, --at/--as'
status: Done
parent: FEAT-576
author: tech-lead
refs:
- ADR-622:implements
description: 'Top-level sq import file (- reads stdin): --dry-run (pre-pass only,
  print handle to id plan + per-op counts), --json, file-level --at/--as defaults,
  --dir.'
created_at: '2026-07-23T13:29:38Z'
updated_at: '2026-07-24T07:42:43Z'
---
<!-- sq:body -->
The `sq import` command surface defined in ADR-622 ("CLI surface"). Thin wiring over the event-model/pre-pass task and the apply task — no new import logic lives here.

## Scope

Top-level `sq import <file>` (attached to the Typer `app` in `_cli/__init__.py`, alongside the other top-level commands; a new `_cli/_import.py` module). `<file>` of `-` reads the JSONL stream from stdin.

Flags (exactly ADR-622's set):
- `--dry-run` — run the validate pre-pass only, write nothing, print the projected `handle -> id` plan and per-op counts.
- `--json` — structured result: per-op counts, the resolved `handle -> id` map, and the ordered error list on failure.
- `--at` / `--as` — supply the file-level defaults events inherit when they omit their own (feeds the pre-pass task's inheritance rule).
- `--dir` — the usual squad selector (via the root callback, same as every command).

Behaviour:
- On any validation error: exit non-zero, write nothing, and list **every** error with its line number (the pre-pass already collects them all — render them in order).
- On success (non-dry-run): render per-op counts and the `handle -> id` map.
- Human output and `--json` output are two renderings of the same result object the pre-pass/apply tasks return — do not recompute anything in the CLI.

## Where it plugs in
- Register on the top-level `app` in `_cli/__init__.py` (see how the top-level commands are attached there); shared console/error-decorator/parsers in `_cli/_common.py`.
- Wrap failures in the `@handle_errors` decorator so a `SquadsError` becomes a clean message + exit 1.

## Conventions (must hold)
- Escape every dynamic/content string with `_cli._common.e()` before printing to the console or a table (Rich treats `[...]` as markup — file paths, titles, error text).
- `--json` must emit clean JSON with no ANSI (the harness sets `FORCE_COLOR`; tests strip it, but the command must not embed escapes in JSON).
- No status/lifecycle prose. Category is "roster". No ticket/sq IDs in source or test names. `SquadsError` family for user-facing errors. `B008` is why Typer `Option`/`Argument` call-defaults are allowed under `_cli/`.

## Testing / gates
- Gates: `uv run --all-extras pyright && uv run --all-extras ruff check . && uv run --all-extras ruff format --check .`.
- If you add ANY module-level constant, run `tests/meta` (mutable-state guard).
- CLI smoke tests with `typer.testing.CliRunner`: a clean file applies and reports counts; `--dry-run` writes nothing and prints the plan; a file with seeded errors exits non-zero, writes nothing, and lists every error with its line number; `--json` shape is asserted; stdin (`-`) path; `--at`/`--as` defaults flow through.
- `uv run sq check` clean before finishing.
<!-- sq:body:end -->

## Subtasks

_Add with `sq task 639 add-subtask "<title>"`; track with `sq task 639 subtask <n> update --status <Status>`._

<!-- sq:summary -->
<!-- sq:summary:end -->

<!-- sq:subtasks -->
<!-- sq:subtasks:end -->

## Discussion

<!-- sq:discussion -->
- [2026-07-24T07:33:43Z] Elias Python:
  - Landed: new _cli/_import.py wraps Service.import_events — sq import <file> ('-' = stdin), --dry-run (pre-pass only, prints handle->id plan + op counts, writes nothing), --json (ok/applied/dry_run/op_counts/handle_to_id/handle_to_sub/issues/created_ids/warnings), --as (file-level actor default, falls through to config default_role). --at reuses the existing global --at (root-level clock override) rather than a redundant local flag, since the CLI's own arg-hoisting always routes a bare --at to root anyway; documented in the command's own help.
  - Validation issues print line-numbered, non-traceback, exit 1, nothing written. CLI tests: tests/cli/test_import_cli.py (clean apply, dry-run, seeded errors, stdin, --json shape both success/failure, --at/--as flow-through, unreadable file). Gates green (pyright/ruff/format), tests/meta green, sq check clean.
<!-- sq:discussion:end -->
