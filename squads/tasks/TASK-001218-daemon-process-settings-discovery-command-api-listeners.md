---
id: TASK-1218
sequence_id: 1218
type: task
title: 'Daemon process: settings, discovery, command API, listeners'
status: Draft
parent: FEAT-1140
author: tech-lead
priority: high
refs:
- ADR-1052:implements
- TASK-1217:depends-on
description: '[daemon] settings and check rule, shared endpoint resolution, runtime
  files, the three routes, serial request scope, retirement, lifecycle, TCP admission'
subentities:
- local_id: ST1
  title: '[daemon] table, SQUADS_DAEMON and the check rule'
  status: Todo
  story: US5
- local_id: ST2
  title: Shared endpoint resolution, key and runtime directory
  status: Todo
  story: US4
- local_id: ST3
  title: HTTP app, three routes and the serial request scope
  status: Todo
  story: US1
- local_id: ST4
  title: Writes, corpus operations and schema skew through the daemon
  status: Todo
  story: US2
- local_id: ST5
  title: Lifecycle, retirement and sq daemon commands
  status: Todo
  story: US4
- local_id: ST6
  title: TCP listeners and admission rules
  status: Todo
  story: US6
- local_id: ST7
  title: Browser listener, off by default
  status: Todo
  story: US7
created_at: '2026-10-28T14:08:41Z'
updated_at: '2026-10-28T14:09:51Z'
---
<!-- sq:body -->
## Goal

The daemon process itself: its settings, where it lives and how it is found, the HTTP application with its three routes, the request scope that runs one command at a time, configuration retirement, the TCP listeners with their admission rules, and `sq daemon run|status|stop`. After this task a daemon can be started by hand and driven with any HTTP client; the CLI does not use it yet (the forwarder is a separate task).

## What it builds

- **Settings (ADR-1052 point 7).** A tolerant `[daemon]` table on `SquadsConfig` (`src/squads/_models/_config.py`), on the `[display]` model: `enabled = true`, `idle_timeout_minutes = 30` (0 = never), `browser = false`; unusable values fall back and are recorded, unknown keys recorded; `to_toml()` writes the table only when a value differs from its default, so `init`/adopt add no lines and the legacy-key regeneration in `sq migrate up` (`_migrations/_config_text.py`) keeps it. `SQUADS_DAEMON=on|off` overrides `enabled`; any other value is unusable. A new `sq check` rule beside `_display_config_valid` (`src/squads/_services/_validators.py`), declared in the bundled workflow spec, reports unknown keys, unusable values and an unusable `SQUADS_DAEMON`.
- **Endpoint resolution, shared (point 9).** One stdlib-only module (no pydantic, no rich, importable before `squads._cli`) that goes from a client directory plus `-C` values to the squad directory (the `.squads.toml` walk-up of `_paths.find_config`, reading `squad_dir` and `[daemon]` with `tomllib`) and from there to the effective daemon setting and the endpoint. `SquadsConfig`'s reading of `[daemon]` and the CLI's `effective_dir` use it, so the daemon, the forwarder and `sq check` cannot disagree. Its input stays open to a configured remote address later (FEAT-33), with no change here.
- **Runtime directory and key (point 8).** Key = short hash of the squad directory's real path, the squads version and the installed package directory. Location: `$XDG_RUNTIME_DIR/squads/` (Linux, WSL2), per-user `$TMPDIR` (macOS), `%LOCALAPPDATA%` (Windows), else a `0700` directory under the user cache dir; never in the squad. Unusable when missing, wrong owner or mode, or the socket path exceeds `sun_path`. Files per key: `.sock` (POSIX, `0600`), `.json` (pid, version, squad real path, every TCP port), `.lock` held for the lifetime, `.log` (the daemon's stderr for its current lifetime).
- **HTTP application (points 1-3).** Stdlib `http.server` on a `socketserver` Unix stream server (POSIX) and TCP servers, one connection per request. `POST /v1/commands` (body: `argv`, `cwd`, `env` limited to the eight listed variables, `terminal`, `attachments`; response `{exit_code, stdout, stderr}`, HTTP 200 whenever the command ran); `GET /v1/daemon` (pid, version, squad real path, listeners, start time, idle deadline); `POST /v1/daemon/stop` (exit after the command in progress). Refusals: `421`/`403` from admission before routing; `503 {"not_executed": "retiring" | "other_squad" | "needs_terminal"}` before any of the command ran.
- **Request scope (point 12).** One context manager beside `compose_service` in `src/squads/_services/_service.py`: commands run strictly one at a time in arrival order on one worker thread, identity and stop answered off that worker. Per command: a new empty `contextvars.Context`; a `RequestContext` seeded from the request (client directory, attachments, terminal facts, the documents loaded at startup through `resolve_documents`); stdin/stdout/stderr pointed at the request's buffers and the listed env variables set to the client's values, both restored after; then the in-process entry from the CLI-entry task. `other_squad` when the command line resolves to another squad; a prompt signal becomes `needs_terminal`, or an error if a transaction already committed in the request. No squad data kept between commands.
- **Configuration retirement (point 13).** Fingerprint at start: the bytes of `.squads.toml` and the names and bytes of every file under `<squad-dir>/.overrides/`. Compared before each command; any difference answers `retiring` and exits. `sq override` and `sq migrate up` retire it the same way, through the next comparison.
- **Writes and corpus operations (points 14-15).** Every write goes through the unchanged service code and `IndexStore.transaction()` (`src/squads/_index/_store.py`); `migrate up`, `repair`, `repad`, `renumber` run like any command; the schema check runs per command through the root callback, so a daemon older than the squad's schema refuses with the old CLI's message.
- **Lifecycle (point 11).** `sq daemon run` (hidden; spawned by the client) takes `<key>.lock` or exits as already running, writes its files, reports `ready` or one failure line on an inherited pipe and closes it, exits after `idle_timeout_minutes` without a request (a running command counts as activity), removes its four files on a clean exit, and replaces a crashed predecessor's log. `sq daemon status` (`--json`) and `sq daemon stop` (waits until the files are gone; exit 0 with none running). The `daemon` group always runs locally.
- **TCP listeners and admission (points 4-6).** Native Windows: a loopback CLI port, always on while the daemon runs. Every platform: the browser port when `browser = true`, bound to `127.0.0.1` (and `::1` if dual-stacked) on an ephemeral port, never a non-loopback address, serving the same routes, writes included. Admission on every TCP listener: `Host` exactly `127.0.0.1:<port>`, `localhost:<port>` or `[::1]:<port>`; no CORS headers, no preflight answered; `GET` never mutates; every other method requires `Content-Type: application/json` and the fixed custom header; the browser port requires `Origin` equal to its own origin on non-`GET`; the Windows CLI port refuses any `Origin`. No authentication.

## Open in the ADR, to settle before or during this task

- The fixed custom header's name and value are not named by ADR-1052 (point 5). It becomes part of the documented API.
- Wire encoding: `stdout`/`stderr` as JSON strings (the CLI writes UTF-8 text) and how attachment content is carried (text vs base64) are not fixed.
- Whether `sq daemon run` is hidden from `--help`.

## Acceptance

US1 (endpoint, fresh scope per command, errors identical), US2 (peer under the lock, cross-mode visibility, schema-older refusal), US4 (singleton, staleness files, idle exit, retirement on config/override edits, status/stop), US5 (settings, validation, `SQUADS_DAEMON`, absent keys harmless), US6 server side (loopback CLI port, admission rules), US7 (browser listener off by default, loopback only, own-origin writes). ADR-1052 Consequences: the negative test per admission rule.

## Test approach

- Settings: a table over every key x {absent, default, valid non-default, wrong type, negative, unknown key} plus `SQUADS_DAEMON` x {unset, on, off, ON, empty, garbage}, asserting the effective setting, the recorded problem and the `to_toml()` round trip, including a legacy-key `migrate up` regeneration that keeps a non-default `[daemon]`. The check rule needs its breach test (`@pytest.mark.breaches`). The spec change puts `tests/meta`, `tests/integration` and `tests/cli` in the run.
- Resolution: one table of client directory x `-C` shapes (relative, absolute, symlinked, repeated, walk-up from a subfolder, none) asserting the key is identical where the squad is, and that `effective_dir` and the resolver agree on every row.
- Request scope: back-to-back commands through the real HTTP app asserting no leakage (the same rows as the CLI-entry task, now over the wire); a write via the daemon read by an in-process local command and the reverse; two writers at once (daemon + local subprocess) leaving `sq repair` with nothing to fix.
- Retirement: one row per fingerprinted input (`.squads.toml`, each override document, a per-role override, a template override, a new file, a deleted file, a same-size same-mtime edit).
- Admission: one negative row per rule from the ADR's Consequences on each TCP listener, plus the positive JSON+header request. Falsify each row by disabling its check.
- Lifecycle: two `daemon run` at once leave one daemon; SIGKILL leaves files that the next start replaces; idle 1-second timeout exits and cleans.
- Native Windows paths (TCP CLI port, `%LOCALAPPDATA%`, lock release on termination) run on the CI Windows runner; locally they are covered only by the platform-independent rows.
<!-- sq:body:end -->

## Subtasks

_Add with `sq task 1218 add-subtask "<title>"`; track with `sq task 1218 subtask <n> update --status <Status>`._

<!-- sq:subtasks -->

<!-- sq:subtask:ST1 -->
### ST1 — [daemon] table, SQUADS_DAEMON and the check rule

<!-- sq:subtask:ST1:body -->
Tolerant `[daemon]` model on `SquadsConfig` (enabled, idle_timeout_minutes with 0 = never, browser), written by `to_toml()` only when non-default and kept by the legacy-key regeneration of `migrate up`; `SQUADS_DAEMON=on|off` precedence; a `sq check` rule (declared in the bundled spec, with its breach test) for unknown keys, unusable values and an unusable env value. Table over key x value shape x env value.
<!-- sq:subtask:ST1:body:end -->

#### Discussion

<!-- sq:subtask:ST1:discussion -->
<!-- sq:subtask:ST1:discussion:end -->
<!-- sq:subtask:ST1:end -->

<!-- sq:subtask:ST2 -->
### ST2 — Shared endpoint resolution, key and runtime directory

<!-- sq:subtask:ST2:body -->
Stdlib-only module from client dir + `-C` values to squad dir, effective daemon setting and endpoint; used by `SquadsConfig`, `effective_dir`, the daemon and the forwarder. Key from squad real path, version and package dir; per-platform runtime directory with owner/mode/`sun_path` checks; the four files per key. Table over `-C`/symlink/walk-up shapes asserting one key and agreement with `effective_dir`.
<!-- sq:subtask:ST2:body:end -->

#### Discussion

<!-- sq:subtask:ST2:discussion -->
<!-- sq:subtask:ST2:discussion:end -->
<!-- sq:subtask:ST2:end -->

<!-- sq:subtask:ST3 -->
### ST3 — HTTP app, three routes and the serial request scope

<!-- sq:subtask:ST3:body -->
Stdlib `http.server` over a Unix stream server and TCP servers; `POST /v1/commands`, `GET /v1/daemon`, `POST /v1/daemon/stop`; one worker thread in arrival order; per command a fresh `contextvars.Context`, a seeded `RequestContext`, stdio and listed env patched and restored, then the in-process entry. `other_squad` and `needs_terminal` refusals before anything runs. Isolation pairs over the wire.
<!-- sq:subtask:ST3:body:end -->

#### Discussion

<!-- sq:subtask:ST3:discussion -->
<!-- sq:subtask:ST3:discussion:end -->
<!-- sq:subtask:ST3:end -->

<!-- sq:subtask:ST4 -->
### ST4 — Writes, corpus operations and schema skew through the daemon

<!-- sq:subtask:ST4:body -->
Writes go through unchanged service code and `IndexStore.transaction()`; `migrate up`, `repair`, `repad`, `renumber` run as commands; a daemon older than the squad schema refuses with the old CLI message. Tests: daemon write read by a local command and the reverse; daemon and local writers at once leave `sq repair` nothing to fix.
<!-- sq:subtask:ST4:body:end -->

#### Discussion

<!-- sq:subtask:ST4:discussion -->
<!-- sq:subtask:ST4:discussion:end -->
<!-- sq:subtask:ST4:end -->

<!-- sq:subtask:ST5 -->
### ST5 — Lifecycle, retirement and sq daemon commands

<!-- sq:subtask:ST5:body -->
`sq daemon run` (hidden): lock singleton, ready/failure line on the pipe, idle exit with a running command counted as activity, files removed on clean exit, crashed log replaced. Fingerprint of `.squads.toml` and every file under `.overrides/`, compared per command, `retiring` on change. `sq daemon status` (`--json`) and idempotent `sq daemon stop`. One retirement row per fingerprinted input, same-size same-tick edit included.
<!-- sq:subtask:ST5:body:end -->

#### Discussion

<!-- sq:subtask:ST5:discussion -->
<!-- sq:subtask:ST5:discussion:end -->
<!-- sq:subtask:ST5:end -->

<!-- sq:subtask:ST6 -->
### ST6 — TCP listeners and admission rules

<!-- sq:subtask:ST6:body -->
Native Windows loopback CLI port, always on; `Host` allow-list, no CORS or preflight, JSON content type plus the fixed custom header on every non-GET, any `Origin` refused on the Windows CLI port. One negative test per rule from the ADR's Consequences, each falsified by disabling its check. The custom header name is open in the ADR.
<!-- sq:subtask:ST6:body:end -->

#### Discussion

<!-- sq:subtask:ST6:discussion -->
<!-- sq:subtask:ST6:discussion:end -->
<!-- sq:subtask:ST6:end -->

<!-- sq:subtask:ST7 -->
### ST7 — Browser listener, off by default

<!-- sq:subtask:ST7:body -->
Opened only when `browser = true`; binds `127.0.0.1` (and `::1` if dual-stacked) on an ephemeral port, never a non-loopback address; serves the same routes, writes included; non-GET requires `Origin` equal to its own origin; listed in `<key>.json` and `GET /v1/daemon`. No authentication. Tests: off by default, bind address assertion, foreign and missing `Origin` refused.
<!-- sq:subtask:ST7:body:end -->

#### Discussion

<!-- sq:subtask:ST7:discussion -->
<!-- sq:subtask:ST7:discussion:end -->
<!-- sq:subtask:ST7:end -->
<!-- sq:subtasks:end -->

## Discussion

<!-- sq:discussion -->
<!-- sq:discussion:end -->
