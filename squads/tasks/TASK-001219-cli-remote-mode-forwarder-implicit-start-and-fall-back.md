---
id: TASK-1219
sequence_id: 1219
type: task
title: 'CLI remote mode: forwarder, implicit start and fall back'
status: Draft
parent: FEAT-1140
author: tech-lead
priority: high
refs:
- ADR-1052:implements
- TASK-1218:depends-on
description: Stdlib forwarder in __main__, detached spawn, discovery and staleness,
  local fall back, attachments table, parity matrix
subentities:
- local_id: ST1
  title: Forwarder, local-only commands and fall back
  status: Todo
  story: US3
- local_id: ST2
  title: Discovery, staleness cleanup and detached spawn
  status: Todo
  story: US4
- local_id: ST3
  title: Native Windows client path
  status: Todo
  story: US6
- local_id: ST4
  title: Attachments table from the command tree, guarded
  status: Todo
  story: US1
- local_id: ST5
  title: Forwarding through the one endpoint and Ctrl-C
  status: Todo
  story: US10
- local_id: ST6
  title: Parity matrix in both modes
  status: Todo
  story: US3
created_at: '2026-10-28T14:08:42Z'
updated_at: '2026-10-28T14:09:57Z'
---
<!-- sq:body -->
## Goal

Remote mode in the CLI: a stdlib-only forwarder in `squads.__main__:main` that starts the daemon on first use, forwards each command through `POST /v1/commands`, and falls back to local mode only where ADR-1052 allows. This is the task that turns the daemon on for adopters, so output parity between the modes is proven here.

## What it builds

- **Forwarder in `src/squads/__main__.py` (point 9).** Runs before `squads._cli` is imported, beside the bare `--version` path. Reads only the leading root options (`-C <path>` in its accepted forms, `--at`, `--help`) and the first command name, then calls the shared endpoint-resolution module from the daemon task. Imports nothing beyond the standard library and that module on the remote path.
- **Silent local mode** when there is no squad, the daemon is off (`[daemon] enabled` / `SQUADS_DAEMON`, or an unusable setting, which prints its one stderr line), the command line holds anything the forwarder does not understand, and for `ui`, `daemon`, `init`, `adopt`, shell completion and a bare `--version`.
- **Attachments (point 9).** The forwarder attaches every `--file` value and the import file argument, and stdin when one of them is `-`. It learns which tokens those are from a table generated from the command tree and checked in; a `tests/meta` guard regenerates it and fails on drift.
- **Discovery and start (points 8, 11).** Find a live daemon for the key (POSIX: connect to `<key>.sock`; Windows: read `<key>.json`, then `GET /v1/daemon` and check pid and squad path, since a port can be reused). A socket refusing connections while `<key>.lock` is free is a dead daemon: remove its files. Otherwise spawn `sys.executable -m squads daemon run` detached (a new session on POSIX; `DETACHED_PROCESS`, `CREATE_NEW_PROCESS_GROUP`, `CREATE_NO_WINDOW` on Windows), wait at most 5 seconds for `ready` or the failure line on the pipe. Two clients spawning at once both connect to the winner.
- **Failed start.** Spawn error, failure line, no answer within 5 seconds, unusable runtime directory: run in local mode with one stderr line giving the reason and how to turn the daemon off; the next command tries again. Where no local squad exists, fail with a clear error (the local CLI's `SquadsError` path).
- **What reaches the user (point 10).** Write `stdout` and `stderr` as received, exit with `exit_code`. `503 not_executed` runs the command locally with no stderr line; nothing else does. A connection lost after the request was sent is an error, never replayed. Ctrl-C stops the wait and exits; the command the daemon started runs to completion.
- **Test suite isolation.** The root `conftest.py` sets `SQUADS_DAEMON=off` for every test that does not exercise the daemon, so a run never leaves daemons behind or answers from one.

## Acceptance

US3 in full (parity including `--json`, the 5-second fallback and its stderr line, `not_executed` as the only local retry, no replay, local-only commands, prompting commands run locally, no-squad failure). US10, second and third bullets (forwarding through the one endpoint, the same command path; Ctrl-C per mode). US1: every command of the CLI runs through the endpoint. US4: implicit start, discovery, staleness cleanup, two simultaneous starts end on one daemon. US6 client side: detached spawn and the loopback port on native Windows. Feature acceptance bullets 1, 2, 3, 4, 5 and 6.

## Test approach

- **Parity matrix (ADR-1052 Consequences).** The CLI's command matrix runs in both modes and compares exit code, stdout and stderr byte for byte, once with stdout not a terminal and once with a terminal of fixed width and colour system. To keep the suite's wall time bounded, the full matrix goes through the HTTP app in-process, and a smaller set (one read, one write, one `--json`, one error, one file attachment, one prompting command) runs against a real spawned daemon. Falsify by dropping one env variable from the forwarded list and by building one console at import again.
- **Forwarder parsing table:** every accepted `-C` form, `--at`, `--help`, `--`, an unknown leading option, each local-only command, completion env vars; assert remote or silent local per row.
- **Fallback table:** spawn error, child failure line, child silent past the bound (shortened by a test seam), unusable runtime directory (missing, wrong mode, wrong owner, path too long), unusable `SQUADS_DAEMON`; assert local output identical plus exactly one stderr line, and that the next command tries again.
- **No replay:** kill the daemon after it accepted the request and assert an error and that the command ran at most once (index counter, item count).
- **Concurrency:** N clients started at once on a cold key end on one daemon pid.
<!-- sq:body:end -->

## Subtasks

_Add with `sq task 1219 add-subtask "<title>"`; track with `sq task 1219 subtask <n> update --status <Status>`._

<!-- sq:subtasks -->

<!-- sq:subtask:ST1 -->
### ST1 — Forwarder, local-only commands and fall back

<!-- sq:subtask:ST1:body -->
Stdlib forwarder in `squads.__main__:main` reading only leading root options and the command name; silent local mode for no squad, daemon off, unknown tokens, `ui`, `daemon`, `init`, `adopt`, completion, bare `--version`; failed start runs locally with one stderr line and retries next time; only `503 not_executed` retries locally; lost connection after send is an error, never replayed. Parsing and fallback tables.
<!-- sq:subtask:ST1:body:end -->

#### Discussion

<!-- sq:subtask:ST1:discussion -->
<!-- sq:subtask:ST1:discussion:end -->
<!-- sq:subtask:ST1:end -->

<!-- sq:subtask:ST2 -->
### ST2 — Discovery, staleness cleanup and detached spawn

<!-- sq:subtask:ST2:body -->
Find the daemon by key (socket on POSIX; `<key>.json` plus `GET /v1/daemon` pid and path check on TCP); remove a dead daemon's files when the socket refuses and the lock is free; spawn `sys.executable -m squads daemon run` detached with the per-platform flags and wait at most 5 seconds. N clients on a cold key end on one pid.
<!-- sq:subtask:ST2:body:end -->

#### Discussion

<!-- sq:subtask:ST2:discussion -->
<!-- sq:subtask:ST2:discussion:end -->
<!-- sq:subtask:ST2:end -->

<!-- sq:subtask:ST3 -->
### ST3 — Native Windows client path

<!-- sq:subtask:ST3:body -->
Windows spawn flags (`DETACHED_PROCESS`, `CREATE_NEW_PROCESS_GROUP`, `CREATE_NO_WINDOW`), the loopback CLI port with no `Origin` header sent, the port-reuse identity check and `%LOCALAPPDATA%` runtime files. Proven on the CI Windows runner; locally covered by the platform-independent rows only.
<!-- sq:subtask:ST3:body:end -->

#### Discussion

<!-- sq:subtask:ST3:discussion -->
<!-- sq:subtask:ST3:discussion:end -->
<!-- sq:subtask:ST3:end -->

<!-- sq:subtask:ST4 -->
### ST4 — Attachments table from the command tree, guarded

<!-- sq:subtask:ST4:body -->
Generate and check in the table of which tokens are file arguments (`--file` values, the import file, `-` for stdin) from the command tree; the forwarder attaches their content. A `tests/meta` guard regenerates it and fails on drift; falsify by adding a file option without regenerating.
<!-- sq:subtask:ST4:body:end -->

#### Discussion

<!-- sq:subtask:ST4:discussion -->
<!-- sq:subtask:ST4:discussion:end -->
<!-- sq:subtask:ST4:end -->

<!-- sq:subtask:ST5 -->
### ST5 — Forwarding through the one endpoint and Ctrl-C

<!-- sq:subtask:ST5:body -->
The forwarder posts argv, cwd, the listed env, terminal facts and attachments, writes stdout/stderr as received and exits with exit_code; no second client or service interface. Ctrl-C stops only the wait, and the started command completes once (asserted through the index counter). Root `conftest.py` sets `SQUADS_DAEMON=off` for every test not exercising the daemon.
<!-- sq:subtask:ST5:body:end -->

#### Discussion

<!-- sq:subtask:ST5:discussion -->
<!-- sq:subtask:ST5:discussion:end -->
<!-- sq:subtask:ST5:end -->

<!-- sq:subtask:ST6 -->
### ST6 — Parity matrix in both modes

<!-- sq:subtask:ST6:body -->
The CLI command matrix in local and remote mode, byte-for-byte exit code, stdout and stderr, once without a terminal and once with a fixed-width, fixed-colour terminal; full matrix in-process over the HTTP app, a small set against a real spawned daemon. Falsify by dropping one forwarded env variable.
<!-- sq:subtask:ST6:body:end -->

#### Discussion

<!-- sq:subtask:ST6:discussion -->
<!-- sq:subtask:ST6:discussion:end -->
<!-- sq:subtask:ST6:end -->
<!-- sq:subtasks:end -->

## Discussion

<!-- sq:discussion -->
<!-- sq:discussion:end -->
