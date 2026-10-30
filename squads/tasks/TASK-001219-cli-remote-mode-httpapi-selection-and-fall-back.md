---
id: TASK-1219
sequence_id: 1219
type: task
title: 'CLI remote mode: HttpApi, selection and fall back'
status: Ready
parent: FEAT-1140
author: tech-lead
refs:
- ADR-1052:implements
- TASK-1218:depends-on
- ADR-1225:implements
- TASK-1233:depends-on
- TASK-1238:depends-on
description: Root callback picks HttpApi or LocalApi; implicit start, conditional
  fall back, timeouts, schema and vocabulary headers, client budget and guard, parity
  run, the TUI as a daemon client
subentities:
- local_id: ST1
  title: API selection in the root callback
  status: Todo
  maps_to: US3
- local_id: ST2
  title: Implicit start, discovery and failed start
  status: Todo
  maps_to: US4
- local_id: ST3
  title: Native Windows client path
  status: Todo
  maps_to: US6
- local_id: ST4
  title: HttpApi requests, headers and errors
  status: Todo
  maps_to: US10
- local_id: ST5
  title: Fall back, no replay, timeouts and Ctrl-C
  status: Todo
  maps_to: US3
- local_id: ST6
  title: Mode parity run over HttpApi
  status: Todo
  maps_to: US3
- local_id: ST7
  title: Schema and vocabulary headers, client side
  status: Todo
  maps_to: US11
- local_id: ST8
  title: 'Client budget: levers, import guard, benchmark'
  status: Todo
  maps_to: US12
- local_id: ST9
  title: The terminal UI as a daemon client
  status: Todo
  maps_to: US13
created_at: '2026-10-28T14:08:42Z'
updated_at: '2026-10-30T07:20:38Z'
priority: high
---
<!-- sq:body -->
## Goal

Remote mode (ADR-1225 section 10, D2): the CLI itself calls the daemon through `HttpApi`, chosen once per invocation by the root callback, with implicit start, the conditional fall back, timeouts, the schema and vocabulary headers, the client budget and its guard, the mode-parity run, and the terminal UI as a daemon client. This is the task that turns the daemon on for adopters. Every command is on an operation (FEAT-1226), so remote mode covers the whole CLI, `squad.rename-field` and `squad.rename-kind` included, and can be trialled with `SQUADS_DAEMON=on` as soon as this lands.

## What it builds

- **API selection** (ADR-1225 section 5, ADR-1052 point 9) — ST1. The root callback calls TASK-1218's endpoint resolution and puts `HttpApi` or `LocalApi` on `RequestContext`. Commands that make no call (`docs`, `migrate help`, `migrate chlog`, `--version`, `--help`, completion) never contact or start a daemon; nor do `init`, `adopt` (`local_only`) and `daemon`. With no squad found, the command fails with today's message. On the remote path the CLI reads only what ADR-1225 section 5 lists: `squad_dir` and `[daemon]` of `.squads.toml`, and the bundled and override `workflow.toml` for parsing; the override's cross-check against the index, the schema gate and the working-language notice are the daemon's. Local mode keeps them where they are.
- **Implicit start and discovery** (ADR-1052 points 8, 11) — ST2. Find a live daemon by key (POSIX: connect to `<key>.sock`; Windows: `<key>.json` then `GET /v1/daemon` with the pid and squad-path check); a socket refusing connections while the lock is free is a dead daemon whose files are removed; otherwise spawn `sys.executable -m squads daemon run` detached and wait at most 5 s for `ready`. A failed start (spawn error, failure line, no answer in 5 s, unusable runtime directory) runs the command locally with one stderr line giving the reason and how to turn the daemon off; the next command tries again.
- **Native Windows client** — ST3. Spawn flags, the loopback CLI port with no `Origin` sent, the port-reuse identity check, `%LOCALAPPDATA%` runtime files.
- **`HttpApi` requests and errors** (ADR-1225 sections 2, 3) — ST4. `http.client` over the Unix socket or loopback TCP, one request per call, using TASK-1227's wire helpers: path and query or JSON body from the request DTO, headers from `RequestContext` (`Squads-Actor`, `Squads-At`, `Squads-Session-Id`, `Squads-Parent-Session-Id`, `Squads-Client-Dir`, `Squads-Schema`, `Squads-Vocabulary`, `Squads-Client: 1`), `Response[Res]` parsed and validated, an error body turned back into a `SquadsError` with the daemon's message and its `warnings` (the error envelope carries them since ADR-1225 section 3's amendment for REV-1235 F48; `parse_response` in `_api/_http.py` drops them today), so the CLI prints the notices, then `error: <message>`, and exits 1.
- **Fall back, no replay, timeouts, Ctrl-C** (ADR-1225 sections 3, 5; ADR-1052 point 10) — ST5. Against an endpoint with a local mode, `503 retiring` reruns the call on `LocalApi` silently, and an unreachable or unstartable daemon gives way to `LocalApi`. Against one without (the FEAT-33 seam), `503 retiring` is retried once against the re-resolved endpoint, then fails with the "is restarting" message; an unreachable server fails with the "cannot reach" message; nothing runs locally. A connection lost after sending is an error, never replayed. Timeouts from the operation's class: `standard` 5 s connect and 300 s answer, `long` 5 s connect and no answer timeout with the `waiting for the daemon (<operation>)…` notice after 10 s. `long` is `migrate up`, `migrate repad`, `migrate rename-type`, `migrate rename-status`, `migrate rename-field`, `migrate rename-kind`, `repair`, `renumber` and `import`, exactly the operations the table classes `long`; `HttpApi` reads `op.timeout` and keeps no list of its own. A timeout or Ctrl-C ends only the wait, with the "may still complete" message, exit 1 or 130; a connect timeout is an unreachable daemon.
- **Mode parity** (ADR-1172 "Mode parity", ADR-1225 section 5) — ST6. A run-wide remote mode of the `invoke` fixture that sends every surface case through `HttpApi` against TASK-1218's application served in-process, selected like the squad: a root `conftest.py` option beside `--squad` (with its environment variable, as `SQUADS_TEST_SQUAD` is), so mode and squad compose and the `bundled_only`/`override_only` markers apply unchanged. The root `conftest.py` sets `SQUADS_DAEMON=off` for every test that does not exercise the daemon. TASK-1220 runs it as its own CI job.
- **Vocabulary hash and schema, client side** (ADR-1225 sections 3, 5) — ST7. The client sends the hash of the documents it parsed with, from the same byte reads TASK-1218 shares between hashing and loading, and its `SCHEMA_VERSION`; it prints the client-behind, client-ahead and vocabulary messages of ADR-1225, naming the document that differs from the per-document digests; exit 1, no fall back. A `tests/meta` guard fails when the parser reaches a document the hash leaves out.
- **Client budget** (ADR-1225 section 5) — ST8. The levers that serve local mode too (lazy command modules with the command-name table and its guard, `gc` handling in `main`, `__version__` without metadata, `defer_build`, lazy `rich.markdown`) landed with TASK-1238 (`gc.disable()` in `__main__`, `LAZY_GROUPS`, `__version__` read on first use); this task adds the remote-only ones: `anyio` confined to the service side and the spec loader path trimmed to what loading needs. The import guard: the remote path (root callback, `HttpApi`, the renderer) loads none of `squads._services`, `squads._index`, `jinja2`, `yaml`, `anyio`, `filelock`, `importlib.metadata`, `starlette`, `uvicorn`, `click` (installed by uvicorn beside the CLI's `typer._click`, ADR-1225 section 5), nor `rich.markdown` before a body is rendered. A benchmark script measuring the client overhead (wall time minus `Server-Timing`) for `sq <type> <n> show`, median of 31 interleaved runs, human and `--json`; the release runbook (the `releasing-squads` skill) runs it on the reference host and records the numbers, beside the step that already runs `scripts/bench_local_mode.py`, whose interleaved run loop the new script reuses.
- **The terminal UI as a daemon client** (ADR-1224 point 7, ADR-1225 section 5) — ST9, on the selector seam TASK-1233 leaves.

## Modules touched

`src/squads/_cli/__init__.py` (selection), `src/squads/__main__.py`, `src/squads/_api/_http.py` and the client half of `_api`, the shared endpoint module of TASK-1218 (spawn and discovery on top of it), `src/squads/_tui/_app.py` (the selector), the spec loader modules (trim), `tests/conftest.py`, the root `conftest.py`, `tests/meta/` (budget import guard, vocabulary-document guard), a new cross-process test directory, a benchmark script under `scripts/`, the `releasing-squads` skill body. Depends on TASK-1218 (the application, endpoint resolution, the hash, the error envelope's `warnings`), TASK-1233 (the TUI seam) and TASK-1238 (the shared levers).

## Acceptance

- FEAT-1140 US3 in full, US4 (implicit start, discovery, staleness, simultaneous starts on one daemon), US6 client side, US10 (metadata sent with each call), US11 client side, US12, US13.
- Feature acceptance bullets 1-6, 9, 10 and the client budget bullet: at most 275 ms human and 235 ms `--json` on the reference host, measured and recorded.
- ADR-1225 sections 2, 3, 5 and 10 (D2); ADR-1052 points 9-11 as amended.

## Test approach (ADR-1172)

- Parity: the existing surface suite rerun in remote mode in its own CI job (TASK-1220). No new cases. The remote run covers both squads (ADR-1172 "Mode parity", manager ruling 2ab58aa on FEAT-1140): the harness takes `--squad override` as it takes the bundled squad, and no case is skipped in remote mode.
- Cross-process set, exactly ADR-1172's members, in `tests/cross_process/` beside the index lock cases already there (the ordinary `test` job passes `--ignore=tests/cross_process`; the `cross-process` job runs it with `-n0`), real `sq` against a scratch squad nested under the test's `tmp_path`, whole output asserted, state read through `show --json`: implicit start, discovery, fall back, no replay, Ctrl-C, detached spawn on Windows. 6 tests.
- Surface cases in remote mode (in-process, `HttpApi` against the served application, whole stderr and exit code): client behind, client ahead, vocabulary mismatch naming the document. 3 tests.
- Guards: budget import, vocabulary documents. 2.
- Built and not tested: idle exit, simultaneous starts, staleness cleanup.
- Timeouts get no automated test (op-pierre, 2026-10-29, FEAT-1140 comment 20c1d4d): the 300 s answer timeout, the 10 s waiting notice, and a timeout or Ctrl-C ending only the client's wait are checked live by QA in TASK-1222 ST3. The Ctrl-C cross-process member of ADR-1172 stays.
- The hosted-squad branches (retry once against the re-resolved endpoint, the "is restarting" and "cannot reach" errors) are built behind the `Endpoint` local-mode flag and not tested in this release: nothing produces an endpoint without a local mode until FEAT-33, which tests them.
- Expected total: 9 tests and 2 guards; the benchmark is a report, not a test.

- The TUI remote behaviours (ST9) get no automated test: no TUI suite this release, the TUI held by the import guard, the surface tests of the operations it calls and the operator's eye check (op-pierre on TASK-1233, 56af3ed), here a session against the daemon (TASK-1222 ST2).

## Known parity hazards (ST6)

- **Server-side stderr.** Settled by ADR-1225 section 3, "Notices raised inside an operation": the index lock's waiting notice and the reflog warnings travel in `warnings` (TASK-1218 ST12), and a `tests/meta` guard forbids stdout and stderr writes below the CLI, which keeps a daemon line out of the harness's captured output. No client code beyond ST4: `HttpApi` puts the error's `warnings` on the `SquadsError`, and the CLI prints them with a response's, before the result or the error. The lock cases live in `tests/cross_process/`, so the parity run does not assert them.
- **Key order across the wire.** Item and sub-entity rows keep stored attributes as extras (`extra="allow"`) and order their trailing keys in a `model_serializer`; a JSON round trip through `parse_response` must give the same `--json` key order. The parity run holds it; the falsification step reorders one key.
- **Process state shared with the harness.** The daemon thread sees the test's environment and working directory, so a header dropped on the wire can be masked by a value the daemon reads from its own process. TASK-1218 forbids those reads; the falsification step drops a header and sees remote-mode cases fail.

## Parallel plan: two developers, two worktrees

TASK-1218 merged first. Each lane is best taken by the developer who built the matching TASK-1218 lane.

- **Lane D, the wire (after TASK-1218 lane A):** ST4, ST5's in-call behaviour (`503 retiring` to `LocalApi`, no replay, timeout classes, the waiting notice, Ctrl-C), ST7, ST6. Files: the client module of `_api` and `_api/_http.py`, the parity hook in `_cli/_calls.py`, the root `conftest.py` (the mode option, composing with `--squad`, and `SQUADS_DAEMON=off`) and `tests/conftest.py`, the vocabulary-document guard, the three remote-mode surface cases. 3 tests, 1 guard.
- **Lane C, the process (after TASK-1218 lane B):** ST1, ST2, ST3, ST8, ST9, and all six cross-process members in `tests/cross_process/`, the no-replay and Ctrl-C ones included, written once lane D's `HttpApi` is merged. Files: `_cli/__init__.py`, `_cli/_calls.py`, `__main__.py`, `_endpoint.py` (spawn and discovery), `_tui/_app.py`, the loader and model modules the trim touches, `scripts/`, the budget import guard, the `releasing-squads` skill body (through `sq skill`). 6 tests, 1 guard.
- **Seams, fixed before both start:** `HttpApi(endpoint)` and the `Endpoint` of TASK-1218 ST2; one hook in `_calls.py` through which the parity fixture hands the root callback an `HttpApi` aimed at the harness, written by lane D and kept by lane C's selection.
- **Merge order:** D, then C rebased on it: C's selection constructs `HttpApi`, and its cross-process no-replay and Ctrl-C members exercise it.
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
`HttpApi` on `http.client`, one request per call over the Unix socket or loopback TCP, built on TASK-1227's wire helpers (ADR-1225 sections 2, 3): path and query from a flat `GET` request DTO, a UTF-8 JSON body otherwise; file text already in the DTO, nothing attached. Headers from the invocation's `RequestContext`: `Squads-Actor` (from `--as`), `Squads-At`, `Squads-Session-Id`, `Squads-Parent-Session-Id`, `Squads-Client-Dir` (the directory paths in messages are spelled from), `Squads-Schema`, `Squads-Vocabulary` (ST7), `Squads-Client: 1`. A `200` parses into `Response[Res]` through pydantic, so a disagreeing client and daemon fail at the boundary; an error body becomes a `SquadsError` carrying the daemon's message and its `warnings` (the error envelope's field since ADR-1225 section 3's amendment for REV-1235 F48; `parse_response` drops them today), so the notices print on stderr before `error: <message>` and the exit is 1, exactly as in local mode; `omitted` gives exit 4 after printing, as locally.

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
- timeouts from the operation's class: `standard` 5 s connect and 300 s answer, `long` 5 s connect and no answer timeout, with `waiting for the daemon (<operation>)…` on stderr after 10 s (`long` is `migrate up`, `migrate repad`, `migrate rename-type`, `migrate rename-status`, `migrate rename-field`, `migrate rename-kind`, `repair`, `renumber` and `import`, exactly the operations the table classes `long`; `HttpApi` reads `op.timeout` and keeps no list of its own); a timeout prints the "may still complete" message and exits 1, Ctrl-C the same sentence without the duration and exits 130; a connect timeout is an unreachable daemon.

Tests: two members of the cross-process set: fall back (an unusable runtime directory runs the command locally with its one stderr line, and the next command tries again) and no replay (a daemon killed after the request was sent gives the error, and `show --json` shows the write at most once); plus the Ctrl-C member (interrupting during a write leaves it visible once). 3 tests. Timeouts and the waiting notice get no automated test; QA checks them live (TASK-1222 ST3, op-pierre 2026-10-29). The no-local-mode branches are not tested in this release; FEAT-33 tests them. The three cross-process cases are written in lane C once this subtask's `HttpApi` behaviour is merged (see the task's parallel plan).
<!-- sq:subtask:ST5:body:end -->

#### Discussion

<!-- sq:subtask:ST5:discussion -->
<!-- sq:subtask:ST5:discussion:end -->
<!-- sq:subtask:ST5:end -->

<!-- sq:subtask:ST6 -->
### ST6 — Mode parity run over HttpApi

<!-- sq:subtask:ST6:body -->
Mode parity (ADR-1172 "Mode parity", ADR-1225 section 5): the `invoke` fixture gains a run-wide remote mode in which the root callback's API is an `HttpApi` talking to TASK-1218's application served on a thread of the test process against the same copied squad, so every existing surface case asserts the same whole output in both modes. Commands that make no call or are `local_only` run as in local mode. What it proves: every DTO round-trips through JSON and the error table keeps messages and exit codes. The mode is a root `conftest.py` option beside `--squad`, with its environment variable, so it composes with the squad selection and the `bundled_only`/`override_only` markers. The harness runs with `--squad override` as with the bundled squad (ADR-1172 "Mode parity": remote mode on both squads, no case skipped). The root `conftest.py` sets `SQUADS_DAEMON=off` for every test that does not exercise the daemon. Daemon-side writes to stdout or stderr cannot reach the client's captured output: notices travel in `warnings` and a `tests/meta` guard forbids such writes below the CLI (TASK-1218 ST12). Falsify by dropping one header or one DTO field on the wire, reordering one key of a row, and printing one line from the daemon side, and seeing remote-mode cases fail each time.

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

Levers on the client path: the ones that serve local mode as well (the literal command-name table with lazy command modules and its guard, `gc.freeze()`/`gc.disable()` in `main`, `__version__` without `importlib.metadata`, `defer_build`, `rich.markdown` on demand) landed with TASK-1238. This subtask adds the remote-only ones: `anyio` confined to the service side, and the spec loader path trimmed to what loading needs (override scaffolding and manifest modules off it).

The import guard (`tests/meta`): importing the remote path (root callback, `HttpApi`, the renderer) in a subprocess leaves `sys.modules` without `squads._services`, `squads._index`, `jinja2`, `yaml`, `anyio`, `filelock`, `importlib.metadata`, `starlette`, `uvicorn`, `click` (installed by uvicorn beside the CLI's `typer._click`, ADR-1225 section 5), and without `rich.markdown` before a body is rendered.

A benchmark script under `scripts/` measures the budget; the `releasing-squads` skill gains the step that runs it on the reference host and records the numbers with the release; TASK-1220 runs it in CI as a report.

Starting point, measured once on the development host on 2026-10-30 (one run each, not a median): `import squads._cli` takes 391 ms and loads `squads._index`, `jinja2`, `yaml` and `importlib.metadata`, so the guard starts red on those four; `squads._services`, `anyio` and `filelock` are already off it. `importlib.metadata` also comes back through pydantic 2.14: building a model's schema loads it, while importing the deferred DTO modules does not (both measured), so the cost likely moves to the first validation, where an import-only guard does not see it and the benchmark does. Spec-derived option building (`_cli/_field_options.py`, `_workflow/_derived_names.py`) now runs on every parse; its import is about 4 ms, its per-invocation work is not measured. The prototype met the budget with 9 ms (human) and 7 ms (`--json`) to spare, so measure the client overhead first, before the levers, and report it on this task.

The benchmark reuses the interleaved run loop of `scripts/bench_local_mode.py`; the runbook step sits beside the one that runs it.

Tests: 1 guard (imports). The benchmark is a report, not a test.
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
- [2026-10-29T06:54:52Z] `tech-lead` Olivia Lead:
  - Per op-pierre 20c1d4d (FEAT-1140): no automated timeout test; QA checks timeouts live in TASK-1222 ST3. Hosted-squad branches are not tested in 0.18 (FEAT-33). Body and ST5 updated; test count unchanged (9).
- [2026-10-29T07:11:55Z] `tech-lead` Olivia Lead:
  - Local-mode levers (lazy command modules and the command-name table guard, gc handling, version without metadata, defer_build, lazy rich.markdown) moved to TASK-1238 per op-pierre 739a3b6; this task keeps the remote budget, its import guard, the benchmark and the remote-only levers. Depends on TASK-1238. Guards 3 -> 2.
- [2026-10-30T00:32:59Z] `tech-lead` Olivia Lead:
  - Brought up to date with release/0.19 (2026-10-30); decisions and test count (9 tests, 2 guards) unchanged.
    - ST4: `HttpApi` restores the error envelope's `warnings` on the `SquadsError` (`parse_response` drops them today).
    - ST6: the remote mode is a root `conftest.py` option beside `--squad`. The body adds three parity hazards with their falsification: server-side stderr leaking through the shared process, key order across the JSON round trip, and process state masking a dropped header.
    - ST8: the TASK-1238 levers have landed. Measured starting point: `import squads._cli` takes 391 ms and loads `squads._index`, `jinja2`, `yaml` and `importlib.metadata`. Re-measure the 9/7 ms margin first, since spec-derived option building now runs on every parse. The benchmark reuses `scripts/bench_local_mode.py`'s loop.
    - ST5: "not tested in 0.18" now reads "this release". The TUI "left open" point is replaced by op-pierre's ruling 56af3ed on TASK-1233.
    - The `role --file` normalisation note (2e98d09) no longer applies: ADR-1225 section 9 removed the attachment table, and file text travels in the request DTO.
    - Parallel plan: lane D (ST4, ST5, ST7, ST6) merges before lane C (ST1, ST2, ST3, ST8, ST9 and the six cross-process cases).
- [2026-10-30T00:44:17Z] `tech-lead` Olivia Lead:
  - Folded the 2026-10-30 rulings: `click` joins the import guard; the parity harness takes `--squad override` and skips no case; the `long` timeout class matches the operation table (rename-field and rename-kind included) and `HttpApi` reads `op.timeout`. Cross-process members go in the existing `tests/cross_process/`. The server-stderr hazard is settled by TASK-1218 ST12.
<!-- sq:discussion:end -->
