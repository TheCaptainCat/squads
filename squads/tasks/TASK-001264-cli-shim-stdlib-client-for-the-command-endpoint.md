---
id: TASK-1264
sequence_id: 1264
type: task
title: 'CLI shim: stdlib client for the command endpoint'
status: Draft
parent: FEAT-1140
author: tech-lead
refs:
- ADR-1261:implements
- TASK-1262:depends-on
description: 'squads.__main__ becomes a stdlib shim: lean endpoint path, local-only
  and file-argument tables, prompts, fall back before sending, Windows transport,
  CLI off HttpApi, the 100 ms budget'
subentities:
- local_id: ST1
  title: Lean endpoint path for the shim
  status: Todo
  maps_to: US12
- local_id: ST2
  title: Shim entry, -C, the local-only table and the local run
  status: Todo
  maps_to: US3
- local_id: ST3
  title: Request building, attachments and answer writing
  status: Todo
  maps_to: US3
- local_id: ST4
  title: Prompts, fall back before sending, no replay, Ctrl-C
  status: Todo
  maps_to: US3
- local_id: ST5
  title: Daemon start from the shim and the Windows transport
  status: Todo
  maps_to: US6
- local_id: ST6
  title: The CLI off HttpApi, the TUI's selection kept
  status: Todo
  maps_to: US3
- local_id: ST7
  title: 'Client budget: the shim''s overhead, benchmark and runbook'
  status: Todo
  maps_to: US12
created_at: '2026-10-30T20:30:30Z'
updated_at: '2026-10-30T20:32:04Z'
priority: high
---
<!-- sq:body -->
## Goal

The client side of ADR-1261: `squads.__main__:main` becomes a standard-library shim that sends the command line to the daemon's command endpoint and writes the answer, or runs the command locally before anything is sent. The CLI stops selecting `HttpApi` itself. This is the task that changes remote mode for adopters, and it carries the client budget: at most 100 ms of shim overhead on the reference host (ADR-1261 point 10), which replaces TASK-1219 ST8's 275/235 ms.

## Scope

- **The lean endpoint path** (point 10): the shim's path imports no `dataclasses`, `typing` or `importlib.metadata`; the squad key takes the version from `squads.__version__` and the package directory from `squads.__file__`. `_endpoint.py` is split so that what the shim needs (config walk-up, `[daemon]` and `SQUADS_DAEMON`, the key, the runtime directory and its checks, the record) is stdlib-only and lean, and the typed models stay where the daemon and `sq check` use them.
- **The shim** (point 4), in order: a bare `--version`; `-C`/`--dir` read from `argv` with the CLI's own hoisting rule; the local-only table (`init`, `adopt`, `daemon`, `ui`) runs locally without contacting a daemon; endpoint resolution (no squad, daemon off, `SQUADS_DAEMON=off`, an unusable setting with its one stderr line: local); connect, starting a daemon if none is live (ADR-1052 point 11, the 5 s bound kept), read attachments, send, write each chunk to its stream through a stdlib copy of the CLI's Windows UTF-8-with-replacement stream setup, exit with the code. Running locally is importing `squads._cli` in the same process and calling `run(argv)`.
- **The request** (point 1): `argv`, `cwd`, the fixed `env` list (one literal in the shim's module, never `SQUADS_SPANS` or `SQUADS_DAEMON`), `prog_name`, `terminal` (per stream: is a terminal, encoding; the size; Windows VT processing), `attachments` from the **file-argument table** (`--file` by name wherever it appears, and `import`'s first argument), stdin read to the end under `-`, `answers`. A file the shim cannot read runs the command locally, so the error is local mode's own. Under `SQUADS_SPANS` the shim prints its own spans and the handler time the daemon sent back.
- **Prompts and fall back** (points 5, 6): on a `prompt` answer, write the output, show the prompt on the stream the answer names, read one line (or end of input) and resend with it appended to `answers`; a daemon lost between the phases makes the shim run the command locally from the start. Before sending, fall back locally on: no daemon and a failed start, a refused or reset connection before the request is fully written, an unreadable file, `503 not_executed`. After sending, nothing is replayed: a lost connection, a timeout or Ctrl-C prints ADR-1225 section 3's "the operation may still complete" error and exits 1, or 130 on Ctrl-C. No memory between invocations.
- **Answer timeouts.** ADR-1261 does not say how a shim that parses nothing applies ADR-1225's classes (`standard` 300 s; `long` no limit, the waiting notice after 10 s). Recommended, pending @architect: a literal table of the `long` command paths in the shim (`migrate up|repad|rename-type|rename-status|rename-field|rename-kind`, `repair`, `renumber`, `import`), held by a `tests/meta` guard equal to the operations the table classes `long`. Build that unless the architect rules otherwise before you reach it.
- **Starting a daemon from the shim:** the start code (`_daemon_start.py`, the parts of `_daemon_link.py` it uses) reached only on the start path, stdlib-only; its use of `filelock` for stale detection becomes a stdlib lock probe or moves into the spawned daemon. The shim's import guard holds the path to a live daemon; state in your handback which modules the start path adds.
- **Native Windows** (point 4, ADR-1052 points 4, 8, 11): the loopback CLI port with the admission headers ADR-1052 point 5 requires and no `Origin`, the port-reuse identity check, the detached spawn.
- **The CLI no longer selects `HttpApi`** (point 8): a CLI process is the shim's local fall back or a served command, both on `LocalApi`; `call()` still takes an `Api` handed in on the context (the route-parity harness). `HttpApi`, endpoint re-resolution and the vocabulary hash stay for the TUI: move the TUI's per-call selection (`session_api`, `SelectedApi`) out of `_cli/_calls.py` if the CLI no longer needs it there. Re-home or retire, with a line each in the handback, the tests whose subject was the CLI's own selection (`tests/daemon/test_remote_refusals.py`, the session cases of `tests/cross_process/test_a_daemon_that_goes_away_and_unusable_settings.py`). The remote-client import guard (`tests/meta/test_the_remote_client_path_loads_none_of_the_server_side.py`) is replaced by the shim's.
- **The budget** (point 10): `scripts/bench_remote_client.py` measures the shim's overhead (wall time minus the handler time sent with the answer), median of 31 interleaved runs of `sq task <n> show`, also `--json` and a bash completion; the `releasing-squads` skill's step names the 100 ms criterion on the reference host (edit through `sq skill`).

## Modules touched

`src/squads/__main__.py`, a new shim module (the env list literal may already exist from the endpoint task), `src/squads/_endpoint.py` (split), `src/squads/_daemon_start.py`, `src/squads/_daemon_link.py`, `src/squads/_cli/_calls.py`, `src/squads/_cli/_remote.py`, `src/squads/_tui/` (selector move only), `scripts/bench_remote_client.py`, `tests/cross_process/`, `tests/meta/`, `tests/daemon/`. The prototype at commit 046144f7 (`src/squads/_shim.py`) is a reference only: it ran `import` and every `--file` command locally and built no prompts, Windows transport or Ctrl-C.

## Acceptance

- ADR-1261 points 3 (client side), 4, 5 (client side), 6, 8 and 10; ADR-1052 points 9-11 as ADR-1261 amends them.
- The shim's overhead for `sq task <n> show`, median of 31 interleaved runs, measured on the development host and reported with p25-p75 and the load average; the 100 ms criterion itself is read on the GitHub-hosted runner's report job (the CI task).
- Output, error text and exit code byte-identical between `SQUADS_DAEMON=off` and the shim on: `show`, `show --json`, `list`, `list --json`, an error, `check`, `--help`, `task --help`, `tree`, `board list`, `inbox`, a bash completion, a confirmed `comment remove`, a `--file` write, a `--file -` write; run on a scratch squad nested under the session scratchpad, never this repository's squad, daemon stopped at the end.
- Gates: `uv run --all-extras pyright`, `uv run --all-extras ruff check .`, `uv run --all-extras ruff format --check .`, `uv run --all-extras pytest -n 6` (one full run, to a file), `--api-mode remote tests/cli`, `--api-mode remote --squad override tests/cli`, `--api-mode routes tests/cli`, `-n0 tests/cross_process`, `python scripts/gen_template_manifest.py --check`, `~/.local/bin/sq check` clean.

## Test approach (ADR-1172)

- Cross-process set (`tests/cross_process/`, real `sq` console script, scratch squad under the test's `tmp_path`, whole output, state through `show --json`), new members: the shim falling back on a refused connection (1); the daemon killed between the two phases of a prompt, the shim asking again locally with nothing written (1); the local-only table never contacting a daemon (1). The existing members (implicit start, discovery, fall back, no replay, Ctrl-C, Windows detached spawn) are re-pointed at the shim and stay. 3 new tests.
- Guards in `tests/meta/` (4, plus 1 replaced): the shim's import set in a subprocess (no other `squads` module, no third-party package, none of `dataclasses`, `typing`, `importlib.metadata`), replacing the remote-client guard; the file-argument table equal to the parameters declared through the shared `--file` helper and `import`'s signature; the local-only table equal to the registered root commands and the `local_only` operations; the shim's `-C` extraction equal to the root callback's over every accepted spelling (a table test). Plus the `long`-class table guard if the timeout recommendation stands. Show each red against a planted violation.
- Timeouts and the waiting notice get no automated test (op-pierre, 2026-10-29); the dogfood task checks them live.
- Expected: 3 tests, 4 guards (5 with the timeout table), 1 guard removed.
- Order: depends on the command-endpoint task (its wire format, served execution and parity harness). Starts when that task is merged.
<!-- sq:body:end -->

## Subtasks

_Add with `sq task 1264 add-subtask "<title>"`; track with `sq task 1264 subtask <n> update --status <Status>`._

<!-- sq:subtasks -->

<!-- sq:subtask:ST1 -->
### ST1 — Lean endpoint path for the shim

<!-- sq:subtask:ST1:body -->
Split `_endpoint.py` so the shim's path is stdlib-only and imports no `dataclasses`, `typing` or `importlib.metadata`: config walk-up, `[daemon]` and `SQUADS_DAEMON`, the key from `squads.__version__` and `squads.__file__`, the runtime directory and its checks, the record. The typed models stay for the daemon and `sq check`.

Guard (replaces `tests/meta/test_the_remote_client_path_loads_none_of_the_server_side.py`): the shim, run in a subprocess on the path to a live daemon, leaves no `squads` module but `squads`, `squads._endpoint` and the shim's own, no third-party package, and none of `dataclasses`, `typing`, `importlib.metadata` in `sys.modules` (1).
<!-- sq:subtask:ST1:body:end -->

#### Discussion

<!-- sq:subtask:ST1:discussion -->
<!-- sq:subtask:ST1:discussion:end -->
<!-- sq:subtask:ST1:end -->

<!-- sq:subtask:ST2 -->
### ST2 — Shim entry, -C, the local-only table and the local run

<!-- sq:subtask:ST2:body -->
`squads.__main__:main` becomes the shim: a bare `--version`; `-C`/`--dir` read with the CLI's hoisting rule; the local-only table (`init`, `adopt`, `daemon`, `ui`) runs locally without contacting a daemon; endpoint resolution, with no squad, daemon off, `SQUADS_DAEMON=off` or an unusable setting (one stderr line) running locally. Running locally is importing `squads._cli` and calling `run(argv)` in the same process.

Tests: cross-process, the local-only table never contacting a daemon (1). Guards: the local-only table equal to the registered root commands and the `local_only` operations (1); the shim's `-C` extraction equal to the root callback's over every accepted spelling (1).
<!-- sq:subtask:ST2:body:end -->

#### Discussion

<!-- sq:subtask:ST2:discussion -->
<!-- sq:subtask:ST2:discussion:end -->
<!-- sq:subtask:ST2:end -->

<!-- sq:subtask:ST3 -->
### ST3 — Request building, attachments and answer writing

<!-- sq:subtask:ST3:body -->
The request of ADR-1261 point 1: `argv` (lone surrogates), `cwd`, the fixed `env` list (never `SQUADS_SPANS` or `SQUADS_DAEMON`), `prog_name`, `terminal` (per stream: terminal or not, encoding; size; Windows VT processing), attachments from the file-argument table (`--file` by name wherever it appears, `import`'s first argument), stdin read to the end under `-`, an unreadable file running the command locally. Each answer chunk written to its stream through a stdlib copy of the CLI's Windows UTF-8-with-replacement setup, then exit with the code; under `SQUADS_SPANS` the shim's spans and the daemon's handler time.

Guard: the file-argument table equal to the parameters declared through the shared `--file` helper and `import`'s signature (1). Behaviour held by the parity run and the twelve-case byte comparison of the task's acceptance.
<!-- sq:subtask:ST3:body:end -->

#### Discussion

<!-- sq:subtask:ST3:discussion -->
<!-- sq:subtask:ST3:discussion:end -->
<!-- sq:subtask:ST3:end -->

<!-- sq:subtask:ST4 -->
### ST4 — Prompts, fall back before sending, no replay, Ctrl-C

<!-- sq:subtask:ST4:body -->
On `prompt`: write the output, show the text on the stream the answer names, read one line or end of input, resend with it appended to `answers`; a daemon lost between the phases runs the command locally from the start. Fall back before sending (no daemon and a failed start, a refused or reset connection before the request is fully written, an unreadable file, `503 not_executed`); after sending, no replay: a lost connection, a timeout or Ctrl-C prints the "may still complete" error, exit 1 or 130. No memory between invocations. Answer timeouts: a literal table of the `long` command paths, unless the architect rules otherwise.

Tests: cross-process, the shim falling back on a refused connection (1); the daemon killed between the phases of a prompt, the shim asking again locally with nothing written (1); the existing no-replay and Ctrl-C members re-pointed. Guard: the `long` table equal to the operations classed `long` (1, if the table stands).
<!-- sq:subtask:ST4:body:end -->

#### Discussion

<!-- sq:subtask:ST4:discussion -->
<!-- sq:subtask:ST4:discussion:end -->
<!-- sq:subtask:ST4:end -->

<!-- sq:subtask:ST5 -->
### ST5 — Daemon start from the shim and the Windows transport

<!-- sq:subtask:ST5:body -->
Starting a daemon from the shim (ADR-1052 point 11, 5 s bound): the start code reached only on the start path and stdlib-only, `filelock` replaced by a stdlib lock probe or the stale check moved into the spawned daemon; the handback names the modules the start path adds. Native Windows: the loopback CLI port with ADR-1052 point 5's admission headers and no `Origin`, the port-reuse identity check, the detached spawn.

Tests: the existing implicit-start, discovery and Windows detached-spawn members re-pointed at the shim. No new case.
<!-- sq:subtask:ST5:body:end -->

#### Discussion

<!-- sq:subtask:ST5:discussion -->
<!-- sq:subtask:ST5:discussion:end -->
<!-- sq:subtask:ST5:end -->

<!-- sq:subtask:ST6 -->
### ST6 — The CLI off HttpApi, the TUI's selection kept

<!-- sq:subtask:ST6:body -->
ADR-1261 point 8: a CLI process uses `LocalApi` (the shim's local fall back or a served command); `call()` still takes an `Api` handed in on the context, which the route-parity mode uses. `HttpApi`, endpoint re-resolution and the vocabulary hash stay for the TUI: its per-call selection (`session_api`, `SelectedApi`) moves out of `_cli/_calls.py` if the CLI no longer needs it. Tests whose subject was the CLI's own selection (`tests/daemon/test_remote_refusals.py`, the session cases in `tests/cross_process/test_a_daemon_that_goes_away_and_unusable_settings.py`) are re-homed on the TUI's selector or the route mode, or retired with their subject; one line each in the handback.

Tests: no new case; the route-parity run holds every operation over HTTP.
<!-- sq:subtask:ST6:body:end -->

#### Discussion

<!-- sq:subtask:ST6:discussion -->
<!-- sq:subtask:ST6:discussion:end -->
<!-- sq:subtask:ST6:end -->

<!-- sq:subtask:ST7 -->
### ST7 — Client budget: the shim's overhead, benchmark and runbook

<!-- sq:subtask:ST7:body -->
The budget of ADR-1261 point 10, which replaces TASK-1219 ST8's: the shim's overhead (wall time minus the handler time sent with the answer), median of 31 interleaved runs of `sq task <n> show`, at most 100 ms on the GitHub-hosted Linux runner. `scripts/bench_remote_client.py` measures it, plus `--json` and a bash completion; the `releasing-squads` skill's runbook step names the criterion (edited through `sq skill`). Measure on the development host and report median and p25-p75 with the load average; the runner figure comes from the CI task's report.

Tests: none; the benchmark is a report.
<!-- sq:subtask:ST7:body:end -->

#### Discussion

<!-- sq:subtask:ST7:discussion -->
<!-- sq:subtask:ST7:discussion:end -->
<!-- sq:subtask:ST7:end -->
<!-- sq:subtasks:end -->

## Discussion

<!-- sq:discussion -->
<!-- sq:discussion:end -->
