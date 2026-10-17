---
id: ADR-1052
sequence_id: 1052
type: decision
title: 'Daemon transport: one HTTP API on a Unix socket and a loopback port'
status: Proposed
author: architect
refs:
- MILE-868
- MILE-1051
- EPIC-29
- FEAT-33
- FEAT-916
description: 'One HTTP API: a per-user Unix socket for the CLI on POSIX, a loopback
  port for the CLI on native Windows, and a disabled-by-default browser port; Host/Origin/JSON
  admission rules instead of authentication; writes stay under the existing file lock'
created_at: '2026-10-16T11:27:26Z'
updated_at: '2026-10-16T12:01:28Z'
---
<!-- sq:body -->
## Context

The 0.17 line (MILE-1051) adds a squads daemon: a long-lived local process that serves squad state over an API. The browser frontend (MILE-868) builds on it. The operator has settled the frame (MILE-868, MILE-1051 and this ADR's discussion, 2026-10-16):

- The API listens on localhost. It has no authentication while the daemon is local-only, and it assumes a trusted local caller.
- **One API, two clients.** The CLI's remote mode and the browser frontend call the same endpoints. There is no separate daemon protocol.
- The CLI keeps a **local mode** (direct reads and writes, as today) next to a **remote mode** (answered by the daemon, writes included).
- The daemon **starts implicitly on first use** and **exits after 30 minutes without a request**. The idle duration and an off switch for daemon mode are settings in the configuration file.
- When the implicit start fails, the CLI **falls back to local mode only where local mode exists**. A squad hosted elsewhere and not present locally is a later case; there the command fails.
- The daemon does **everything local mode does**, including `migrate up`, `repair`, `repad` and `renumber`.
- **Native Windows is supported in 0.17, remote mode included.**
- The browser port **accepts writes**. It ships in 0.17 **disabled by default**, and an authentication mode is designed when the web app is built (MILE-868). There is no per-launch token before then.

What is open is the transport: an HTTP port on loopback, a Unix domain socket, a Windows named pipe, or a combination. The one-API rule requires one HTTP API, with the same routes, bodies and status codes for every client. It does not require a single listener, because the same HTTP application can be served on several listeners at once.

Five facts bear on the choice.

1. **The integrity core already supports more than one writer.** `IndexStore.transaction()` (`src/squads/_index/_store.py`) takes three locks in order: a per-loop `anyio.Lock`, a per-process mutex, then a cross-process `filelock.FileLock` on `<squad-dir>/.squads.json.lock`, with a 10-second timeout. Inside the lock, every transaction re-reads the index from disk, never from a cached snapshot. It writes the markdown first and commits the index last with `os.replace`. The per-invocation read scope (`_ReadScope`, a `ContextVar`) is never wired to that commit path. A daemon that writes through `transaction()` is one more process under the same lock, like a second `sq` invocation.
2. **The CLI's cost is fixed startup work, not the transport.** EPIC-29 and FEAT-916 record about 0.7s of pre-dispatch work (Typer app construction and spec loading) on every invocation. A re-run on 2026-10-16 gave 0.717s (released `sq --version`, median of 5).
   - One connect + HTTP request + 4.4KB response (2000 iterations, two runs, Python 3.14 stdlib on WSL2) took 81-111 µs over a Unix socket and 132-150 µs over TCP loopback. Both are four orders of magnitude below the startup floor.
   - A bare `python3 -I -c pass` takes 0.029s. Adding `import http.client, socket` brings it to 0.115s (medians of 10).
3. **A Unix socket cannot live everywhere a squad can.**
   - On WSL2, `bind()` of an `AF_UNIX` socket on the Windows-mounted drive (`/mnt/c`, 9p/drvfs) fails with `EOPNOTSUPP` (measured 2026-10-16).
   - `sun_path` is limited to 108 bytes on Linux and 104 on macOS, and squad paths can be longer.
4. **Native Windows CPython has no Unix sockets, but has a named-pipe server outside its public API.** On this machine's native Windows Python 3.14.7 (measured 2026-10-16), `socket.AF_UNIX` and `asyncio.start_unix_server` are both absent, even though the Windows kernel supports `AF_UNIX`. `asyncio.ProactorEventLoop.start_serving_pipe` and `asyncio.windows_events.PipeServer` exist but are undocumented. Per Microsoft's documentation (not measured here), a named pipe created with the default security descriptor grants read access to Everyone. Restricting it to the current user needs an explicit DACL, set through `ctypes` or a Windows-only dependency.
5. **Browsers cannot connect to a Unix socket or a named pipe.** A page reaches only `http(s)://host:port`, so the browser client needs a TCP listener.

## Options

### A. HTTP on a loopback port only, everywhere

One listener on `127.0.0.1:<ephemeral port>` serves both clients on every platform.

- **Security without authentication.** Any process on the machine, and any user on a shared host, can connect and write. File permissions do not apply to a port. A browser page can also reach it:
  - **CSRF.** A page on any origin can send "simple" cross-origin requests (form posts, `text/plain` bodies) without a CORS preflight. It cannot read the response, but it can trigger a write.
  - **DNS rebinding.** An attacker's domain re-resolves to `127.0.0.1`. The page then counts as same-origin and can read responses and send any request.
  - **Port scanning.** An ephemeral port is not a secret.
- **Platform reach.** Everywhere. Under WSL2's localhost forwarding, a WSL listener on 127.0.0.1 is also reachable from the Windows side (WSL2's documented behaviour, not measured here).
- **Browser.** Direct.

### B. Unix socket for the CLI, loopback port for the browser, same HTTP application

- **Security.** On POSIX, the CLI path sits in a per-user `0700` directory with a `0600` socket, so only the owning user reaches it. No browser can reach it either. The browser port carries option A's exposure and needs the browser defences.
- **Platform reach.** Linux, macOS and WSL2. **Native Windows is left without a CLI transport**, because of fact 4. On its own, this option fails the Windows ruling.

### C. Option B, plus a Windows CLI transport

The Windows CLI path has three candidates:

- **C1, a loopback port.** It uses the same server stack as the browser port and works on stock CPython. It gives no per-user isolation: any local process or user can reach it, exactly as with the browser port.
- **C2, a named pipe with a current-user DACL.** It restores per-user isolation on Windows. The cost is a third listener implementation, built on an undocumented asyncio API or a new Windows-only dependency, plus hand-written ACL code. It also needs an HTTP server running over a pipe stream, which off-the-shelf ASGI servers do not provide.
- **C3, `AF_UNIX` on Windows.** Not available in CPython (fact 4).

## Decision

Adopt **option C with C1**: one HTTP application, served on a per-user Unix socket for the CLI on POSIX, on a loopback port for the CLI on native Windows, and on a separate, disabled-by-default loopback port for the browser.

1. **The API is HTTP, on every listener.** HTTP/1.1 runs over the Unix socket too. Every route, body, status code and error shape is identical on all listeners, because they serve one application. Listeners differ only in which requests they admit (point 4).
2. **CLI transport per platform.**
   - **POSIX (Linux, macOS, WSL2):** the Unix socket only, with no fallback to a port.
   - **Native Windows:** a loopback CLI port, separate from the browser port and always on while the daemon runs.

   C2 is rejected for 0.17. The operator has accepted, for the browser port, that any local process can drive the API, so a named pipe would buy isolation for one listener on one platform while the browser port, once enabled, gives that isolation up on every platform. The authentication mode designed with the web app (MILE-868) covers the Windows CLI port too, and makes the pipe unnecessary rather than merely deferred.
3. **The browser port is present in 0.17 and disabled by default.** It binds to `127.0.0.1` (and `::1` if dual-stacked) on an ephemeral port, never to `0.0.0.0`. It accepts writes and serves the frontend's pages. It is turned on by `daemon.browser` (point 7).
4. **Admission rules, without authentication.** Every TCP listener, the Windows CLI port and the browser port alike:
   - Refuses any request whose `Host` is not exactly `127.0.0.1:<port>`, `localhost:<port>` or `[::1]:<port>`, before routing (`421`/`403`). A DNS-rebinding page carries its own hostname in `Host` and is refused.
   - Sends **no** CORS headers and answers no preflight. `GET` never mutates.
   - Requires, on every state-changing request (any method other than `GET`/`HEAD`), `Content-Type: application/json` plus a fixed custom request header. A cross-origin page cannot send either without a preflight that fails, and a form post or `text/plain` body fails the content-type check. This closes CSRF.
   - Varies only in its `Origin` rule:
     - The **browser port** requires `Origin` to equal its own origin on every state-changing request. Its own pages are same-origin and pass.
     - The **Windows CLI port** refuses any request that carries an `Origin` header at all. Browsers send `Origin` on every non-`GET` request, and the CLI never sends one, so this port is unreachable from a page even through a bug in the other checks.
5. **Security, stated per platform.** The baseline everywhere is loopback-only binding plus point 4, which stops browser-originated attacks. Above that baseline:
   - **POSIX, browser port off (the default):** the API is reachable only by the owning user, through the socket's file permissions.
   - **Native Windows, any configuration:** any local process or user can read and write through the CLI port. Browsers cannot.
   - **Any platform, browser port on:** same as Windows, through the browser port.

   Per-user isolation is therefore a property of POSIX with the browser port off, not a guarantee of the daemon. The operator accepts this until the MILE-868 authentication mode exists.
6. **One daemon per squad and per squads version, discovered in a per-user runtime directory, never in the squad.**
   - **Identity.** A short hash of the squad directory's resolved real path (`SquadPaths.squad_dir`) and the squads version, so a symlink, a `-C` path and a walk-up all reach the same daemon. A hash keeps the socket name inside `sun_path` and keeps the squad path out of the filename.
   - **Location.**
     - Linux and WSL2: `$XDG_RUNTIME_DIR/squads/`, a per-user `0700` tmpfs cleared at logout (present here as `/run/user/1000`).
     - macOS: under the per-user `$TMPDIR`.
     - Windows: under `%LOCALAPPDATA%`.
     - Otherwise: a per-user `0700` directory under the user's cache directory.

     Never inside the squad directory, for four reasons: drvfs refuses sockets there, the path may exceed `sun_path`, a network filesystem shared by two hosts would put two machines' daemons on one name, and a runtime file in the squad would show up in adopters' git status.
   - **Files per key.**
     - `<key>.sock` on POSIX.
     - `<key>.json` holds the pid, the squads version, the squad's real path, and every TCP port in use.
     - `<key>.lock` is held exclusively for the daemon's lifetime. The OS releases it on process death, including `SIGKILL` and Windows termination.
   - **Singleton and staleness.** A daemon that cannot take `<key>.lock` exits, because one is already running. A client that finds the socket refused, or the lock free, treats the daemon as dead and removes the stale files. Because a port number can be reused by an unrelated process, a client connecting over TCP first calls an identity endpoint and checks that the pid and squad path match `<key>.json`.
7. **Configuration lives in `.squads.toml`, under a `[daemon]` table.** `.squads.toml` is today's only configuration file. It is committed, so a setting applies to every clone of the project. Proposed keys and defaults:

   ```toml
   [daemon]
   enabled = true              # false: local mode only; the CLI never spawns or contacts a daemon
   idle_timeout_minutes = 30   # the daemon exits after this long without a request; 0 = never
   browser = false             # true: the daemon also opens the browser port (point 3)
   ```

   - The daemon reads these keys at startup. A change takes effect on the daemon's next start, which an idle exit or a manual stop provides.
   - This repository sets `enabled = false` while the code is being worked on.
   - The keys become `SquadsConfig` fields, emitted by `to_toml()`. `.squads.toml` is rewritten from the model (by init, adopt and the maintenance paths), and that model ignores unknown keys, so a key outside the model would be silently dropped on the next rewrite.
8. **Implicit start, idle exit and fallback.**
   - A CLI with `enabled = true` that finds no live daemon for its key spawns one from its own installation, detached from the terminal (a new session on POSIX, a detached process on Windows). It then waits a bounded time for the socket or port to answer.
   - Two CLIs starting at once are resolved by the singleton lock: the loser exits and both clients connect to the winner. The first call pays the daemon's own startup.
   - The daemon exits after `idle_timeout_minutes` with no request, releasing its lock and removing its runtime files. An in-flight request, a migration included, counts as activity until it completes.
   - **Failed start.** A spawn error, a readiness timeout or an unusable runtime directory falls back to local mode when the squad is present locally, with a one-line warning on stderr so that stdout and `--json` output stay identical. Where no local squad exists, the command fails with a `SquadsError`.
   - **No fallback once a request is sent.** A connection lost after the request left the client is reported as an error, never retried in local mode, because a write may already have committed in the daemon.
9. **The daemon is a peer under the file lock, never its owner.** Every daemon write goes through the same service code as local mode, and so through `IndexStore.transaction()` and the rebuild paths unchanged. A local-mode CLI, the daemon, another daemon of a different version, an editor extension shelling out to `sq`, and a git hook all serialise exactly as concurrent CLIs do today. The markdown-before-index order and the in-lock fresh read hold because the daemon runs the same code.
10. **Warm state never reaches the commit path and never outlives a change it cannot see.**
   - Each request runs in its own read scope (the existing `_ReadScope`, entered per request where the CLI enters it per invocation).
   - An index snapshot kept across requests is revalidated on every request against the index file's `(st_ino, st_mtime_ns, st_size)`. `os.replace` changes the inode, so every commit by any process is detected, as is a `git checkout`. The parsed workflow spec is revalidated the same way against its source files.
   - Item markdown is read from disk per request.
   - What stays warm is what costs the 0.7s: imported modules, the constructed command layer, and the spec while it is still valid.
11. **Corpus-wide operations run in the daemon like any command.**
    - `migrate up`, `repair`, `repad` and `renumber` are API operations with the same exclusion they use in local mode.
    - The daemon applies the schema check **on every request**, not once at startup. A daemon whose code is newer than the squad's schema serves only `migrate up` (and help) until the migration has run, then serves normally. No restart is needed, because the code that just migrated the squad is the code now serving it.
    - After any corpus-wide operation, the daemon drops all warm state outright rather than relying on revalidation.
12. **Version skew between CLI and daemon is resolved by keying, not by restarts.**
    - A CLI only ever talks to the daemon of its own squads version, because the version is part of the key (point 6).
    - An upgraded CLI starts its own daemon. The old daemon keeps running and hits the per-request schema check once the squad is migrated, refusing with the same message an old CLI would print.
    - Two installs of different versions on one machine (a released tool and a development checkout, say) each get their own daemon instead of killing each other's on every call. They then coexist under the file lock exactly as two CLI versions do today.
    - The upgrade path is therefore: install the new version, run `sq migrate up` (which reaches the new daemon), and the old daemon is left idle with nothing to stop.

## Consequences

- **The daemon helps the CLI only if remote dispatch skips the pre-dispatch work.** A remote-mode call must resolve the squad, find the listener and forward the request before Typer or the spec is constructed. Otherwise it pays 0.7s and then the round trip, and is slower than local mode. A stdlib client costs about 0.03s of interpreter start plus up to about 0.09s for `http.client`, and that budget is a design target for the remote-mode feature. FEAT-916's lazy loading benefits both modes and sets the baseline the daemon is measured against.
- **Local mode is always complete wherever the squad is local.** Daemon mode off, a filesystem with no usable runtime directory, or a daemon that cannot start all leave a working CLI. Correctness never depends on which path answered, because both take the same lock.
- **Three listener configurations share one parity suite.** The API suite runs against the Unix socket, the Windows CLI port and the browser port. The TCP runs add negative tests for every admission rule: a rebinding `Host`, a cross-origin form post, a `text/plain` write, a missing custom header, a foreign `Origin` on the browser port, and any `Origin` on the Windows CLI port.
- **Old daemons are reaped by idle exit.** Version keying trades restart churn for idle processes of old versions. Each one exits `idle_timeout_minutes` after its last request. A squad that sets `idle_timeout_minutes = 0` keeps them until logout or a manual stop.
- **Lock-hold time is shared.** A long operation in the daemon, a migration above all, blocks every local-mode CLI and every other daemon for up to the 10-second lock timeout on each acquire, as a long CLI command does today. Handlers keep transactions as short as today's commands.
- **The design must leave room for a squad hosted elsewhere.** A later CLI will address a squad that is not committed locally, served by a daemon on another host. That case has no local mode, no local squad path to hash, and needs the authentication mode. It is not designed here, but nothing in 0.17 may close it off:
  - The CLI resolves "which squad, reached how" in one place, which returns an endpoint. Today the input is a local squad directory and the endpoint is a socket or port found in the runtime directory. Later the input can be a configured remote address with no local directory. Commands and the API client never derive an endpoint from a filesystem path themselves.
  - API routes address items relative to the squad the daemon serves and never carry a client-side filesystem path. A remote daemon's paths mean nothing to its client.
  - "Local mode exists" is decided by whether that resolution found a local squad directory, so the failed-start rule in point 8 already covers the remote case.
  - The `.claude/` pointer gap noted on FEAT-33 returns with this case, since the role and skill files will not be on the client's disk.
- **Remote access beyond localhost, and the authentication mode, are a later decision.** No listener binds a non-loopback address. When the MILE-868 authentication mode lands, it applies to every TCP listener, including the Windows CLI port.

### What would change this decision

- **Per-user isolation on Windows becomes a requirement before the authentication mode exists.** Then C2 (a named pipe with a current-user DACL) replaces the Windows CLI port.
- **CPython gains `AF_UNIX` on Windows.** The Windows CLI port could then become a socket in `%LOCALAPPDATA%`, giving one CLI transport everywhere.
- **The authentication mode lands.** Per-user isolation stops depending on the transport, and a single loopback listener (option A) becomes a candidate simplification.

## Open questions for the operator

None.
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
<!-- sq:discussion:end -->
