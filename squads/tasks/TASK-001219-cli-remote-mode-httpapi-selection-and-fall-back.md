---
id: TASK-1219
sequence_id: 1219
type: task
title: 'CLI remote mode: HttpApi, selection and fall back'
status: Draft
parent: FEAT-1140
author: tech-lead
priority: high
refs:
- ADR-1052:implements
- TASK-1218:depends-on
- ADR-1225:implements
- TASK-1233:depends-on
description: Root callback picks HttpApi or LocalApi; implicit start, conditional
  fall back, timeouts, schema and vocabulary headers, client budget and guard, parity
  run, the TUI as a daemon client
subentities:
- local_id: ST1
  title: API selection in the root callback
  status: Todo
  story: US3
- local_id: ST2
  title: Implicit start, discovery and failed start
  status: Todo
  story: US4
- local_id: ST3
  title: Native Windows client path
  status: Todo
  story: US6
- local_id: ST4
  title: HttpApi requests, headers and errors
  status: Todo
  story: US10
- local_id: ST5
  title: Fall back, no replay, timeouts and Ctrl-C
  status: Todo
  story: US3
- local_id: ST6
  title: Mode parity run over HttpApi
  status: Todo
  story: US3
- local_id: ST7
  title: Schema and vocabulary headers, client side
  status: Todo
  story: US11
- local_id: ST8
  title: 'Client budget: levers, import guard, benchmark'
  status: Todo
  story: US12
- local_id: ST9
  title: The terminal UI as a daemon client
  status: Todo
  story: US13
created_at: '2026-10-28T14:08:42Z'
updated_at: '2026-10-28T22:25:06Z'
---
<!-- sq:body -->
## Goal

Remote mode (ADR-1225 section 10, D2): the CLI itself calls the daemon through `HttpApi`, chosen once per invocation by the root callback, with implicit start, the conditional fall back, timeouts, the schema and vocabulary headers, the client budget and its guard, the mode-parity run, and the terminal UI as a daemon client. This is the task that turns the daemon on for adopters. A command not yet on an operation runs locally, so remote mode can be trialled with `SQUADS_DAEMON=on` as soon as this lands.

## What it builds

- **API selection** (ADR-1225 section 5, ADR-1052 point 9) — ST1. The root callback calls TASK-1218's endpoint resolution and puts `HttpApi` or `LocalApi` on `RequestContext`. Commands that make no call (`docs`, `migrate help`, `migrate chlog`, `--version`, `--help`, completion) never contact or start a daemon; nor do `init`, `adopt` (`local_only`) and `daemon`. With no squad found, the command fails with today's message. On the remote path the CLI reads only what ADR-1225 section 5 lists: `squad_dir` and `[daemon]` of `.squads.toml`, and the bundled and override `workflow.toml` for parsing; the override's cross-check against the index, the schema gate and the working-language notice are the daemon's. Local mode keeps them where they are.
- **Implicit start and discovery** (ADR-1052 points 8, 11) — ST2. Find a live daemon by key (POSIX: connect to `<key>.sock`; Windows: `<key>.json` then `GET /v1/daemon` with the pid and squad-path check); a socket refusing connections while the lock is free is a dead daemon whose files are removed; otherwise spawn `sys.executable -m squads daemon run` detached and wait at most 5 s for `ready`. A failed start (spawn error, failure line, no answer in 5 s, unusable runtime directory) runs the command locally with one stderr line giving the reason and how to turn the daemon off; the next command tries again.
- **Native Windows client** — ST3. Spawn flags, the loopback CLI port with no `Origin` sent, the port-reuse identity check, `%LOCALAPPDATA%` runtime files.
- **`HttpApi` requests and errors** (ADR-1225 sections 2, 3) — ST4. `http.client` over the Unix socket or loopback TCP, one request per call, using TASK-1227's wire helpers: path and query or JSON body from the request DTO, headers from `RequestContext` (`Squads-Actor`, `Squads-At`, `Squads-Session-Id`, `Squads-Parent-Session-Id`, `Squads-Client-Dir`, `Squads-Schema`, `Squads-Vocabulary`, `Squads-Client: 1`), `Response[Res]` parsed and validated, an error body turned back into a `SquadsError` with the daemon's message so `@handle_errors` prints it and exits 1.
- **Fall back, no replay, timeouts, Ctrl-C** (ADR-1225 sections 3, 5; ADR-1052 point 10) — ST5. Against an endpoint with a local mode, `503 retiring` reruns the call on `LocalApi` silently, and an unreachable or unstartable daemon gives way to `LocalApi`. Against one without (the FEAT-33 seam), `503 retiring` is retried once against the re-resolved endpoint, then fails with the "is restarting" message; an unreachable server fails with the "cannot reach" message; nothing runs locally. A connection lost after sending is an error, never replayed. Timeouts from the operation's class: `standard` 5 s connect and 300 s answer, `long` 5 s connect and no answer timeout with the `waiting for the daemon (<operation>)…` notice after 10 s. A timeout or Ctrl-C ends only the wait, with the "may still complete" message, exit 1 or 130; a connect timeout is an unreachable daemon.
- **Mode parity** (ADR-1172 "Mode parity", ADR-1225 section 5) — ST6. A run-wide remote mode of the `invoke` fixture that sends every surface case through `HttpApi` against TASK-1218's application served in-process. The root `conftest.py` sets `SQUADS_DAEMON=off` for every test that does not exercise the daemon. TASK-1220 runs it as its own CI job.
- **Vocabulary hash and schema, client side** (ADR-1225 sections 3, 5) — ST7. The client sends the hash of the documents it parsed with, from the same `spec_sources` bytes TASK-1218 introduces, and its `SCHEMA_VERSION`; it prints the client-behind, client-ahead and vocabulary messages of ADR-1225, naming the document that differs from the per-document digests; exit 1, no fall back. A `tests/meta` guard fails when the parser reaches a document the hash leaves out.
- **Client budget** (ADR-1225 section 5) — ST8. The levers: `gc.freeze()` once output is flushed, `gc.disable()` for start-up; a literal command-name table at the root importing only the invoked group's module (root `--help` still loads all), guarded against the registered tree; `__version__` without `importlib.metadata`; `anyio` confined to the service side; the spec loader path trimmed to what loading needs. The import guard: the remote path (root callback, `HttpApi`, the renderer) loads none of `squads._services`, `squads._index`, `jinja2`, `yaml`, `anyio`, `filelock`, `importlib.metadata`, `starlette`, `uvicorn`, nor `rich.markdown` before a body is rendered. A benchmark script measuring the client overhead (wall time minus `Server-Timing`) for `sq <type> <n> show`, median of 31 interleaved runs, human and `--json`; the release runbook (the `releasing-squads` skill) runs it on the reference host and records the numbers.
- **The terminal UI as a daemon client** (ADR-1224 point 7, ADR-1225 section 5) — ST9, on the selector seam TASK-1233 leaves.

## Modules touched

`src/squads/_cli/__init__.py` (selection, the command-name table, `gc` handling in `main`), `src/squads/__main__.py`, `src/squads/__init__.py` (`__version__`), `src/squads/_api/_http.py` and the client half of `_api`, the shared endpoint module of TASK-1218 (spawn and discovery on top of it), `src/squads/_tui/_app.py` (the selector), the spec loader modules (trim), `tests/conftest.py`, the root `conftest.py`, `tests/meta/` (budget import guard, command-name table guard, vocabulary-document guard), a new cross-process test directory, a benchmark script under `scripts/`, the `releasing-squads` skill body. Depends on TASK-1218 (the application, endpoint resolution, the hash) and TASK-1233 (the TUI seam).

## Acceptance

- FEAT-1140 US3 in full, US4 (implicit start, discovery, staleness, simultaneous starts on one daemon), US6 client side, US10 (metadata sent with each call), US11 client side, US12, US13.
- Feature acceptance bullets 1-6, 9, 10 and the client budget bullet: at most 275 ms human and 235 ms `--json` on the reference host, measured and recorded.
- ADR-1225 sections 2, 3, 5 and 10 (D2); ADR-1052 points 9-11 as amended.

## Test approach (ADR-1172)

- Parity: the existing surface suite rerun in remote mode in its own CI job (TASK-1220). No new cases.
- Cross-process set, exactly ADR-1172's members, real `sq` against a scratch squad, whole output asserted, state read through `show --json`: implicit start, discovery, fall back, no replay, Ctrl-C, detached spawn on Windows. 6 tests.
- Surface cases in remote mode (in-process, `HttpApi` against the served application, whole stderr and exit code): client behind, client ahead, vocabulary mismatch naming the document. 3 tests.
- Guards: budget import, command-name table, vocabulary documents. 3.
- Built and not tested: idle exit, simultaneous starts, staleness cleanup, the 300 s timeout and the 10 s waiting notice, and the hosted-squad branches (no endpoint without a local mode exists in 0.18). See "Left open".
- Expected total: 9 tests and 3 guards; the benchmark is a report, not a test.

## Left open

- **Timeouts and the waiting notice untested.** A case would wait 10 s or more, or need a test-only delay hook. Recommendation: build them untested, as idle exit is, and say so on ADR-1225.
- **Hosted-squad branches unreachable.** Nothing in 0.18 produces an `Endpoint` without a local mode, so the retry-once and "cannot reach" paths have no surface. Recommendation: build them behind the `Endpoint` flag untested; FEAT-33 tests them when it adds the source.
- **The TUI remote behaviours** (ST9) have no automated surface either; recommendation as on TASK-1233: the operator's check in a session against the daemon.
<!-- sq:body:end -->

## Subtasks

_Add with `sq task 1219 add-subtask "<title>"`; track with `sq task 1219 subtask <n> update --status <Status>`._

<!-- sq:subtasks -->

<!-- sq:subtask:ST1 -->
### ST1 — API selection in the root callback

<!-- sq:subtask:ST1:body -->
The root callback resolves the endpoint once per invocation (TASK-1218's shared module) and puts `HttpApi` or `LocalApi` on `RequestContext` (ADR-1224 point 4, ADR-1225 section 5). Never contacted or started: commands that make no call (`docs`, `migrate help`, `migrate chlog`, `--version`, `--help`, completion), `local_only` operations (`init`, `adopt`) and the `daemon` group. No squad found: today's message. On the remote path the client reads only `squad_dir` and `[daemon]` from `.squads.toml` and the two `workflow.toml` documents for parsing; the index cross-check of the override, the schema gate and the working-language notice come from the daemon (as its error or a `warnings` entry). In local mode they stay where they are, so local output is unchanged.

Tests: the selection itself is observed through the parity run (ST6) and the implicit-start and fall back members (ST2, ST5). No new case.
<!-- sq:subtask:ST1:body:end -->

#### Discussion

<!-- sq:subtask:ST1:discussion -->
<!-- sq:subtask:ST1:discussion:end -->
<!-- sq:subtask:ST1:end -->

<!-- sq:subtask:ST2 -->
### ST2 — Implicit start, discovery and failed start

<!-- sq:subtask:ST2:body -->
Find a live daemon for the key (POSIX: connect to `<key>.sock`; TCP: read `<key>.json`, then `GET /v1/daemon` and check pid and squad path, since a port can be reused). A socket refusing connections while `<key>.lock` is free is a dead daemon: remove its files. Otherwise spawn `sys.executable -m squads daemon run` detached (new session on POSIX) and wait at most 5 s for `ready` or the failure line. Two clients spawning at once both end on the winner. A failed start (spawn error, failure line, no answer in 5 s, unusable runtime directory) runs the command locally with one stderr line giving the reason and how to turn the daemon off; the next command tries again (ADR-1052 points 8, 11).

Tests: two members of the cross-process set (ADR-1172): implicit start (a first command on a cold key starts a daemon that `sq daemon status --json` then reports) and discovery (a second command is answered by the same pid). Simultaneous starts and staleness cleanup are built and not tested. 2 tests.
<!-- sq:subtask:ST2:body:end -->

#### Discussion

<!-- sq:subtask:ST2:discussion -->
<!-- sq:subtask:ST2:discussion:end -->
<!-- sq:subtask:ST2:end -->

<!-- sq:subtask:ST3 -->
### ST3 — Native Windows client path

<!-- sq:subtask:ST3:body -->
Native Windows client path (ADR-1052 points 4, 8, 11): spawn with `DETACHED_PROCESS`, `CREATE_NEW_PROCESS_GROUP`, `CREATE_NO_WINDOW`; reach the loopback CLI port, never sending an `Origin` header; the port-reuse identity check through `GET /v1/daemon`; runtime files under `%LOCALAPPDATA%`. The CLI's UTF-8 stdout and stderr reconfiguration at import applies unchanged, since rendering stays in the client.

Tests: the detached-spawn member of the cross-process set, Windows only: the daemon a command started still answers after that client's process group has ended. The other members run on the Windows job as on every OS (TASK-1220). 1 test.
<!-- sq:subtask:ST3:body:end -->

#### Discussion

<!-- sq:subtask:ST3:discussion -->
<!-- sq:subtask:ST3:discussion:end -->
<!-- sq:subtask:ST3:end -->

<!-- sq:subtask:ST4 -->
### ST4 — HttpApi requests, headers and errors

<!-- sq:subtask:ST4:body -->
`HttpApi` on `http.client`, one request per call over the Unix socket or loopback TCP, built on TASK-1227's wire helpers (ADR-1225 sections 2, 3): path and query from a flat `GET` request DTO, a UTF-8 JSON body otherwise; file text already in the DTO, nothing attached. Headers from the invocation's `RequestContext`: `Squads-Actor` (from `--as`), `Squads-At`, `Squads-Session-Id`, `Squads-Parent-Session-Id`, `Squads-Client-Dir` (the directory paths in messages are spelled from), `Squads-Schema`, `Squads-Vocabulary` (ST7), `Squads-Client: 1`. A `200` parses into `Response[Res]` through pydantic, so a disagreeing client and daemon fail at the boundary; an error body becomes a `SquadsError` carrying the daemon's message, printed by `@handle_errors` with exit 1 exactly as in local mode; `omitted` gives exit 4 after printing, as locally.

Tests: every operation's request and answer are the parity run (ST6); the binding of each header on the daemon side is TASK-1218 ST8. No new case.
<!-- sq:subtask:ST4:body:end -->

#### Discussion

<!-- sq:subtask:ST4:discussion -->
<!-- sq:subtask:ST4:discussion:end -->
<!-- sq:subtask:ST4:end -->

<!-- sq:subtask:ST5 -->
### ST5 — Fall back, no replay, timeouts and Ctrl-C

<!-- sq:subtask:ST5:body -->
Conditional fall back, no replay, timeouts and Ctrl-C (ADR-1225 sections 3 and 5, ADR-1052 point 10), driven by the `Endpoint`'s local-mode flag:
- local daemon: `503 retiring` reruns that call on `LocalApi` with no stderr line; an unreachable or unstartable daemon gives way to `LocalApi` (ST2's line);
- no local mode (the FEAT-33 seam): `503 retiring` is sent once more to the re-resolved endpoint, then fails with `error: the squad served at <endpoint> is restarting; re-run the command in a moment.`; an unreachable server fails with `error: cannot reach the squad served at <endpoint>: <cause>.`; exit 1, nothing runs locally;
- either: `vocabulary_mismatch` and `schema_mismatch` never retried and never fall back; a connection lost after sending is an error, never replayed;
- timeouts from the operation's class: `standard` 5 s connect and 300 s answer, `long` 5 s connect and no answer timeout, with `waiting for the daemon (<operation>)…` on stderr after 10 s; a timeout prints the "may still complete" message and exits 1, Ctrl-C the same sentence without the duration and exits 130; a connect timeout is an unreachable daemon.

Tests: two members of the cross-process set: fall back (an unusable runtime directory runs the command locally with its one stderr line, and the next command tries again) and no replay (a daemon killed after the request was sent gives the error, and `show --json` shows the write at most once); plus the Ctrl-C member (interrupting during a write leaves it visible once). 3 tests. Timeouts, the waiting notice and the no-local-mode branches are built and not tested (see the task's "Left open").
<!-- sq:subtask:ST5:body:end -->

#### Discussion

<!-- sq:subtask:ST5:discussion -->
<!-- sq:subtask:ST5:discussion:end -->
<!-- sq:subtask:ST5:end -->

<!-- sq:subtask:ST6 -->
### ST6 — Mode parity run over HttpApi

<!-- sq:subtask:ST6:body -->
Mode parity (ADR-1172 "Mode parity", ADR-1225 section 5): the `invoke` fixture gains a run-wide remote mode in which the root callback's API is an `HttpApi` talking to TASK-1218's application served on a thread of the test process against the same copied squad, so every existing surface case asserts the same whole output in both modes. Commands that make no call or are `local_only` run as in local mode. What it proves: every DTO round-trips through JSON and the error table keeps messages and exit codes. The root `conftest.py` sets `SQUADS_DAEMON=off` for every test that does not exercise the daemon. Falsify by dropping one header or one DTO field on the wire and seeing remote-mode cases fail.

Tests: no new case; the existing suite runs in a second mode in its own CI job (TASK-1220).
<!-- sq:subtask:ST6:body:end -->

#### Discussion

<!-- sq:subtask:ST6:discussion -->
<!-- sq:subtask:ST6:discussion:end -->
<!-- sq:subtask:ST6:end -->

<!-- sq:subtask:ST7 -->
### ST7 — Schema and vocabulary headers, client side

<!-- sq:subtask:ST7:body -->
Client side of the schema and vocabulary checks (ADR-1225 sections 3 and 5). The CLI sends `Squads-Schema` with its `SCHEMA_VERSION` and `Squads-Vocabulary` with the hash of exactly the documents it parsed the command with, computed by TASK-1218's `_api` function from the same `spec_sources` bytes the parser loaded, on every call. Messages, exit 1, no fall back:
- client behind: `error: squads <version> speaks schema v<A>, and the squad served at <endpoint> runs schema v<B>. Install a squads release at schema v<B>, then re-run.`
- client ahead: `error: squads <version> speaks schema v<A>, and the squad served at <endpoint> runs schema v<B>. The squad's server must be upgraded and the squad migrated (sq migrate up) before this client can use it.`
- vocabulary: `error: this checkout's workflow vocabulary differs from the squad served at <endpoint> (<document> differs). Bring this checkout in line with the squad, by pulling its configuration or installing the squads version it runs, then re-run.`, naming the document from the per-document digests.

A `tests/meta` guard fails if the parser reaches a document the hash leaves out.

Tests (surface, remote mode in-process): one case per message, whole stderr and exit code (3); the guard (1).
<!-- sq:subtask:ST7:body:end -->

#### Discussion

<!-- sq:subtask:ST7:discussion -->
<!-- sq:subtask:ST7:discussion:end -->
<!-- sq:subtask:ST7:end -->

<!-- sq:subtask:ST8 -->
### ST8 — Client budget: levers, import guard, benchmark

<!-- sq:subtask:ST8:body -->
The client budget of ADR-1225 section 5: client overhead (wall time minus the daemon's `Server-Timing`) for `sq <type> <n> show`, median of 31 interleaved runs on the reference host, at most 275 ms human and 235 ms `--json`.

Levers on the client path not already set by the command-layer tasks (DTO modules per resource with `defer_build`, renderers importing only `rich` and `_api`, `rich.markdown` lazy, no `_services`):
- `gc.freeze()` once output is flushed and `gc.disable()` for start-up, in `main`;
- lazy command modules: a literal command-name table at the root importing only the invoked group's module (root `--help` still loads all), with a `tests/meta` guard comparing the table to the registered tree;
- `__version__` without `importlib.metadata` at import;
- `anyio` confined to the service side;
- the spec loader path trimmed to what loading needs (override scaffolding and manifest modules off it).

The import guard (`tests/meta`): importing the remote path (root callback, `HttpApi`, the renderer) in a subprocess leaves `sys.modules` without `squads._services`, `squads._index`, `jinja2`, `yaml`, `anyio`, `filelock`, `importlib.metadata`, `starlette`, `uvicorn`, and without `rich.markdown` before a body is rendered.

A benchmark script under `scripts/` measures the budget; the `releasing-squads` skill gains the step that runs it on the reference host and records the numbers with the release; TASK-1220 runs it in CI as a report.

Tests: 2 guards (imports, command-name table). The benchmark is a report, not a test.
<!-- sq:subtask:ST8:body:end -->

#### Discussion

<!-- sq:subtask:ST8:discussion -->
<!-- sq:subtask:ST8:discussion:end -->
<!-- sq:subtask:ST8:end -->

<!-- sq:subtask:ST9 -->
### ST9 — The terminal UI as a daemon client

<!-- sq:subtask:ST9:body -->
The terminal UI as a daemon client (FEAT-1140 US13, ADR-1224 point 7, ADR-1225 section 5), on the per-call selector TASK-1233 leaves in `_tui/_app.py`:
- `sq ui` selects by the same rule as any command; in remote mode its terminal stays in its own process;
- each call resolves the endpoint and computes the vocabulary hash from the checkout (0.2 ms), so a configuration edited mid-session is picked up on the next call;
- `503 retiring` from a local daemon runs that call on `LocalApi`, the next call reaches a daemon on the new configuration, and the filter catalogs are reloaded after a retirement; the session never stays in local mode;
- a refused connection (a daemon that exited) resolves again for that call: a local daemon is started again, or `LocalApi` answers when that fails;
- a call lost after it was sent is shown as an error on the screen, never replayed, and the user can refresh.

Tests: none automated (see TASK-1233); the operator checks a session against the daemon, editing the workflow override and stopping the daemon mid-session.
<!-- sq:subtask:ST9:body:end -->

#### Discussion

<!-- sq:subtask:ST9:discussion -->
<!-- sq:subtask:ST9:discussion:end -->
<!-- sq:subtask:ST9:end -->
<!-- sq:subtasks:end -->

## Discussion

<!-- sq:discussion -->
- [2026-10-28T19:03:20Z] `manager` Catherine Manager:
  - @tech-lead From the TASK-1217 fixes (REV-1223 F1): role add/update --file are typed Path, so typer normalises ./r.toml to r.toml before the attachment lookup. The file-argument table in ST4 must key those two options by the normalised form, or the forwarder must normalise the same way.
<!-- sq:discussion:end -->
