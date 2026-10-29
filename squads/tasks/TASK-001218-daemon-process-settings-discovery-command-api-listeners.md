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
- local_id: ST8
  title: Prompt after a commit fails instead of retrying
  status: Todo
  story: US3
- local_id: ST9
  title: Typer help and usage output follow the request
  status: Todo
  story: US3
- local_id: ST10
  title: Endpoint surface tests for the seeded request path
  status: Todo
  story: US10
created_at: '2026-10-28T14:08:41Z'
updated_at: '2026-10-28T19:17:52Z'
---
<!-- sq:body -->
## Goal

The daemon process itself: its settings, where it lives and how it is found, the HTTP application with its three routes, the request scope that runs one command at a time, configuration retirement, the TCP listeners with their admission rules, and `sq daemon run|status|stop`. After this task a daemon can be started by hand and driven with any HTTP client; the CLI does not use it yet (the forwarder is a separate task).

## What it builds

- **Settings (ADR-1052 point 7).** A tolerant `[daemon]` table on `SquadsConfig` (`src/squads/_models/_config.py`), on the `[display]` model: `enabled = true`, `idle_timeout_minutes = 30` (0 = never), `browser = false`; unusable values fall back and are recorded, unknown keys recorded; `to_toml()` writes the table only when a value differs from its default, so `init`/adopt add no lines and the legacy-key regeneration in `sq migrate up` (`_migrations/_config_text.py`) keeps it. `SQUADS_DAEMON=on|off` overrides `enabled`; any other value is unusable. A new `sq check` rule beside `_display_config_valid` (`src/squads/_services/_validators.py`), declared in the bundled workflow spec, reports unknown keys, unusable values and an unusable `SQUADS_DAEMON`.
- **Endpoint resolution, shared (point 9).** One stdlib-only module (no pydantic, no rich, importable before `squads._cli`) that goes from a client directory plus `-C` values to the squad directory (the `.squads.toml` walk-up of `_paths.find_config`, reading `squad_dir` and `[daemon]` with `tomllib`) and from there to the effective daemon setting and the endpoint. `SquadsConfig`'s reading of `[daemon]` and the CLI's `effective_dir` use it, so the daemon, the forwarder and `sq check` cannot disagree. Its input stays open to a configured remote address later (FEAT-33), with no change here.
- **Runtime directory and key (point 8).** Key = short hash of the squad directory's real path, the squads version and the installed package directory. Location: `$XDG_RUNTIME_DIR/squads/` (Linux, WSL2), per-user `$TMPDIR` (macOS), `%LOCALAPPDATA%` (Windows), else a `0700` directory under the user cache dir; never in the squad. Unusable when missing, wrong owner or mode, or the socket path exceeds `sun_path`. Files per key: `.sock` (POSIX, `0600`), `.json` (pid, version, squad real path, every TCP port), `.lock` held for the lifetime, `.log` (the daemon's stderr for its current lifetime).
- **HTTP application (points 1-3).** Stdlib `http.server` on a `socketserver` Unix stream server (POSIX) and TCP servers, one connection per request. `POST /v1/commands` (body: `argv`, `cwd`, `env` limited to the eight listed variables, `terminal`, `attachments`; response `{exit_code, stdout, stderr}`, HTTP 200 whenever the command ran); `GET /v1/daemon` (pid, version, squad real path, listeners, start time, idle deadline); `POST /v1/daemon/stop` (exit after the command in progress). Refusals: `421`/`403` from admission before routing; `503 {"not_executed": "retiring" | "other_squad" | "needs_terminal"}` before any of the command ran.
- **Request scope (point 12).** One context manager beside `compose_service` in `src/squads/_services/_service.py`: commands run strictly one at a time in arrival order on one worker thread, identity and stop answered off that worker. Per command: a new empty `contextvars.Context`; a `RequestContext` seeded from the request (client directory, attachments, terminal facts, the documents loaded at startup through `resolve_documents`); stdin/stdout/stderr pointed at the request's buffers and the listed env variables set to the client's values, both restored after; then the in-process entry (`squads._cli.run`). The root callback consumes the seeded `documents` instead of loading the spec, playbook and catalog again, so each document is loaded once per daemon lifetime (ADR-1128). `other_squad` when the command line resolves to another squad; a `NeedsTerminal` signal raised before anything committed becomes `503 needs_terminal`; one raised after a transaction committed in the request fails the command with an error instead (point 12). No squad data kept between commands.
- **Configuration retirement (point 13).** Fingerprint at start: the bytes of `.squads.toml` and the names and bytes of every file under `<squad-dir>/.overrides/`. Compared before each command; any difference answers `retiring` and exits. `sq override` and `sq migrate up` retire it the same way, through the next comparison.
- **Writes and corpus operations (points 14-15).** Every write goes through the unchanged service code and `IndexStore.transaction()` (`src/squads/_index/_store.py`); `migrate up`, `repair`, `repad`, `renumber` run like any command; the schema check runs per command through the root callback, so a daemon older than the squad's schema refuses with the old CLI's message.
- **Lifecycle (point 11).** `sq daemon run` (hidden; spawned by the client) takes `<key>.lock` or exits as already running, writes its files, reports `ready` or one failure line on an inherited pipe and closes it, exits after `idle_timeout_minutes` without a request (a running command counts as activity), removes its four files on a clean exit, and replaces a crashed predecessor's log. `sq daemon status` (`--json`) and `sq daemon stop` (waits until the files are gone; exit 0 with none running). The `daemon` group always runs locally.
- **TCP listeners and admission (points 4-6).** Native Windows: a loopback CLI port, always on while the daemon runs. Every platform: the browser port when `browser = true`, bound to `127.0.0.1` (and `::1` if dual-stacked) on an ephemeral port, never a non-loopback address, serving the same routes, writes included. Admission on every TCP listener: `Host` exactly `127.0.0.1:<port>`, `localhost:<port>` or `[::1]:<port>`; no CORS headers, no preflight answered; `GET` never mutates; every other method requires `Content-Type: application/json` and `Squads-Client: 1`; the browser port requires `Origin` equal to its own origin on non-`GET`; the Windows CLI port refuses any `Origin`. No authentication.

## Wire encoding (ADR-1052 point 1)

- Request and response bodies are UTF-8 JSON. `argv`, `cwd`, the `env` values, `stdout` and `stderr` are JSON strings; the output is the text the command wrote, captured before any encoding to bytes. A lone surrogate (an undecodable POSIX file name or argument) travels as its `\u` escape and round-trips exactly.
- `terminal` carries, beside the tty flags and size, the encoding of each of the three streams. The request scope's stream buffers report the client's encodings, so Rich's encoding-dependent choices (box drawing, ASCII fallback) match local mode. `TerminalFacts` in `src/squads/_context.py` gains those fields here.
- `attachments` is an object keyed by each file argument exactly as the command line writes it (`-` for stdin), valued by the content in base64 (RFC 4648, standard alphabet, padded). The daemon decodes a `--file` attachment as UTF-8 as `client_path` reading does, and reads an attached stdin through a text stream with the client's stdin encoding, so a non-UTF-8 file fails the same way in both modes.
- The custom header is `Squads-Client: 1` (name case-insensitive, value exactly `1`). Clients send it on every listener, the Unix socket included.
- `sq daemon run` is hidden from `--help` and from the adopter documentation; its start-report pipe is a private protocol. It still runs by hand in the foreground for diagnosis.

## Acceptance

US1 (endpoint, fresh scope per command, errors identical), US2 (peer under the lock, cross-mode visibility, schema-older refusal), US4 (singleton, staleness files, idle exit, retirement on config/override edits, status/stop), US5 (settings, validation, `SQUADS_DAEMON`, absent keys harmless), US6 server side (loopback CLI port, admission rules), US7 (browser listener off by default, loopback only, own-origin writes). ADR-1052 Consequences: the negative test per admission rule.

## Test approach

Per ADR-1172: endpoint tests follow "The daemon's command endpoint" (in-process harness serving the HTTP app on a thread, whole response asserted, state read through `invoke … show --json`, no `covers` marker); `sq daemon` and `sq check` cases are ordinary surface cases with `covers`/`breaches` markers. One case per behaviour plus its boundary refusals; each subtask names its cases.

- Commands that already have a surface case (`repair`, `migrate up`, every read) reach the endpoint through the remote-mode run (ADR-1172 "Mode parity", TASK-1219 ST6), not new cases.
- Built and not tested: idle exit (ADR-1052 point 11), the post-commit prompt branch (ADR-1052 point 12), and the lock singleton, crash leftovers and two writers in separate processes, none of which is a member of ADR-1172 "The cross-process set".
- Expected size: about 45 new in-process tests.
- Falsify each case once when written: break the behaviour, see it red, restore.
<!-- sq:body:end -->

## Subtasks

_Add with `sq task 1218 add-subtask "<title>"`; track with `sq task 1218 subtask <n> update --status <Status>`._

<!-- sq:subtasks -->

<!-- sq:subtask:ST1 -->
### ST1 — [daemon] table, SQUADS_DAEMON and the check rule

<!-- sq:subtask:ST1:body -->
Tolerant `[daemon]` model on `SquadsConfig` (enabled, idle_timeout_minutes with 0 = never, browser), written by `to_toml()` only when non-default and kept by the legacy-key regeneration of `migrate up`; `SQUADS_DAEMON=on|off` precedence; a `sq check` rule declared in the bundled spec for unknown keys, unusable values and an unusable env value. Tests (surface): in `tests/check/`, three breach cases with their `breaches` marker (an unusable `[daemon]` value, an unknown key, an unusable `SQUADS_DAEMON`), asserting the whole `sq check` finding line; one `sq migrate up` case on a legacy-key squad whose regenerated `.squads.toml` keeps a non-default table. Which mode a command takes under a setting is held by the fall back member of the cross-process set (ADR-1172 "The cross-process set"). About 4 new tests.
<!-- sq:subtask:ST1:body:end -->

#### Discussion

<!-- sq:subtask:ST1:discussion -->
<!-- sq:subtask:ST1:discussion:end -->
<!-- sq:subtask:ST1:end -->

<!-- sq:subtask:ST2 -->
### ST2 — Shared endpoint resolution, key and runtime directory

<!-- sq:subtask:ST2:body -->
Stdlib-only module from client dir + `-C` values to squad dir, effective daemon setting and endpoint; used by `SquadsConfig`, `effective_dir`, the daemon and the forwarder. Key from squad real path, version and package dir; per-platform runtime directory with owner/mode/`sun_path` checks; the four files per key. Tests (surface): with the endpoint harness serving the squad, `sq daemon status --json` through `invoke` with `-C` pointing into a subfolder of the squad reports the serving daemon (whole JSON); from another squad it reports none running. About 2 new tests; the path forms `-C` accepts are already root-option cases. An unusable runtime directory is a failed start, held by the fall back member (ADR-1172 "The cross-process set").
<!-- sq:subtask:ST2:body:end -->

#### Discussion

<!-- sq:subtask:ST2:discussion -->
<!-- sq:subtask:ST2:discussion:end -->
<!-- sq:subtask:ST2:end -->

<!-- sq:subtask:ST3 -->
### ST3 — HTTP app, three routes and the serial request scope

<!-- sq:subtask:ST3:body -->
Stdlib `http.server` over a Unix stream server and TCP servers; `POST /v1/commands`, `GET /v1/daemon`, `POST /v1/daemon/stop`; one worker thread in arrival order; per command a fresh `contextvars.Context`, a seeded `RequestContext`, stdio and listed env patched and restored, then `squads._cli.run`. Wire encoding per ADR-1052 point 1: UTF-8 JSON, output captured as text before encoding, lone surrogates as `\u` escapes; `TerminalFacts` gains each stream's encoding and the stream buffers report the client's; attachments base64, keyed by the literal token, `--file` decoded as UTF-8 and stdin through a text stream in the client's stdin encoding. The root callback consumes the seeded `documents` rather than reloading them. `other_squad` and `needs_terminal` refusals before anything runs. Tests (surface, endpoint harness, whole response asserted): one case per route (3); `other_squad` with a `-C` naming another squad (1); a non-UTF-8 attachment failing with local mode's whole message and an ascii client stdout giving local mode's ASCII rendering (2). About 6 new tests. Load-once of the documents is not observable through a surface and gets no test here.
<!-- sq:subtask:ST3:body:end -->

#### Discussion

<!-- sq:subtask:ST3:discussion -->
<!-- sq:subtask:ST3:discussion:end -->
<!-- sq:subtask:ST3:end -->

<!-- sq:subtask:ST4 -->
### ST4 — Writes, corpus operations and schema skew through the daemon

<!-- sq:subtask:ST4:body -->
Writes go through unchanged service code and `IndexStore.transaction()`; `migrate up`, `repair`, `repad`, `renumber` run as commands; a daemon older than the squad schema refuses with the old CLI message. Tests (surface): a `create` sent to the endpoint read back by `invoke … show --json`, and a write made with `invoke` read through the endpoint; `repair`, `repad`, `renumber` and `migrate up` through the endpoint come from the remote-mode run of their existing surface cases (TASK-1219 ST6), not new tests; a squad stamped with a newer schema refused through the endpoint with local mode's whole message. Two writers in separate processes serialise on the existing file lock and are not in the cross-process set, so they get no new test. About 3 new tests.
<!-- sq:subtask:ST4:body:end -->

#### Discussion

<!-- sq:subtask:ST4:discussion -->
<!-- sq:subtask:ST4:discussion:end -->
<!-- sq:subtask:ST4:end -->

<!-- sq:subtask:ST5 -->
### ST5 — Lifecycle, retirement and sq daemon commands

<!-- sq:subtask:ST5:body -->
`sq daemon run` (hidden): lock singleton, ready/failure line on the pipe, idle exit with a running command counted as activity, files removed on clean exit, crashed log replaced. Fingerprint of `.squads.toml` and every file under `.overrides/`, compared per command, `retiring` on change. `sq daemon status` (`--json`) and idempotent `sq daemon stop`. Tests (surface, `invoke` with `covers` markers, endpoint harness for a running daemon): `daemon status` with a daemon and with none, `--json` once; `daemon stop` with one running (then `status --json` reports none) and with none (exit 0, whole message); `daemon run` refused as already running while the harness holds the key. Retirement: an edited `.squads.toml` and an override scaffolded by `sq override` each answer `retiring` (the fingerprint covers files, so two inputs prove both roots). About 8 new tests. Idle exit is built and not tested (ADR-1052 point 11). The lock singleton and crash leftovers are not members of the cross-process set (ADR-1172 "The cross-process set") and get no test; the start pipe is exercised by its implicit-start member.
<!-- sq:subtask:ST5:body:end -->

#### Discussion

<!-- sq:subtask:ST5:discussion -->
<!-- sq:subtask:ST5:discussion:end -->
<!-- sq:subtask:ST5:end -->

<!-- sq:subtask:ST6 -->
### ST6 — TCP listeners and admission rules

<!-- sq:subtask:ST6:body -->
Native Windows loopback CLI port, always on; `Host` allow-list, no CORS or preflight, `Content-Type: application/json` plus `Squads-Client: 1` (name case-insensitive, value exactly `1`) on every non-GET, any `Origin` refused on the Windows CLI port. Tests (surface, endpoint harness over TCP, whole HTTP status and body asserted): one negative case per rule from ADR-1052's Consequences (rebinding `Host`, form post, `text/plain` body, missing and wrong `Squads-Client`, any `Origin` on the Windows CLI port) and the positive request. About 7 new tests, each a distinct rule. The Windows CLI port cases run in this same suite on the Windows runner and skip by platform elsewhere. Falsify each case by disabling its check.
<!-- sq:subtask:ST6:body:end -->

#### Discussion

<!-- sq:subtask:ST6:discussion -->
<!-- sq:subtask:ST6:discussion:end -->
<!-- sq:subtask:ST6:end -->

<!-- sq:subtask:ST7 -->
### ST7 — Browser listener, off by default

<!-- sq:subtask:ST7:body -->
Opened only when `browser = true`; binds `127.0.0.1` (and `::1` if dual-stacked) on an ephemeral port, never a non-loopback address; serves the same routes, writes included; non-GET requires `Origin` equal to its own origin; listed in `<key>.json` and `GET /v1/daemon`. No authentication. Tests (surface): `sq daemon status --json` lists no browser listener by default and a loopback one with `browser = true`; through that listener, a write with its own `Origin` succeeds (read back by `invoke … show --json`), a foreign `Origin` is refused with the whole response asserted. About 3 new tests.
<!-- sq:subtask:ST7:body:end -->

#### Discussion

<!-- sq:subtask:ST7:discussion -->
<!-- sq:subtask:ST7:discussion:end -->
<!-- sq:subtask:ST7:end -->

<!-- sq:subtask:ST8 -->
### ST8 — Prompt after a commit fails instead of retrying

<!-- sq:subtask:ST8:body -->
ADR-1052 point 12: a prompt reached after a transaction has committed in the request fails the command with an error instead of answering `needs_terminal`, because the client would otherwise replay a command whose write already landed. The request scope records that a commit happened in the current request (a request-scoped flag set from the commit path of `IndexStore.transaction()`, not module state) and turns a `NeedsTerminal` raised after it into the command's error exit with a clear message. Carries REV-1223 F6.

Also carries REV-1223 F8 (first point): a command can write output before it signals (comment removal prints the matching comments before `confirm_or_signal` raises `NeedsTerminal`). When the scope turns the signal into `503 needs_terminal`, it discards that request's buffered stdout and stderr.

Tests (surface, endpoint harness): comment removal sent without a terminal answers `503 needs_terminal` with no output in the body and `invoke … show --json` shows the comment still there (the signal and F8's discard in one case); the other prompting commands share the helper and get no repeat. About 1 new test. The post-commit branch has no surface that reaches it, since every prompting command asks before it writes; it is built untested (ADR-1052 point 12).
<!-- sq:subtask:ST8:body:end -->

#### Discussion

<!-- sq:subtask:ST8:discussion -->
<!-- sq:subtask:ST8:discussion:end -->
<!-- sq:subtask:ST8:end -->

<!-- sq:subtask:ST9 -->
### ST9 — Typer help and usage output follow the request

<!-- sq:subtask:ST9:body -->
Carries REV-1223 F3. Typer renders `--help` and click usage errors through its own consoles (`typer.rich_utils._get_rich_console`), not the CLI's per-invocation consoles, and takes `FORCE_COLOR` from `typer.rich_utils.FORCE_TERMINAL`, computed once at import from the daemon's environment. In the request scope, the patched stdio buffers report the client's `isatty` and encodings, and the colour decision for Typer's consoles follows the request's `FORCE_COLOR`/`NO_COLOR`/`TERM` rather than the daemon's import-time value, so help and usage errors match local mode and a daemon started with `FORCE_COLOR` does not colour other clients' help. Tests (surface, endpoint harness): `--help` from a terminal client and a usage error (exit 2) from a terminal client, each asserting the whole response equals what `invoke` gives under the same terminal facts; a harness started with `FORCE_COLOR=1` serving a pipe client gives uncoloured help. About 3 new tests. Falsify by leaving the import-time value in place.
<!-- sq:subtask:ST9:body:end -->

#### Discussion

<!-- sq:subtask:ST9:discussion -->
<!-- sq:subtask:ST9:discussion:end -->
<!-- sq:subtask:ST9:end -->

<!-- sq:subtask:ST10 -->
### ST10 — Endpoint surface tests for the seeded request path

<!-- sq:subtask:ST10:body -->
The seeded-path behaviours of the in-process command entry that no `sq` command shows in local mode, tested through the command endpoint (US1, US10) instead of by calling the entry or `read_client_text` (ADR-1172 "The daemon's command endpoint"). Endpoint harness, whole response asserted, state read back by `invoke … show --json`:
- Isolation between commands: a request with `--at`, then one without, shows the real clock; a request whose `env` sets `SQUADS_SESSION_ID`, then one without, attributes the second write without it; a request with a narrow `COLUMNS`, then one without, renders at the default width. One case per carried value, no combinations.
- Attachments: a relative `--file` body and `-` (stdin) for `import`, each served from `attachments`; an unattached file argument refused with its whole message and nothing written.
- Start directory: `cwd` in a squad subfolder resolves the squad as local mode does from there.
- Prompt signalling: covered by ST8's cases.
- Terminal facts to consoles: a terminal client of fixed width and colour system gets the same styled output as `invoke` under those facts; a pipe client gets plain output.
Each case falsified once when written. About 9 new tests.
<!-- sq:subtask:ST10:body:end -->

#### Discussion

<!-- sq:subtask:ST10:discussion -->
<!-- sq:subtask:ST10:discussion:end -->
<!-- sq:subtask:ST10:end -->
<!-- sq:subtasks:end -->

## Discussion

<!-- sq:discussion -->
<!-- sq:discussion:end -->
