---
id: TASK-1262
sequence_id: 1262
type: task
title: 'Daemon command endpoint: CLI commands served in process'
status: InProgress
parent: FEAT-1140
author: tech-lead
assignee: python-dev
refs:
- ADR-1261:implements
description: 'POST /v1/commands on the CLI listener: served execution on the daemon''s
  LocalApi, stdio and env proxies, attachments, two-phase prompts, endpoint and route
  parity modes'
subentities:
- local_id: ST1
  title: Endpoint route, request and answer, admission
  status: Todo
  maps_to: US3
- local_id: ST2
  title: Served execution on the daemon's own LocalApi
  status: Todo
  maps_to: US3
- local_id: ST3
  title: Per-request consoles, stdio and environment proxies
  status: Todo
  maps_to: US10
- local_id: ST4
  title: Attachments and stdin served from the request
  status: Todo
  maps_to: US1
- local_id: ST5
  title: Two-phase prompts, nothing written before the answer
  status: Todo
  maps_to: US3
- local_id: ST6
  title: Endpoint and route parity modes for tests/cli
  status: Todo
  maps_to: US3
created_at: '2026-10-30T20:30:24Z'
updated_at: '2026-10-30T20:36:32Z'
priority: high
---
<!-- sq:body -->
## Goal

The daemon side of ADR-1261: the private command endpoint `POST /v1/commands`, through which the daemon runs this installation's CLI in process on its own `LocalApi` and renders the output, with attachments, stdin and two-phase prompts, and the endpoint-parity harness that reruns `tests/cli` through it. The shim that calls it is the next task; until it lands, the CLI keeps its current remote mode, so this task changes nothing an adopter sees.

## Scope

- **The route** (ADR-1261 points 1, 2): `POST /v1/commands` on the CLI listener only (the Unix socket on POSIX, the CLI port on Windows), never on the browser port; absent from `GET /v1/openapi.json`; ADR-1052 point 5's admission rules apply. Request: `argv` (lone surrogates round-trip), `cwd`, `env`, `prog_name`, `terminal`, `attachments`, `answers`. Answer: `done` (`output` as ordered `[stream, text]` chunks, `exit_code`) or `prompt` (output so far, prompt text, digest). `503 {"not_executed": "retiring"}` stays the only refusal after which the client may run the command itself. The daemon's handler time goes back with the answer, as `Server-Timing` does on the routes.
- **Served execution** (point 2): the Typer app built once at daemon start-up; the daemon's `LocalApi` bound on the request's `RequestContext` before the root callback runs, reusing the normal-mode service composed at start-up and, per call, the schema grant, the composition mode and the read scope of ADR-1225 section 7. A served command runs on a worker thread inside the daemon's one serial lock for its whole run, parse to render. `select_api` refuses to run inside a served command. The squad is the daemon's: nothing walks up from `cwd` or reads a path the client names; `cwd` seeds `start_dir` for path spelling. Notices raised inside an operation print through the sink the root callback sets, which here is the request's stderr capture, in local mode's order.
- **Process state** (point 2, fact 7): per-request consoles built from `terminal`; `sys.stdin`, `sys.stdout` and `sys.stderr` replaced once at start-up by proxies that write to the current request's capture (accepting `bytes` as well as `str`) and read from its answers, and fall back to the daemon's log outside a request; `os.environ` replaced once by a proxy where a name on the fixed list reads the request's `env` (absent when not sent) and every other name the daemon's own. The fixed list is the literal of ADR-1261 point 1; it lives in the shim's module (next task), so this task reads it from one module the shim will own (create it here with only the literal, stdlib only). Every `squads` module that reads an environment variable at import time moves the read to first use (`_spans` and `SQUADS_SPANS` first).
- **Attachments and stdin** (point 3, daemon side): `read_client_text` serves an attachment keyed by the argument exactly as written and decodes it as local mode does (UTF-8, the same refusal text); a name the request does not carry is an internal error; `-` is decoded with the client's stdin encoding, and a prompt later in the same command reads end of input and aborts.
- **Prompts** (point 5): a served command reaching `confirm` with no matching answer stops and answers `prompt`; the digest covers the output written before the prompt plus its text; an answer is fed only to a prompt reached with the same digest, otherwise `prompt` again with the full new output; on a match the answer leaves out the output already shown; an invalid line comes back as another `prompt` with Click's error text. A prompt reached after a non-`GET` operation ran in the same request is an internal error. The `prompt` answer says which stream the prompt text belongs to (Click writes it to stderr under `--json`).
- **Parity modes** (point 9): `--api-mode remote` (`SQUADS_TEST_MODE=remote`) now sends each `invoke` case's `argv` to the daemon application served on a thread of the test process against the copied squad and builds the result from the chunks and the exit code; `--api-mode routes` keeps today's harness, an `HttpApi` handed to the root callback. Both compose with `--squad override`; no case is skipped. What the fixtures set on the test's context (the frozen clock, the plain-output environment, the empty starting directory) must reach the served command through the request or the harness, never through the daemon reading the test process's own state; build the Typer app once per squad module, not per case, or the run will not fit ADR-1172's 10-minute bound.

## Hazards the developer resolves and reports

- The stdio and `os.environ` proxies installed in the pytest process must not disturb `CliRunner`'s capture or pytest's: install them through the same start-up step the harness calls, with the original streams as the outside-a-request fall back.
- The tests/meta guard that forbids stdout and stderr writes outside `_cli`, `_tui`, `squads.__main__` and `_spans` must admit the proxies' module and the shim's module by name, nothing broader.
- `-C` in a served command: the shim has already resolved it to reach this daemon; the daemon applies it to `cwd` only to spell paths, and never stats a path a TCP caller named (ADR-1052 point 6). If that is not possible without a filesystem read, stop and ask @architect.

## Modules touched

`src/squads/_daemon/` (a new module for the endpoint and served execution, `_app.py`, `_listeners.py`, `_admission.py`, `_state.py`), `src/squads/_context.py`, `src/squads/_cli/__init__.py` (root callback in a served command), `src/squads/_cli/_common.py` (`read_client_text`, `confirm`, consoles), `src/squads/_cli/_calls.py` (`select_api` refusal), `src/squads/_spans.py`, the root `conftest.py` and `tests/conftest.py` (the two parity modes), `tests/daemon/`, `tests/meta/`. The prototype at commit 046144f7 (branch `worktree-agent-ab8070e632116d3ff`, `src/squads/_daemon/_commands.py`) is a reference only: it skipped tests and the import-edge guards; do not merge it.

## Acceptance

- ADR-1261 points 1, 2, 3 (daemon side) and 5, and point 9's endpoint parity, endpoint tests and the two guards below.
- `uv run --all-extras pytest --api-mode remote tests/cli` and the same with `--squad override` pass with no case skipped; `--api-mode routes tests/cli` passes as today's remote run does.
- Every new package-to-package import edge is a row in `tests/meta/test_package_import_edges_match_the_recorded_table.py`.
- Gates: `uv run --all-extras pyright`, `uv run --all-extras ruff check .`, `uv run --all-extras ruff format --check .`, `uv run --all-extras pytest -n 6` (one full run, to a file), `--api-mode remote tests/cli`, `--api-mode remote --squad override tests/cli`, `--api-mode routes tests/cli`, `-n0 tests/cross_process`, `python scripts/gen_template_manifest.py --check`, `~/.local/bin/sq check` clean.

## Test approach (ADR-1172)

- Endpoint parity: the existing `tests/cli` cases through the endpoint; no new case, none skipped. Falsify: drop one `env` name from the request, print one line from the daemon side outside the capture, reorder two chunks; each turns remote-mode cases red.
- Endpoint tests in `tests/daemon/`, rules 4-6, no `covers` marker, whole answer asserted, state read back through `show --json`: completion answering local mode's candidates for bash, zsh and fish (3); stdout and stderr chunks in local mode's order (1); an unattached file name refused (1); stdin attached under `-` (1); a prompt answered, refused, given an invalid line, and a changed screen between the phases (4); a prompt reached after a write refused (1; no CLI command reaches it, so the harness serves an app carrying one test-only command that writes and then confirms: confirm with @architect before building it); the browser port refusing the endpoint (1); `503 retiring` on the endpoint (1). 13 tests.
- Guards (2): the endpoint's modules import neither `squads._cli._remote`, `http.client` nor `subprocess`; no `squads` module reads an environment variable at import time. Show each red against a planted violation.
- Expected: 13 tests, 2 guards.
- Order: first of the chain; runs in parallel with the parse-cache task. The shim task depends on this one.
<!-- sq:body:end -->

## Subtasks

_Add with `sq task 1262 add-subtask "<title>"`; track with `sq task 1262 subtask <n> update --status <Status>`._

<!-- sq:subtasks -->

<!-- sq:subtask:ST1 -->
### ST1 — Endpoint route, request and answer, admission

<!-- sq:subtask:ST1:body -->
`POST /v1/commands` on the CLI listener only (Unix socket on POSIX, CLI port on Windows), never on the browser port; absent from `GET /v1/openapi.json`; ADR-1052 point 5's admission rules. Request and answer as ADR-1261 point 1 states them (`done` with ordered `[stream, text]` chunks and `exit_code`, or `prompt`); `503 {"not_executed": "retiring"}` unchanged; the handler time sent back with the answer.

Tests: the browser port refusing the endpoint (1); `503 retiring` on the endpoint (1). The `done` and `prompt` kinds are asserted by ST5 and the parity run.
<!-- sq:subtask:ST1:body:end -->

#### Discussion

<!-- sq:subtask:ST1:discussion -->
<!-- sq:subtask:ST1:discussion:end -->
<!-- sq:subtask:ST1:end -->

<!-- sq:subtask:ST2 -->
### ST2 — Served execution on the daemon's own LocalApi

<!-- sq:subtask:ST2:body -->
The Typer app built once at daemon start-up; the daemon's `LocalApi` bound on the request's `RequestContext` before the root callback (schema grant, composition mode, read scope per call, ADR-1225 section 7); a worker thread inside the serial lock for the whole run; `select_api` refuses inside a served command; the squad is the daemon's, `cwd` seeds `start_dir` only; notices raised inside an operation print through the request's stderr sink in local mode's order.

Tests: the parity run (ST6) and completion for bash, zsh and fish answering local mode's candidates (3). Guard: the endpoint's modules import neither `squads._cli._remote`, `http.client` nor `subprocess` (1).
<!-- sq:subtask:ST2:body:end -->

#### Discussion

<!-- sq:subtask:ST2:discussion -->
<!-- sq:subtask:ST2:discussion:end -->
<!-- sq:subtask:ST2:end -->

<!-- sq:subtask:ST3 -->
### ST3 — Per-request consoles, stdio and environment proxies

<!-- sq:subtask:ST3:body -->
Per-request consoles from `terminal`; `sys.stdin`/`stdout`/`stderr` replaced once at start-up by proxies writing to the current request's capture (`bytes` and `str`) and reading its answers, falling back to the daemon's log outside a request; `os.environ` replaced once by a proxy reading the request's `env` for a name on the fixed list (the literal of ADR-1261 point 1, in the shim's module, stdlib only) and the daemon's own otherwise. Import-time environment reads (`_spans` first) moved to first use. The stdout/stderr-writes guard admits the proxies' and the shim's modules by name.

Tests: stdout and stderr chunks in local mode's order (1). Guard: no `squads` module reads an environment variable at import time (1). Session ids reaching the reflog are held by the parity run.
<!-- sq:subtask:ST3:body:end -->

#### Discussion

<!-- sq:subtask:ST3:discussion -->
<!-- sq:subtask:ST3:discussion:end -->
<!-- sq:subtask:ST3:end -->

<!-- sq:subtask:ST4 -->
### ST4 — Attachments and stdin served from the request

<!-- sq:subtask:ST4:body -->
Daemon side of ADR-1261 point 3: `read_client_text` serves an attachment keyed by the argument as written, decoded as local mode does (UTF-8, same refusal text); an unattached name is an internal error; `-` decoded with the client's stdin encoding, and a later prompt in the same command reads end of input and aborts. The daemon never reads a path the client names.

Tests: an unattached name refused (1); stdin attached under `-` (1).
<!-- sq:subtask:ST4:body:end -->

#### Discussion

<!-- sq:subtask:ST4:discussion -->
<!-- sq:subtask:ST4:discussion:end -->
<!-- sq:subtask:ST4:end -->

<!-- sq:subtask:ST5 -->
### ST5 — Two-phase prompts, nothing written before the answer

<!-- sq:subtask:ST5:body -->
ADR-1261 point 5, daemon side: `confirm` with no matching answer answers `prompt` (output so far, text, the stream it belongs to, digest of output plus text); an answer feeds only a prompt reached with the same digest, else `prompt` again with the full new output; on a match the answer leaves out what was shown; an invalid line answers `prompt` with Click's error; a prompt reached after a non-`GET` operation in the same request is an internal error.

Tests: a prompt answered, refused, given an invalid line, and a changed screen between the phases (4); a prompt after a write refused (1), through a test-only command in the harness app, confirmed with the architect before it is built.
<!-- sq:subtask:ST5:body:end -->

#### Discussion

<!-- sq:subtask:ST5:discussion -->
<!-- sq:subtask:ST5:discussion:end -->
<!-- sq:subtask:ST5:end -->

<!-- sq:subtask:ST6 -->
### ST6 — Endpoint and route parity modes for tests/cli

<!-- sq:subtask:ST6:body -->
`--api-mode remote` sends each `invoke` case's `argv` to the daemon application served on a thread against the copied squad and builds the result from the chunks and exit code; `--api-mode routes` keeps today's `HttpApi` hand-in. Both compose with `--squad override`, no case skipped. The fixtures' context (frozen clock, plain-output environment, empty starting directory) reaches the served command through the request or the harness, never through the daemon reading the test process. The Typer app is built once per squad module, so the run fits the 10-minute bound.

Tests: no new case. Falsify: drop one `env` name, print one line outside the capture, reorder two chunks; each turns remote-mode cases red.
<!-- sq:subtask:ST6:body:end -->

#### Discussion

<!-- sq:subtask:ST6:discussion -->
<!-- sq:subtask:ST6:discussion:end -->
<!-- sq:subtask:ST6:end -->
<!-- sq:subtasks:end -->

## Discussion

<!-- sq:discussion -->
<!-- sq:discussion:end -->
