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
updated_at: '2026-10-28T19:17:57Z'
---
<!-- sq:body -->
## Goal

Remote mode in the CLI: a stdlib-only forwarder in `squads.__main__:main` that starts the daemon on first use, forwards each command through `POST /v1/commands`, and falls back to local mode only where ADR-1052 allows. This is the task that turns the daemon on for adopters, so output parity between the modes is proven here.

## What it builds

- **Forwarder in `src/squads/__main__.py` (point 9).** Runs before `squads._cli` is imported, beside the bare `--version` path. Reads only the leading root options (`-C <path>` in its accepted forms, `--at`, `--help`) and the first command name, then calls the shared endpoint-resolution module from the daemon task. Imports nothing beyond the standard library and that module on the remote path.
- **Silent local mode** when there is no squad, the daemon is off (`[daemon] enabled` / `SQUADS_DAEMON`, or an unusable setting, which prints its one stderr line), the command line holds anything the forwarder does not understand, and for `ui`, `daemon`, `init`, `adopt`, shell completion and a bare `--version`.
- **Attachments (point 9).** The forwarder attaches, base64-encoded and keyed by the token exactly as written, the value of every client-file parameter (today every `--file` option and the file argument of `import`), and stdin when one of them is `-`. A file it cannot read runs the command in local mode, which reports the error as it always does.
- **File-argument table (point 9).** A checked-in, stdlib-only module the forwarder imports: the client-file option names, and per command path the positions of client-file arguments. Options are keyed by name, so the item commands of custom types are covered without the forwarder knowing their names. Each client-file parameter is declared through one shared helper in `src/squads/_cli/_common.py` (today `file_option` covers `--file`; the `import` argument joins it). A `tests/meta` guard walks the command tree, an item app built for a custom type included, compares the declared parameters with the module and prints the expected module on drift. No generator script, no build step.
- **Request (point 1).** `argv`, `cwd`, the eight listed env variables, `terminal` (tty flags, size and each stream's encoding) and `attachments`, as UTF-8 JSON, with `Squads-Client: 1` on every listener. On native Windows the forwarder first reconfigures its stdout and stderr to UTF-8 with replacement, as the CLI does at import, so the encodings it reports and writes with are local mode's.
- **Discovery and start (points 8, 11).** Find a live daemon for the key (POSIX: connect to `<key>.sock`; Windows: read `<key>.json`, then `GET /v1/daemon` and check pid and squad path, since a port can be reused). A socket refusing connections while `<key>.lock` is free is a dead daemon: remove its files. Otherwise spawn `sys.executable -m squads daemon run` detached (a new session on POSIX; `DETACHED_PROCESS`, `CREATE_NEW_PROCESS_GROUP`, `CREATE_NO_WINDOW` on Windows), wait at most 5 seconds for `ready` or the failure line on the pipe. Two clients spawning at once both connect to the winner.
- **Failed start.** Spawn error, failure line, no answer within 5 seconds, unusable runtime directory: run in local mode with one stderr line giving the reason and how to turn the daemon off; the next command tries again. Where no local squad exists, fail with a clear error (the local CLI's `SquadsError` path).
- **What reaches the user (point 10).** Write `stdout` and `stderr` as received, exit with `exit_code`. `503 not_executed` runs the command locally with no stderr line; nothing else does. A connection lost after the request was sent is an error, never replayed. Ctrl-C stops the wait and exits; the command the daemon started runs to completion.
- **Test suite isolation.** The root `conftest.py` sets `SQUADS_DAEMON=off` for every test that does not exercise the daemon, so a run never leaves daemons behind or answers from one.

## Acceptance

US3 in full (parity including `--json`, the 5-second fallback and its stderr line, `not_executed` as the only local retry, no replay, local-only commands, prompting commands run locally, no-squad failure). US10, second and third bullets (forwarding through the one endpoint, the same command path; Ctrl-C per mode). US1: every command of the CLI runs through the endpoint. US4: implicit start, discovery, staleness cleanup, two simultaneous starts end on one daemon. US6 client side: detached spawn and the loopback port on native Windows. Feature acceptance bullets 1, 2, 3, 4, 5 and 6.

## Test approach

- Parity: the existing surface suite runs again in remote mode in its own CI job (ADR-1172 "Mode parity", ST6). No new cases.
- Cross-process: exactly the members ADR-1172 "The cross-process set" names: implicit start and discovery (ST2), fall back and no replay (ST1), Ctrl-C (ST5), detached spawn on Windows (ST3). 6 tests, run by TASK-1220's job.
- The file-argument table is held by its `tests/meta` guard (ST4).
- Built and not tested: idle exit (ADR-1052 point 11), simultaneous starts and staleness cleanup.
<!-- sq:body:end -->

## Subtasks

_Add with `sq task 1219 add-subtask "<title>"`; track with `sq task 1219 subtask <n> update --status <Status>`._

<!-- sq:subtasks -->

<!-- sq:subtask:ST1 -->
### ST1 — Forwarder, local-only commands and fall back

<!-- sq:subtask:ST1:body -->
Stdlib forwarder in `squads.__main__:main` reading only leading root options and the command name; silent local mode for no squad, daemon off, unknown tokens, `ui`, `daemon`, `init`, `adopt`, completion, bare `--version`; failed start runs locally with one stderr line and retries next time; only `503 not_executed` retries locally; lost connection after send is an error, never replayed. Tests: two members of the cross-process set (ADR-1172 "The cross-process set"), real `sq` against a scratch squad, whole stdout, stderr and exit code asserted: fall back (an unusable runtime directory runs the command locally with its one stderr line, and the next command tries again) and no replay (a daemon killed after the request was sent gives the error, and `sq … show --json` shows the write at most once). The local-only commands are held by the remote-mode run of their existing surface cases. 2 tests.
<!-- sq:subtask:ST1:body:end -->

#### Discussion

<!-- sq:subtask:ST1:discussion -->
<!-- sq:subtask:ST1:discussion:end -->
<!-- sq:subtask:ST1:end -->

<!-- sq:subtask:ST2 -->
### ST2 — Discovery, staleness cleanup and detached spawn

<!-- sq:subtask:ST2:body -->
Find the daemon by key (socket on POSIX; `<key>.json` plus `GET /v1/daemon` pid and path check on TCP); remove a dead daemon's files when the socket refuses and the lock is free; spawn `sys.executable -m squads daemon run` detached with the per-platform flags and wait at most 5 seconds. Tests: two members of the cross-process set (ADR-1172 "The cross-process set"): implicit start (a first command on a cold key starts a daemon that `sq daemon status --json` then reports) and discovery (a second command is answered by that same pid). Simultaneous starts, staleness cleanup and idle exit are built and not tested (idle exit: ADR-1052 point 11). 2 tests.
<!-- sq:subtask:ST2:body:end -->

#### Discussion

<!-- sq:subtask:ST2:discussion -->
<!-- sq:subtask:ST2:discussion:end -->
<!-- sq:subtask:ST2:end -->

<!-- sq:subtask:ST3 -->
### ST3 — Native Windows client path

<!-- sq:subtask:ST3:body -->
Windows spawn flags (`DETACHED_PROCESS`, `CREATE_NEW_PROCESS_GROUP`, `CREATE_NO_WINDOW`), the loopback CLI port with no `Origin` header sent, the port-reuse identity check and `%LOCALAPPDATA%` runtime files. Tests: the detached-spawn member of the cross-process set (ADR-1172 "The cross-process set"), Windows only: the daemon a command started still answers after that client's process group has ended. The other members run on the `windows-latest` job as on every OS. 1 test.
<!-- sq:subtask:ST3:body:end -->

#### Discussion

<!-- sq:subtask:ST3:discussion -->
<!-- sq:subtask:ST3:discussion:end -->
<!-- sq:subtask:ST3:end -->

<!-- sq:subtask:ST4 -->
### ST4 — Attachments table from the command tree, guarded

<!-- sq:subtask:ST4:body -->
A checked-in, stdlib-only module the forwarder imports: client-file option names, and per command path the positions of client-file arguments; options keyed by name so custom-type item commands are covered. Each client-file parameter is declared through one shared helper in `_cli/_common.py` (the `import` file argument joins `file_option`). A `tests/meta` guard walks the command tree, a custom-type item app included, compares with the module and prints the expected module on drift; no generator script. Falsify by adding a file parameter without updating the module. The forwarder base64-encodes each attachment keyed by its literal token; a file it cannot read runs the command locally.
<!-- sq:subtask:ST4:body:end -->

#### Discussion

<!-- sq:subtask:ST4:discussion -->
<!-- sq:subtask:ST4:discussion:end -->
<!-- sq:subtask:ST4:end -->

<!-- sq:subtask:ST5 -->
### ST5 — Forwarding through the one endpoint and Ctrl-C

<!-- sq:subtask:ST5:body -->
The forwarder posts argv, cwd, the listed env, terminal facts (tty flags, size, each stream's encoding) and attachments with `Squads-Client: 1`, writes stdout/stderr as received and exits with exit_code; no second client or service interface. On native Windows it reconfigures stdout and stderr to UTF-8 with replacement first, as the CLI does at import. Ctrl-C stops only the wait, and the started command completes once. Root `conftest.py` sets `SQUADS_DAEMON=off` for every test not exercising the daemon. Tests: the Ctrl-C member of the cross-process set (ADR-1172 "The cross-process set"): interrupting the client during a write leaves that write visible once in `sq … show --json`. Output parity is ST6. 1 test.
<!-- sq:subtask:ST5:body:end -->

#### Discussion

<!-- sq:subtask:ST5:discussion -->
<!-- sq:subtask:ST5:discussion:end -->
<!-- sq:subtask:ST5:end -->

<!-- sq:subtask:ST6 -->
### ST6 — Parity matrix in both modes

<!-- sq:subtask:ST6:body -->
Parity matrix (ADR-1052 Consequences) as the CLI surface suite run in remote mode: the `invoke` fixture gains a run-wide remote mode that sends each argument list through the endpoint harness of TASK-1218 with the runner's terminal facts, so every existing surface case asserts the same whole output in both modes, with stdout not a terminal and with a fixed-width, fixed-colour terminal. Commands ADR-1052 keeps local run locally in that mode. Its CI job is TASK-1220's. No new test cases: the existing cases run in a second mode. Falsify by dropping one forwarded env variable and seeing remote-mode cases fail. Per ADR-1172 "Mode parity".
<!-- sq:subtask:ST6:body:end -->

#### Discussion

<!-- sq:subtask:ST6:discussion -->
<!-- sq:subtask:ST6:discussion:end -->
<!-- sq:subtask:ST6:end -->
<!-- sq:subtasks:end -->

## Discussion

<!-- sq:discussion -->
- [2026-10-28T19:03:20Z] `manager` Catherine Manager:
  - @tech-lead From the TASK-1217 fixes (REV-1223 F1): role add/update --file are typed Path, so typer normalises ./r.toml to r.toml before the attachment lookup. The file-argument table in ST4 must key those two options by the normalised form, or the forwarder must normalise the same way.
<!-- sq:discussion:end -->
