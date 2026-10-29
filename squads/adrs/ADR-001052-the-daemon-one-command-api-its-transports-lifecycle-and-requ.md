---
id: ADR-1052
sequence_id: 1052
type: decision
title: 'The daemon: one command API, its transports, lifecycle and requests'
status: Accepted
author: architect
refs:
- MILE-868
- EPIC-29
- FEAT-33
- FEAT-916
- ADR-1128
- FEAT-1140
- MILE-1152
description: One HTTP command endpoint the CLI forwards to and the browser shares;
  Unix socket on POSIX, loopback ports on Windows and for the browser; serial commands
  in a fresh scope; edited configuration retires the daemon
created_at: '2026-10-16T11:27:26Z'
updated_at: '2026-10-28T18:28:02Z'
---
<!-- sq:body -->
## Context

The 0.18 line (MILE-1152, FEAT-1140) adds a squads daemon: a long-lived local process that serves squad state over an API. The browser frontend (MILE-868) builds on it. The operator has settled the frame (MILE-868, MILE-1051 and this ADR's discussion, 2026-10-16):

- The API listens on localhost. It has no authentication while the daemon is local-only, and it assumes a trusted local caller.
- **One API, two clients.** The CLI's remote mode and the browser frontend call the same endpoints. There is no separate daemon protocol.
- The CLI keeps a **local mode** (direct reads and writes, as today) next to a **remote mode** (answered by the daemon, writes included).
- The daemon **starts implicitly on first use** and **exits after 30 minutes without a request**. The idle duration and an off switch are settings in the configuration file.
- When the implicit start fails, the CLI **falls back to local mode only where local mode exists**. A squad hosted elsewhere and not present locally is a later case; there the command fails.
- The daemon does **everything local mode does**, including `migrate up`, `repair`, `repad` and `renumber`.
- **Native Windows is supported in 0.18, remote mode included.**
- The browser port **accepts writes**. It ships in 0.18 **disabled by default**, and an authentication mode is designed when the web app is built (MILE-868). There is no per-launch token before then.

The operator ruled on three further points in this ADR's discussion (2026-10-25):

- **One command endpoint for both clients.** The CLI and the web client both call `POST /v1/commands`; FEAT-33's Protocol-typed `RemoteService` is dropped.
- **An environment override,** `SQUADS_DAEMON=on|off`, beside the configuration file's switch.
- **Ctrl-C in remote mode stops only the client's wait,** and the documentation says so.

ADR-1128 decides how the service is built: one composition function, the workflow spec, role catalog and playbook loaded once per invocation, and in the daemon the service built once at startup with a per-request scope. It leaves two points to this decision: how an edited override, or a file changed outside the daemon, reaches a running daemon, and what the request scope is.

This decision sets the API's shape, the transport, discovery, the lifecycle and the request model. The facts that bear on them, read from release/0.17 (the 0.17.0 code the 0.18 release builds on) on 2026-10-25 unless stated otherwise:

1. **The integrity core already supports more than one writer.** `IndexStore.transaction()` (`src/squads/_index/_store.py`) takes a per-loop `anyio.Lock`, a per-process mutex, then a cross-process `filelock.FileLock` on `<squad-dir>/.squads.json.lock` (10-second timeout, a waiting notice after 1 second). Inside the lock it re-reads the index from disk, writes the markdown first and commits the index last with `os.replace`. The per-invocation read scope (`_ReadScope`, a `ContextVar`) is opened by the CLI's `command` bridge and never wired to that commit path. A daemon that writes through `transaction()` is one more process under the same lock.
2. **Nothing about the squad survives an invocation today.** The index is read from disk at most once per invocation (the read scope), item files are read from disk, and the spec documents are loaded per invocation. Module-level state is limited to CODE caches by `tests/meta/test_no_unallowlisted_module_level_mutable_state.py`; per-request values live on `RequestContext` (`src/squads/_context.py`). Two caches sit outside that guard and depend on squad files: the custom-type command caches (`SpecKeyedCache`, keyed on the spec object) and the Jinja environment cache (`_rendering/_engine.py`, keyed on the squad directory, which decides at build time whether `.overrides/templates` exists).
3. **The CLI reads its terminal and process from module-level and process-level state.** The two consoles are `Console()` objects built at import (`_cli/_common.py`); `--json` goes through `print()`; `effective_dir` reads `Path.cwd()` and is "the one place the CLI reads the process directory"; `-C` resolves against it into `RequestContext.client_cwd`; `--file` and the import file are read through `client_path` against that directory, and `-` reads stdin; `actor.session_from_env()` reads `SQUADS_SESSION_ID` and `SQUADS_PARENT_SESSION_ID`; four `typer.confirm`/`typer.prompt` sites ask the terminal (item, sub-entity and comment removal, `init`). The root callback builds a fresh `RequestContext` per invocation and inherits only the clock override from the previous one.
4. **The CLI's cost is fixed startup work, not the transport.** TASK-1123 recorded (2026-10-25, shared machine, about 0.1s noise): a bare `sq --version` at about 0.1s, now answered by `squads.__main__:main` before `squads._cli` is imported; `sq task <n> show` and a write command at about 0.7s. On 2026-10-16: one connect, HTTP request and 4.4KB response took 81-111 µs over a Unix socket and 132-150 µs over TCP loopback (Python 3.14 stdlib, WSL2); `python3 -I -c pass` took 0.029s, and adding `import http.client, socket` 0.115s. Measured 2026-10-25 on this repository's squad (1.7MB index, about 1140 items, dev tree): parsing and validating `.squads.json` takes 0.032s; reading and hashing `.squads.toml` plus every file under `squads/.overrides/` takes 25 µs.
5. **A Unix socket cannot live everywhere a squad can.** On WSL2, `bind()` of an `AF_UNIX` socket on the Windows-mounted drive (`/mnt/c`, drvfs) fails with `EOPNOTSUPP` (measured 2026-10-16). `sun_path` is limited to 108 bytes on Linux and 104 on macOS.
6. **Native Windows CPython has no Unix sockets.** On native Windows Python 3.14.7 (measured 2026-10-16), `socket.AF_UNIX` and `asyncio.start_unix_server` are absent. Named-pipe servers exist only through undocumented asyncio APIs, and a pipe with the default security descriptor grants read access to Everyone (Microsoft's documentation, not measured); restricting it needs an explicit DACL.
7. **Browsers reach only `http(s)://host:port`**, so the browser client needs a TCP listener.
8. **`.squads.toml` is the adopter's file, written from `SquadsConfig` only at `sq init`, an adopt that creates it, and `sq migrate up`** (ADR-1119). `sq migrate up` edits only the `schema_version` line in place, except on a squad carrying legacy keys, where it regenerates the whole file from `SquadsConfig`; the model ignores unknown keys, so a key outside it is lost there, named in the migration report. No other command, `sq sync` included, writes the file. Its `[display]` table is the precedent for a tolerant table: an unusable value falls back to its default and is reported by `sq check`.

## Options

### API shape

- **I. One command endpoint.** The client sends a command line with the context it runs in; the daemon runs the same CLI code in-process and returns the exit code, stdout and stderr. `--json` output is the CLI's own JSON, so the API's data contract is the CLI's. Output parity holds by construction, the CLI client stays a stdlib-only forwarder, and a squad hosted elsewhere is reached the same way.
- **II. Resource routes behind a service interface** (FEAT-33's Protocol-typed `RemoteService`). The CLI keeps parsing and rendering locally and calls the service over HTTP. Every service method and result type needs a wire form, every renderer must produce the same bytes from wire data as from live objects, and the client still pays the 0.7s of CLI and spec construction, so remote mode would be slower than local mode.

### Transport

- **A. A loopback port only.** Works everywhere, but any local process or user can connect, and a browser page can attempt CSRF, DNS rebinding and port scanning.
- **B. A Unix socket for the CLI, a loopback port for the browser.** Per-user isolation on POSIX through file permissions; native Windows is left without a CLI transport (fact 6).
- **C. Option B plus a Windows CLI transport:** C1 a loopback port; C2 a named pipe with a current-user DACL (a third listener on an undocumented API plus hand-written ACL code); C3 `AF_UNIX`, unavailable (fact 6).

## Decision

Adopt **option I** for the API and **option C with C1** for the transport.

Option II is rejected, and with it FEAT-33's `RemoteService`: no Protocol-typed service interface and no second service implementation are built. The browser reads the CLI's `--json` output through the same endpoint, so there are no resource routes to keep in step with the renderers.

### The API

1. **One HTTP/1.1 application, served on every listener, with three routes.**
   - `POST /v1/commands` runs one `sq` command line. The request body carries:
     - `argv`: the arguments after `sq`, unchanged;
     - `cwd`: the client's process directory, which `-C` values resolve against;
     - `env`: a fixed list of variables, the ones the CLI and its console read (`SQUADS_SESSION_ID`, `SQUADS_PARENT_SESSION_ID`, `NO_COLOR`, `FORCE_COLOR`, `TERM`, `COLORTERM`, `COLUMNS`, `LINES`);
     - `terminal`: whether the client's stdin, stdout and stderr are terminals, the encoding of each of the three streams, and the terminal size;
     - `attachments`: an object keyed by each file argument exactly as the command line writes it (`-` for stdin), whose value is the content of that file, or of stdin, in base64 (RFC 4648, standard alphabet, padded) (point 9).

     The response is `{"exit_code", "stdout", "stderr"}` with HTTP 200 whenever the command ran, whatever its exit code. With `--json` in `argv`, `stdout` is the CLI's JSON document character for character.
   - **Wire encoding.** Request and response bodies are UTF-8 JSON.
     - **Text travels as JSON strings:** `argv`, `cwd`, the `env` values, `stdout` and `stderr`. The output is the text the command wrote, before any encoding to bytes. The client writes it through its own stdout and stderr, so their encoding and error handler apply as in local mode, and the daemon's stream buffers report the client's encodings, so the CLI's rendering choices that depend on the stream encoding (Rich's box-drawing and ASCII fallbacks) are the ones local mode makes. A browser client gets the `--json` document as a plain string.
     - **A string that is not valid Unicode** (a lone surrogate, which is what an undecodable file name or argument becomes on POSIX) is sent as its `\u` escape, as Python's default `json.dumps` and the browser's `JSON.stringify` both do, so it round-trips exactly.
     - **Attachments are bytes,** because local mode decodes them itself: the daemon decodes a `--file` attachment as UTF-8 as `client_path` reading does, and reads an attached stdin through a text stream with the client's stdin encoding. A file that is not valid UTF-8 therefore fails the same way in both modes.
   - `GET /v1/daemon` returns the daemon's identity and state: pid, squads version, the squad directory's real path, listeners, start time and idle deadline.
   - `POST /v1/daemon/stop` asks the daemon to exit once the command in progress has finished.
2. **A refusal never runs anything.** HTTP status codes describe the transport, the exit code describes the command:
   - `421`/`403` for a request the admission rules refuse (point 5), before routing;
   - `503` with `{"not_executed": "<reason>"}` for a command the daemon declined before running any of it. The reasons are `retiring` (point 13), `other_squad` (the command line resolves to a squad this daemon does not serve) and `needs_terminal` (point 12). This is the only answer after which the client may run the command itself (point 10).
3. **The server and client are the standard library.** The daemon uses `http.server` on a `socketserver` Unix stream server (POSIX) and TCP servers, one connection per request; the client uses `http.client`. No dependency is added.

### Transport and admission

4. **CLI transport per platform.**
   - **POSIX (Linux, macOS, WSL2):** a Unix socket only, in a per-user `0700` directory with a `0600` socket, and no fallback to a port.
   - **Native Windows:** a loopback CLI port, separate from the browser port and always on while the daemon runs.
   - **Browser port:** present in 0.18 and off unless `daemon.browser` is set (point 7). It binds `127.0.0.1` (and `::1` if dual-stacked) on an ephemeral port, never `0.0.0.0`, and serves the same routes.

   C2 is rejected for 0.18. The operator has accepted, for the browser port, that any local process can drive the API, so a named pipe would buy isolation for one listener on one platform while the browser port gives it up on every platform. The authentication mode designed with the web app (MILE-868) covers the Windows CLI port too.
5. **Admission rules, without authentication, on every TCP listener:**
   - A request whose `Host` is not exactly `127.0.0.1:<port>`, `localhost:<port>` or `[::1]:<port>` is refused before routing. A DNS-rebinding page carries its own hostname and is refused.
   - No CORS headers are sent and no preflight is answered. `GET` never mutates.
   - Every other method requires `Content-Type: application/json` and the custom request header `Squads-Client: 1` (the name case-insensitive, as in HTTP; the value exactly `1`), which a cross-origin page cannot send without a preflight that fails. A form post or a `text/plain` body fails this check. Clients send the header on every listener, the Unix socket included, so one request works on any of them. The name carries no `X-` prefix, which RFC 6648 retires for new headers.
   - `Origin`: the browser port requires it to equal its own origin on every non-`GET` request; the Windows CLI port refuses any request that carries one, since browsers send it and the CLI never does.
6. **Security, stated per platform.** The baseline everywhere is loopback-only binding plus point 5, which stops browser-originated attacks. Above it:
   - **POSIX, browser port off (the default):** only the owning user reaches the API.
   - **Native Windows, any configuration:** any local process or user can read and write the squad through the CLI port. Browsers cannot.
   - **Any platform, browser port on:** the same as Windows, through the browser port.

   The daemon never reads a file named by a client path from its own filesystem (point 9), so a caller who can reach a TCP listener reaches the squad and nothing else the owning user can read. The operator accepts this until the MILE-868 authentication mode exists.

### Discovery and settings

7. **Settings: a `[daemon]` table in `.squads.toml`, and one environment variable.**

   ```toml
   [daemon]
   enabled = true              # false: local mode only; the CLI never starts or contacts a daemon
   idle_timeout_minutes = 30   # exit after this long without a request; 0 = never
   browser = false             # true: also open the browser port
   ```

   - The keys are `SquadsConfig` fields. The adopter writes the table; `to_toml()` writes it only when a value differs from its default, as it does for `[display]`, so `sq init` and adopt add no lines and the legacy-key regeneration of `sq migrate up` keeps it (fact 8).
   - `SQUADS_DAEMON=off` forces local mode for every command in that environment; `SQUADS_DAEMON=on` uses the daemon even where `enabled = false`. Unset, the table decides. The variable is an adopter-visible surface and is documented with the `[daemon]` table. It lets a test suite or CI job that runs `sq` in temporary squads keep every squad in local mode, and lets this repository try the daemon without committing `enabled = true`. The test suite sets `off` for every test that does not exercise the daemon.
   - A setting takes effect at the next command, because changing `.squads.toml` retires the running daemon (point 13).
   - **Validation.** An unknown key in `[daemon]` is reported by `sq check` and otherwise ignored, so a table written by a newer squads version does not break an older one. A known key with an unusable value (not a boolean, a negative or non-integer timeout), or an unusable `SQUADS_DAEMON` value, puts every command in local mode with one line on stderr naming the problem; `sq check` reports it too. Local mode is always correct, so a broken setting can only cost speed.
   - This repository sets `enabled = false` and documents the switch-on step.
8. **One daemon per squad and per installation, found in a per-user runtime directory, never in the squad.**
   - **Key.** A short hash of the squad directory's real path (`SquadPaths.squad_dir` resolved), the squads version and the installed package's directory. A symlink, a `-C` path and a walk-up reach the same daemon; two installations, even of one version, never share one.
   - **Location.** `$XDG_RUNTIME_DIR/squads/` on Linux and WSL2; under the per-user `$TMPDIR` on macOS; under `%LOCALAPPDATA%` on Windows; otherwise a per-user `0700` directory under the user's cache directory. Never inside the squad: drvfs refuses sockets there, the path may exceed `sun_path`, a network filesystem would put two machines' daemons on one name, and runtime files would show in adopters' git status. A directory that cannot hold the socket (missing, wrong owner or mode, path too long) is unusable, which is a failed start (point 11).
   - **Files per key.** `<key>.sock` (POSIX); `<key>.json` with the pid, version, squad real path and every TCP port; `<key>.lock`, held for the daemon's lifetime and released by the OS on process death, `SIGKILL` and Windows termination included; `<key>.log`, the daemon's own stderr for its current lifetime. A clean exit removes all four. After a crash the log stays until the next start for that key, which replaces it.
   - **Singleton and staleness.** A daemon that cannot take `<key>.lock` exits: one is already running. A client that finds the socket refusing connections while the lock is free treats the daemon as dead and removes its files. Over TCP, because a port can be reused by an unrelated process, the client first calls `GET /v1/daemon` and checks the pid and squad path against `<key>.json`.

### The client

9. **Remote mode is a stdlib-only forwarder inside `squads.__main__:main`,** which runs before `squads._cli` is imported, as the bare `--version` path does now.
   - It reads only the leading root options (`-C <path>` in its accepted forms, `--at`, `--help`) and the first command name. One function resolves "which squad, reached how": from the client directory and the `-C` values to the squad directory (the `.squads.toml` walk-up, reading `squad_dir` and `[daemon]` with `tomllib`) and from there to an endpoint. That module is shared with the daemon and with `SquadsConfig`'s reading of `[daemon]`, so the two sides cannot resolve differently; the CLI's `effective_dir` uses the same function.
   - **Local mode, silently,** when there is no squad, when the command line holds anything the forwarder does not understand, and for the commands that cannot or need not run in the daemon: `ui` (it owns the terminal), `daemon` (it talks to the daemon itself), `init` and `adopt` (they create the squad the key is made from), shell completion, and a bare `--version`.
   - **Attachments.** The forwarder attaches the content of every client-file parameter's value, and stdin when one of them is `-`: today every `--file` option and the file argument of `import`. A file it cannot read runs the command in local mode, which reports the error as it always does. In the daemon, `client_path` reads come only from the attachments; a path that is not attached is refused with a clean error.
   - **The file-argument table** is a checked-in, stdlib-only module the forwarder imports: the client-file option names, and per command path the positions of client-file arguments. Keying options by name covers the item commands of custom types, whose names the forwarder never knows. The CLI declares each client-file parameter through one shared helper in `_cli/_common.py`; a `tests/meta` guard walks the command tree, an item app built for a custom type included, collects the declared parameters, compares them with the module and prints the expected module on drift. There is no generator script and no build step: the forwarder cannot import the command tree, and the table changes only when a file parameter is added, which the guard catches.
10. **What reaches the user.** The forwarder writes `stdout` and `stderr` as received and exits with `exit_code`. On native Windows it first sets its stdout and stderr to UTF-8 with replacement, as the CLI does at import, so the encodings it reports and writes with are local mode's.
    - A `not_executed` answer runs the command in local mode, with no line on stderr.
    - **No replay after sending.** A connection lost after the request left the client is an error, never retried locally, because a write may already have committed.
    - **Ctrl-C** stops the client waiting, not the command: a command the daemon has started runs to completion, as it would once its transaction had begun in local mode. There is no mid-command cancel. In local mode Ctrl-C kills the process, so the two modes differ here; the user documentation for remote mode states the difference.
    - Output is returned when the command ends; a long command's progress lines arrive together at the end.

### Lifecycle

11. **Start, idle exit and stop.**
    - A command that finds no live daemon for its key, with the daemon enabled, spawns `sys.executable -m squads daemon run` for that squad, detached from the terminal (a new session on POSIX; `DETACHED_PROCESS`, `CREATE_NEW_PROCESS_GROUP` and `CREATE_NO_WINDOW` on Windows). The child reports on a pipe, then closes it: `ready` once it serves, or one line saying why it cannot. The client waits for that line for at most 5 seconds.
    - **Two clients at once.** Both may spawn; the lock lets one child win, the other reports "already running", and both clients connect to the winner.
    - **Failed start.** A spawn error, a child that reports failure, no answer within 5 seconds, or an unusable runtime directory: the command runs in local mode with one line on stderr giving the reason and how to turn the daemon off. The next command tries again. Where no local squad exists, the command fails with a `SquadsError`. A child that becomes ready after its client gave up serves later commands.
    - **Idle exit** after `idle_timeout_minutes` without a request; a command in progress counts as activity until it ends. The daemon removes its files and releases its lock.
    - **`sq daemon status`** prints the identity from `GET /v1/daemon`, or that none is running (`--json` supported). **`sq daemon stop`** asks it to stop and waits until its files are gone; with none running it does nothing and exits 0. The next command starts a fresh daemon unless the daemon is disabled.
    - **`sq daemon run`** is hidden from `--help` and from the adopter documentation. Its interface, the start-report pipe it inherits, is a private protocol between the client and the daemon, not a contract. It still runs by hand in the foreground for diagnosis, and the lock keeps it a singleton.

### The request model

12. **One command at a time, each in a fresh scope.**
    - The daemon accepts connections on every listener but runs commands strictly one at a time, in arrival order, on one worker thread. Identity and stop requests are answered without waiting for that worker.
    - **The request scope** is one context manager beside ADR-1128's composition function. For each command it:
      - runs the command in a new, empty `contextvars.Context`, so no `RequestContext` field, read scope, clock override or actor from an earlier command is visible;
      - binds a `RequestContext` seeded from the request: the client directory that `effective_dir` starts from, the attachments, the terminal facts, and the documents the daemon loaded at startup;
      - for the command's duration, points the process's stdin, stdout and stderr at the request's buffers (reporting the client's terminal facts) and sets the listed environment variables to the client's values, restoring both afterwards. This is safe because commands run one at a time;
      - runs the CLI's normal entry with `argv`: the root callback, the schema check, the per-invocation read scope opened by `command`, and the command itself, exactly as one local invocation.
    - The root callback derives its `RequestContext` from the seeded one instead of building a new one from defaults. The consoles are built per invocation from the current stdio and environment, not at import.
    - **A prompt** (`typer.confirm` or `typer.prompt`) reached in the daemon ends the command with `needs_terminal`, and the client runs it in local mode. Every prompting command asks before it writes; if a transaction has already committed in the request, the prompt fails the command with an error instead, and a test pins each prompting site to the first case.
    - **Warm across commands:** imported modules, the CLI's command tree, the documents loaded at startup, and the CODE caches. **Read per command, as local mode does:** the index (through the read scope), item files, and the override's cross-check against the index. No squad data is kept between commands, so a write by any process is visible to the next command in either mode.
    - The scope holds no service collaborator, so ADR-1128's reopen trigger (three or more request-scoped collaborators with teardown) is not met.
13. **Edited configuration retires the daemon.**
    - The daemon fingerprints its configuration at startup: the bytes of `.squads.toml` and the names and bytes of every file under `<squad-dir>/.overrides/`. This covers the workflow, roles and playbook overrides, per-role override files and template overrides.
    - Before running each command it compares the fingerprint. On any difference it answers `retiring`, finishes nothing further, and exits; the client runs that command locally and the next command starts a daemon that loads the new configuration. `sq override` and `sq migrate up`, which write these files, retire the daemon the same way.
    - The comparison reads bytes rather than modification times, so a same-size edit inside one timestamp tick is not missed.
    - Item files and the index need no invalidation, because nothing read from them outlives a command (point 12). A `git checkout` is seen the same way: items through the per-command reads, overrides through the fingerprint.
    - The daemon runs the code it started with, and nothing detects an editable install. This repository keeps the daemon off (point 7). The contributor documentation says that a daemon started from a development checkout serves the code it started with until `sq daemon stop`, and that `SQUADS_DAEMON=off` keeps a session in local mode. The key's package directory (point 8) already keeps a checkout's daemon from answering an installed release. Detection through PEP 610's `direct_url.json` would add a package-metadata lookup to every forwarded command to protect contributors, who already have both switches.
14. **The daemon is a peer under the file lock, never its owner.** Every write goes through the same service code as local mode, so through `IndexStore.transaction()` and the rebuild paths unchanged. A local-mode CLI, a daemon, a daemon of another version or installation, an editor extension shelling out to `sq`, and a git hook serialise exactly as concurrent CLIs do today.
15. **Corpus-wide operations and version skew.**
    - `migrate up`, `repair`, `repad` and `renumber` run in the daemon like any command, under their local-mode exclusion. The schema check runs per command, because the root callback does. A daemon older than the squad's schema refuses with the message an old CLI prints.
    - A CLI only ever talks to the daemon of its own installation (point 8). An upgraded CLI starts its own daemon; `migrate up` stamps `.squads.toml`, which retires any daemon serving that squad; an old daemon left without callers exits when idle.

## Consequences

- **The CLI layer changes before the daemon can run it:** one entry function from `argv` to an exit code, shared by `main` and the daemon; consoles built per invocation; `effective_dir` starting from the request's client directory; `client_path` serving attachments in the daemon; the root callback deriving its context from the seeded one. Each is invisible in local mode.
- **Remote mode is faster only because the forwarder skips CLI construction.** Its budget is the interpreter start plus `http.client` (about 0.1s) plus the command's own work in the daemon, which includes the per-command index read (0.032s on this repository's squad).
- **Local mode is always complete wherever the squad is local.** Daemon off, an unusable runtime directory, a failed start or a declined command all leave a working CLI, and correctness never depends on which path answered.
- **Parity is tested, not assumed.** The CLI's command matrix runs in both modes and compares exit code, stdout and stderr byte for byte with stdout not a terminal, and with a terminal of fixed width and colour system. The TCP listeners add a negative test for every admission rule: a rebinding `Host`, a cross-origin form post, a `text/plain` write, a missing or wrong `Squads-Client` header, a foreign `Origin` on the browser port, and any `Origin` on the Windows CLI port.
- **Commands queue.** A long command, a migration above all, delays every other command sent to that daemon until it ends; local-mode commands still wait only for the file lock, as today.
- **Old daemons are reaped by idle exit.** A squad that sets `idle_timeout_minutes = 0` keeps them until logout, a stop, or the next configuration change.
- **The caches outside the mutable-state guard are safe in the daemon:** the custom-type command caches are keyed on the spec object, which lives as long as the daemon, and an override template appearing or changing retires the daemon, so the Jinja environment cache keyed on the squad directory never outlives the overrides it was built from.
- **Room for a squad hosted elsewhere** (FEAT-33). The endpoint-resolution function is the one seam: later its input can be a configured remote address with no local directory. Routes never carry a client filesystem path, and client files travel as attachments, so a remote daemon needs nothing from the client's disk. "Local mode exists" is decided by whether that resolution found a local squad. FEAT-33's `RemoteService` is not built; the command endpoint is the shared seam. The `.claude/` pointer gap noted on FEAT-33 returns with that case.
- **`SQUADS_DAEMON` is part of the adopter surface,** documented beside `[daemon]` and covered by `sq check`'s validation (point 7).
- **Ctrl-C behaves differently in the two modes,** and the documentation states it: remote mode abandons the wait, local mode kills the command.
- **Remote access beyond localhost, and the authentication mode, are a later decision.** No listener binds a non-loopback address. The MILE-868 authentication mode applies to every TCP listener, the Windows CLI port included.

### What would change this decision

- **Per-user isolation on Windows becomes a requirement before the authentication mode exists:** C2 replaces the Windows CLI port.
- **CPython gains `AF_UNIX` on Windows:** the Windows CLI port can become a socket in `%LOCALAPPDATA%`.
- **The authentication mode lands:** a single loopback listener (option A) becomes a candidate simplification.
- **Commands must run concurrently** (the web app's reads queueing behind writes, measured): the request scope stops patching process stdio and environment, and output and environment reach the CLI only through `RequestContext`.
- **The per-command index read is measured as the dominant cost of a remote command:** an index snapshot kept across commands, revalidated against the index file before each one.
- **Progress output must arrive while a command runs:** `POST /v1/commands` streams its response.
<!-- sq:body:end -->

## Discussion

<!-- sq:discussion -->
- [2026-10-16T11:27:49Z] `architect` Robert Architect:
  - Drafted from the 2026-10-16 operator rulings on MILE-868 and MILE-1051 (one API, two clients), EPIC-29/FEAT-916 timings, and the store lock/commit order. Measured on this machine 2026-10-16: request round trip 81-111 us over a Unix socket vs 132-150 us over TCP loopback; Unix socket bind on /mnt/c (drvfs) fails with EOPNOTSUPP; released sq --version takes 0.717s.
  - @op-pierre seven questions are at the end of the body. Question 2 (whether no authentication on the browser port is acceptable, given that it leaves other local processes able to write) is the one that could change the option. @product-owner the API, CLI-mode and lifecycle features depend on this ADR.
- [2026-10-16T11:31:40Z] `op-pierre` Pierre Chat:
  - - 2026-10-16, answers to the ADR's operator questions:
    - Q1: native Windows must be supported in 0.17, remote mode included.
    - Q2: no protection beyond the browser defences while the daemon is local-only; no per-launch token.
    - Q3: the browser port accepts writes. The web app will get an edit mode one day, and so will the TUI and the VS Code extension.
    - Q4: the browser port ships in 0.17, disabled by default. An authentication mode is designed when the JS web app is built (MILE-868).
    - Q5/Q6: the daemon starts implicitly on first use. Daemon mode can be switched off in the TOML configuration; this repo uses that while working on the code.
    - Q7: no refusal. The daemon can do everything the CLI does in local mode, including migrate up, repair, repad and renumber.
- [2026-10-16T11:34:08Z] `architect` Robert Architect:
  - Body revised to carry the operator answers of 2026-10-16. Windows: measured native CPython 3.14.7 here has no AF_UNIX; the CLI on Windows uses a loopback port (named pipe rejected for 0.17, kept as the change condition). That port refuses any request with an Origin header. Per-user isolation is stated as a POSIX-with-browser-port-off property, not a daemon guarantee. Daemons are keyed per squad and per squads version, so version skew needs no restart and migrate up runs in the new daemon. Three questions remain open: idle exit, where the off switch lives, and what happens when implicit start fails.
  - @op-pierre the three remaining questions are at the end of the body.
- [2026-10-16T11:54:34Z] `op-pierre` Pierre Chat:
  - - 2026-10-16, answers to the three remaining questions:
    - Idle exit: the daemon exits after 30 minutes without a request. The duration is a setting in the configuration file.
    - Off switch: in that same configuration file.
    - Failed implicit start: the CLI falls back to local mode only when local mode exists. A later case will have the CLI talk to a squad hosted elsewhere and not committed locally; there, there is no local mode to fall back to, and the command fails.
- [2026-10-16T11:55:49Z] `architect` Robert Architect:
  - Body revised for the operator answers of 2026-10-16 11:54Z: a [daemon] table in .squads.toml (enabled, idle_timeout_minutes = 30, browser), modelled on SquadsConfig so that to_toml() rewrites keep it; implicit start falls back to local mode only when the squad is local, and never after a request has been sent; a squad hosted elsewhere is recorded as a consequence the endpoint resolution must leave room for. No open questions remain.
- [2026-10-16T12:01:28Z] `op-pierre` Pierre Chat:
  - 2026-10-16: stays Proposed. Accepted when the 0.17 release opens, after another review pass.
- [2026-10-25T11:05:26Z] `architect` Robert Architect:
  - 2026-10-25, review against FEAT-1140 and ADR-1128; body amended. What changed:
    
    - **API shape decided (new):** one command endpoint, `POST /v1/commands` (argv, client directory, a fixed env list, terminal facts, file attachments in; exit code, stdout, stderr out), plus `GET /v1/daemon` and `POST /v1/daemon/stop`. A `503 not_executed` answer is the only one after which the client may run the command itself. The old body left the API's shape open, which every story depends on.
    - **Request scope decided (ADR-1128's open point):** commands run one at a time, each in a new empty `contextvars.Context` with a `RequestContext` seeded from the request; process stdio and the listed env vars are pointed at the request for its duration; the CLI's normal entry then runs unchanged. A prompt answers `needs_terminal` and the command runs locally.
    - **Staleness decided (ADR-1128's open point):** the daemon fingerprints the bytes of `.squads.toml` and every file under `.overrides/`; any difference retires it before the next command runs. No squad data is kept between commands, so item and index edits need no invalidation. This replaces the stat-revalidated index and spec snapshot (old point 10) and the "drop warm state after corpus-wide operations" rule (old point 11): both were stored state without a measured failure (index parse is 0.032s on this squad, measured today).
    - **Stale against release/0.17, corrected:** startup figures now cite TASK-1123 (bare `--version` about 0.1s via `squads.__main__:main`); remote dispatch sits in that entry point; `[daemon]` follows the `[display]` precedent (written only when non-default, unknown keys reported by `sq check`); the `-C` path goes through `effective_dir`/`client_path`, which today read `Path.cwd()` and the local disk.
    - **Added:** the key includes the install directory (a dev checkout and a release of one version no longer share a daemon); a start handshake on a pipe with a 5 s bound, so a failed start is reported on the command that tried; `<key>.log`; `sq daemon status|stop`; file attachments instead of the daemon reading client paths (keeps TCP callers away from the owner's other files, and keeps the remote-host case open).
    - Transport, admission rules, per-platform security and the version-keyed skew policy are unchanged in substance. Title and summary updated to the wider scope.
    
    @op-pierre three questions are yours; the rest is decided in the body:
    
    1. **API shape.** Option I reads "one API, same endpoints" as both clients calling the one command endpoint: the browser gets the CLI's `--json`, not resource routes, and FEAT-33's Protocol-typed `RemoteService` is not built. Option II (resource routes behind a service interface) makes remote mode slower than local mode and needs a wire form for every service type. I recommend I.
    2. **`SQUADS_DAEMON=on|off`**, an environment override of `[daemon] enabled`: a new adopter-visible surface. Without it, any test suite or CI job that runs `sq` in temporary squads spawns a daemon per squad, and this repository cannot trial the daemon without committing `enabled = true`. I recommend keeping it.
    3. **Ctrl-C in remote mode** stops the client waiting; a command the daemon has started runs to completion (no replay, no mid-command cancel). In local mode Ctrl-C kills the process. I recommend accepting the difference, documented.
- [2026-10-25T17:37:20Z] `op-pierre` Pierre Chat:
  - Yes to all three: one command endpoint shared by the CLI and the web client (FEAT-33 RemoteService dropped); a SQUADS_DAEMON=on|off environment override; Ctrl-C in remote mode stops only the client wait, documented as such.
- [2026-10-25T17:39:29Z] `manager` Catherine Manager:
  - Accepted: the three operator rulings are folded into the body as decisions.
- [2026-10-25T21:41:29Z] `architect` Robert Architect:
  - Audited 2026-10-25: holds as a decision; the daemon is not built yet. One fact in its Context is dated: since ADR-1119, .squads.toml is rewritten only at init/adopt and by migrate up, so point 7 reads as "to_toml writes the table only when non-default" at those writes.
- [2026-10-28T13:53:58Z] `product-owner` Nina Product:
  - @architect the body still says 0.17 throughout (Context, "Native Windows is supported in 0.17", "ships in 0.17 disabled", "read from release/0.17", "0.17 line (MILE-1051, FEAT-1140)"). The daemon release is 0.18 (MILE-1152); MILE-1051 is the closed roles-and-checks release. Please correct the release references.
- [2026-10-28T14:01:46Z] `architect` Robert Architect:
  - @product-owner corrected, thanks. Body amended 2026-10-28, release references only, no change in substance:
    - Context: "The 0.17 line (MILE-1051, FEAT-1140)" now "The 0.18 line (MILE-1152, FEAT-1140)". The settled-frame citation of MILE-1051 stays: the 2026-10-16 one-API ruling is recorded on that milestone's discussion.
    - "Native Windows is supported in 0.17", "ships in 0.17 disabled by default", "present in 0.17" (browser port) and "C2 is rejected for 0.17" now say 0.18.
    - "read from release/0.17 on 2026-10-25" keeps the branch, which is where the facts were read, and now names it as the 0.17.0 code the 0.18 release builds on. Changing it to release/0.18 would misstate the source: that branch was cut on 2026-10-28.
    - No 0.19 or 0.20 reference was in the body. The older 0.17 mentions in this discussion are dated history and stay as written.
- [2026-10-28T14:03:03Z] `architect` Robert Architect:
  - Body amended 2026-10-28 to match ADR-1119, closing the dated fact my 2026-10-25 audit named. The decision is unchanged:
    - Context fact 8 now says `.squads.toml` is the adopter's file. `sq` writes it from `SquadsConfig` only at `sq init`, at an adopt that creates it, and during `sq migrate up`. `migrate up` stamps the `schema_version` line in place and regenerates the whole file only on a squad that carries legacy keys, where a key outside the model is lost and named in the migration report. No other command writes the file, `sq sync` included. The old text said every rewrite dropped unknown keys. Checked against the code: `to_toml()` is called only by init, adopt and `_migrations/_config_text.py::_regenerated`.
    - Decision point 7, the settings bullet (I misnumbered it as point 12 in my handback): "so every rewrite keeps it" now names the writes that remain. `sq init` and adopt add no lines, and the legacy-key regeneration keeps the table. Its commitments are unchanged: the keys are `SquadsConfig` fields, the table is written only when a value is non-default, it survives every `sq` write, and the `sq check` reporting is untouched. So this needed no ruling.
- [2026-10-28T18:28:02Z] `architect` Robert Architect:
  - Body amended 2026-10-28: the five points left open by the TASK-1218 breakdown are decided in the points they belong to (op-pierre approved settling them). @tech-lead
    
    - **Point 5, custom header:** `Squads-Client: 1`, value exactly `1`, sent by clients on every listener. Not `X-Squads-Client`: RFC 6648 retires the `X-` prefix for new headers, and this name becomes documented API.
    - **Point 1, wire encoding (new sub-bullet):** UTF-8 JSON bodies. `stdout`, `stderr`, `argv`, `cwd` and `env` values are JSON strings carrying the text the command wrote, not bytes; the client writes them through its own streams, so its encoding and error handler apply as in local mode. Lone surrogates (undecodable POSIX names) travel as `\u` escapes and round-trip exactly. Attachments are base64 bytes keyed by the argument as written, because local mode decodes them itself (UTF-8 for `--file`, the client's stdin encoding for `-`), so invalid UTF-8 fails identically. Two additions this needed: `terminal` now carries each stream's encoding, since Rich picks box-drawing or ASCII from it; and point 10 has the forwarder apply the CLI's Windows UTF-8-with-replacement stream setup before it reports or writes.
    - **Point 11, `sq daemon run`:** hidden from `--help` and the adopter docs. Its start-report pipe is a private client-daemon protocol, not a contract; it still runs by hand for diagnosis.
    - **Point 13, development installs:** no editable-install detection. This repo keeps `enabled = false`; the contributor docs name `sq daemon stop` and `SQUADS_DAEMON=off`. The key's package directory already keeps a checkout's daemon away from a released CLI; detection would add a metadata lookup to every forwarded command to protect only contributors.
    - **Point 9, file-argument table:** a checked-in stdlib-only module plus a `tests/meta` guard, with no generator script. Options are keyed by name, not command path, so custom-type item commands are covered without the forwarder knowing type names. Parameters are declared through one shared `_cli/_common.py` helper, so the guard reads a declaration. Also decided: a file the forwarder cannot read runs the command in local mode, which keeps the error message identical.
    - Consequences: the admission negative test now reads "a missing or wrong `Squads-Client` header". Nothing escalated: all five are technical.
<!-- sq:discussion:end -->
