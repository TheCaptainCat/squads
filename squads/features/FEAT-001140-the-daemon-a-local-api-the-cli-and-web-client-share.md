---
id: FEAT-1140
sequence_id: 1140
type: feature
title: 'The daemon: a local API the CLI and web client share'
status: InProgress
parent: EPIC-29
author: product-owner
refs:
- FEAT-33
- ADR-1052:depends-on
- TASK-1125:depends-on
- FEAT-1226
- ADR-1225:depends-on
- ADR-1224
- MILE-1241:targets
description: A local process serving the squad as resource routes, called by the CLI
  in remote mode, the terminal UI and later the browser; local mode stays
subentities:
- local_id: US1
  title: Every operation served at its own resource route
  status: InProgress
- local_id: US2
  title: Writes through the routes, safe against concurrent edits
  status: InProgress
- local_id: US3
  title: CLI remote and local modes
  status: InProgress
- local_id: US4
  title: Daemon lifecycle and discovery
  status: InProgress
- local_id: US5
  title: Daemon settings in .squads.toml
  status: Todo
- local_id: US6
  title: Native Windows support
  status: Todo
- local_id: US7
  title: Browser listener, off by default
  status: Todo
- local_id: US8
  title: Dogfood in this repository
  status: Todo
- local_id: US9
  title: Documentation for adopters
  status: Todo
- local_id: US10
  title: Actor, time, session and paths travel with each call
  status: InProgress
- local_id: US11
  title: Client and daemon refuse a schema or vocabulary mismatch
  status: Todo
- local_id: US12
  title: Remote commands within a measured client budget
  status: Todo
- local_id: US13
  title: The terminal UI as a daemon client
  status: Todo
created_at: '2026-10-25T10:47:24Z'
updated_at: '2026-10-30T07:20:40Z'
priority: high
---
<!-- sq:body -->
## Problem

Every `sq` invocation starts cold: it builds the CLI, loads the vocabulary and reads the squad again, then exits. Nothing is kept between two commands, and nothing other than the CLI can ask a running process about the squad. The browser frontend (MILE-868) needs exactly that: typed resources it can call from a Vue or Angular front. The CLI benefits from the same door.

## What the daemon gives an adopter

- A local process that serves the squad as resource routes under `/v1`, one route per operation, with a typed JSON answer and an OpenAPI document a front can generate its types from.
- A CLI that uses it without being asked: the first command starts the daemon, later commands are answered by it, and the daemon exits by itself after a quiet period. The CLI still parses and renders in the user's own process, so output is the same in both modes.
- Local mode kept as it is: with the daemon switched off, or when a local daemon cannot start, the CLI reads and writes the squad directly.
- One API for every client. The CLI's remote mode, the terminal UI and the future browser frontend call the same routes (op-pierre rulings, 2026-10-16 and 2026-10-28); there is no second protocol.
- Writes that refuse to overwrite what changed since a client read it, and a client and daemon that refuse each other before running anything when their schema or vocabulary differ.

## Scope

- The routes: every operation of the command layer (the operation table that FEAT-1226 builds) served at its own route, plus daemon status, stop and the OpenAPI document; reads and local single-user writes, and everything local mode does, including migrate, repair, repad and renumber.
- The errors a client can act on: an HTTP status and a machine-readable type per failure, with the same sentence local mode prints.
- The request headers: actor, clock, session ids, client directory, schema and vocabulary checks, and `If-Match` for writes on an item.
- The CLI's two modes, remote (answered by the daemon) and local (direct), chosen once per invocation, with the fall back from the first to the second for a local daemon, and the timeouts a remote call applies.
- The terminal UI on the same selection: a daemon client in remote mode.
- The client budget: what a remote command costs in the client's own process, measured at release.
- The daemon's lifecycle: implicit start, discovery, staleness, idle exit, stop, and settings in `.squads.toml`.
- Native Windows supported, remote mode included.
- This repository dogfooding the daemon, switched off at first and enabled once it has earned trust.
- The browser-facing listener exists but is off by default.

The command layer the routes serve (one operation per command, its result shape, `--json` on every command) is FEAT-1226. The transport, discovery, lifecycle and request model are decided in ADR-1052; the routes, wire format, errors and mode selection in ADR-1225. This feature states outcomes and leaves those choices to them.

## Non-goals

- The browser frontend (MILE-868). It consumes these routes and is not built here.
- Authentication and authorization. The API assumes a trusted local caller, and the actor a request names is declared, not verified.
- A squad hosted on another machine (FEAT-33), and any listener reachable beyond the adopter's machine.
- Pagination of listings and search results; it comes with the web front.
- Cutting the fixed startup cost of a local invocation (FEAT-916, Done) as a criterion: local mode benefits from the client's lighter start where it can, but only remote mode carries a budget.
- Progress output while an operation runs: a remote answer arrives when the operation ends.

## Boundary with FEAT-33

FEAT-33 is the client side of a squad hosted elsewhere. This feature delivers the server side on one machine and the seam that case plugs into: endpoint resolution returns an endpoint, and the CLI and the terminal UI call it through the same HTTP client the local daemon uses. The endpoint says whether a local mode exists; only a local daemon has one. FEAT-33 adds a source for that endpoint (an address the client's own settings name), authentication, a listener beyond loopback, the hosted-squad fall back rule as a user-facing behaviour, synchronising the workflow configuration between a checkout and a hosted squad, and the `.claude/` pointer gap. No second client or service interface is built for it.

## Acceptance criteria

- On a machine with the daemon enabled, any `sq` command starts a daemon if none is running, and its output and exit code are identical to local mode, `--json` included.
- A second command is answered by the same daemon; stopping it, or leaving it idle for the configured time, ends the process and removes its runtime files.
- With the daemon disabled in `.squads.toml` or by `SQUADS_DAEMON=off`, `sq` never starts or contacts one.
- When a local daemon cannot start, the command still succeeds in local mode and one line on stderr says why.
- A write made through the daemon is visible to a local-mode command right after, and the reverse, with no stale answer.
- Two commands started at once end up on one daemon.
- A client other than the CLI reads and writes the squad through the documented routes, generates its types from `GET /v1/openapi.json`, and tells failures apart by HTTP status and error type.
- A write that names an item version the item no longer has is refused with `409` and writes nothing.
- A client and a daemon at different schema versions, or parsing with different workflow vocabularies, refuse each other before anything runs, and the CLI's message names the remedy.
- The terminal UI browses the squad through the daemon in remote mode and directly in local mode, with the same screens.
- Client budget, a release criterion: the client's overhead for `sq <type> <n> show` (wall time minus the daemon's own handling time), as the median of 31 interleaved runs on the reference host, is at most 275 ms in human mode and 235 ms with `--json`, and the measurement is recorded with the release.
- The same behaviour holds on Linux, macOS and native Windows.
- This repository runs with the daemon disabled and a documented step to enable it.
<!-- sq:body:end -->

## User Stories

_Add with `sq feature 1140 add-story "As a <role>, I want … so that …"`; track with `sq feature 1140 story <n> update --status <Status>`._

<!-- sq:stories -->

<!-- sq:story:US1 -->
### US1 — Every operation served at its own resource route

<!-- sq:story:US1:body -->
As a front author or tool author, I call every operation of the squad at its own route under `/v1` and get a typed JSON answer, described by an OpenAPI document I can generate my client's types from.

Done when:
- Every operation of the command layer (FEAT-1226) is served at its route: items by id at `/v1/items/{id}`, so a custom type needs no new route; roles, skills and operators under `/v1/roles/{addr}`, `/v1/skills/{addr}` and `/v1/operators/{addr}`, addressed by slug, id or number as on the CLI; squad-wide operations under `/v1/squad/`.
- `GET` reads and never changes anything; filters are query parameters, and a repeated filter repeats its key. Creation is a `POST` on a collection, a partial update a `PATCH`, a body replacement a `PUT` on `…/body`, a removal a `DELETE`, and any other action a `POST` on a sub-resource named after it (`…/status`, `…/retype`).
- A successful answer is `200` with `data`, `omitted` and `warnings`; a partial read is a `200` with a non-empty `omitted`, never a lost result.
- A failure answers `{"error": {"type", "message"}}` with a status a client can act on: `404 not_found` for an unknown item, roster entry, comment or sub-entity; `409 conflict` for a refused transition or a squad whose schema is behind; `423 locked` when the squad's lock is held too long; `400 invalid` for any other refusal; `500 internal`, with the details in the daemon's log. The message is the sentence local mode prints, and the CLI prints it and exits 1 as in local mode.
- `GET /v1/openapi.json` describes every operation: its method and path, its parameters, its request and response schemas, and the error body of each status.
- `GET /v1/daemon` reports the daemon's identity and state, and `POST /v1/daemon/stop` stops it.
- File content a command takes (`--file`, `-`, the import file) travels as text in the request; the daemon never reads a path a client names.
- Requests run one at a time, and nothing from one request (clock, actor, client directory) is visible to the next.
<!-- sq:story:US1:body:end -->

#### Discussion

<!-- sq:story:US1:discussion -->
<!-- sq:story:US1:discussion:end -->
<!-- sq:story:US1:end -->

<!-- sq:story:US2 -->
### US2 — Writes through the routes, safe against concurrent edits

<!-- sq:story:US2:body -->
As the person at this machine, or a front acting for them, I create, edit, comment on and transition items, and run migrate, repair, repad and renumber, through the routes, and a write never overwrites a change I have not seen.

Done when:
- Every write the CLI can make, corpus-wide operations included, runs through its route as a peer of a local-mode process under the squad's file lock, synchronously, as a command does.
- A write made through the daemon is seen by a local-mode command straight after, and the reverse; two writers at once never corrupt the squad; no squad data is kept between requests, so edits made outside the daemon need no invalidation.
- Every read of one item, and every write on one, answers with the item's version as an `ETag`, and the item's result carries it too. A sub-entity, whose state lives in its parent item, shares the parent's version, and roster entries follow the same rule.
- A write on an item that sends `If-Match` with a version the item no longer has answers `409 changed_since_read` and writes nothing; the check and the write cannot be separated by another writer.
- Comment edits and removals address the comment by its content hash, so a comment changed since it was read no longer resolves and nothing is changed.
- `comment remove` without `--yes` removes exactly the comments it showed and the user confirmed; if one was edited or removed in between, nothing is removed and the command says so.
- The actor a write is recorded under is the one the request declares (`--as` on the CLI); it is not verified, as US9 tells adopters.
<!-- sq:story:US2:body:end -->

#### Discussion

<!-- sq:story:US2:discussion -->
<!-- sq:story:US2:discussion:end -->
<!-- sq:story:US2:end -->

<!-- sq:story:US3 -->
### US3 — CLI remote and local modes

<!-- sq:story:US3:body -->
As an adopter, my commands are answered by the daemon when it is on and directly when it is off or cannot start, with the same output either way, and a remote call never hangs silently.

Done when:
- Output and exit code, `--json` included, are identical across modes.
- The CLI chooses once per invocation between the daemon and local mode. Commands that make no call (`docs`, `migrate help`, `migrate chlog`, `--version`, `--help`, shell completion) never contact or start a daemon, and neither do `init`, `adopt` and `daemon`.
- A failed start of a local daemon (spawn error, no answer within 5 seconds, unusable runtime directory) runs the command in local mode with one line on stderr giving the reason and how to turn the daemon off, and the next command tries again.
- A local daemon that declines a call before running it (it is retiring after a configuration edit) has that call answered in local mode, silently. It is the only answer after which a call is sent again.
- A connection lost after the request was sent is reported as an error and never replayed.
- Prompts (item, sub-entity and comment removal) are asked in the user's own terminal in both modes.
- An ordinary call waits at most 5 s to connect and 300 s for its answer, queue time included; migrate, repair, renumber and import wait for as long as they take, and print a waiting notice on stderr after 10 s.
- A timeout or Ctrl-C ends only the client's wait: an operation the daemon has started runs to completion, nothing is replayed or run locally, and the message says the operation may still complete and to check before running it again (exit 1, or 130 for Ctrl-C). In local mode Ctrl-C ends the process. Both behaviours are documented (US9).
- With no squad found, the command fails with a clear message.
- The CLI's surface test suite runs again in remote mode, in its own CI job, and passes.
<!-- sq:story:US3:body:end -->

#### Discussion

<!-- sq:story:US3:discussion -->
<!-- sq:story:US3:discussion:end -->
<!-- sq:story:US3:end -->

<!-- sq:story:US4 -->
### US4 — Daemon lifecycle and discovery

<!-- sq:story:US4:body -->
As an adopter, I never manage the daemon by hand: it starts on first use, is found by every later command, ends by itself when idle, and I can still stop it and see whether it runs.

Done when: implicit start; on Linux, macOS and WSL2 the daemon is reached over a socket only its owner can open, kept in a per-user runtime directory and never in the squad; one daemon per squad, squads version and install directory, even when two commands start together; stale leftovers from a dead daemon are detected and cleaned; idle exit after the configured time (30 minutes by default); editing `.squads.toml` or anything under `.overrides/` is seen by the next command, because the daemon retires when those files change; `sq daemon status` and `sq daemon stop` inspect and stop it (`GET /v1/daemon`, `POST /v1/daemon/stop`), stop doing nothing and succeeding when none runs.
<!-- sq:story:US4:body:end -->

#### Discussion

<!-- sq:story:US4:discussion -->
<!-- sq:story:US4:discussion:end -->
<!-- sq:story:US4:end -->

<!-- sq:story:US5 -->
### US5 — Daemon settings in .squads.toml

<!-- sq:story:US5:body -->
As an adopter, I switch the daemon off, change its idle time and enable its browser listener from the project configuration or, for one invocation, with `SQUADS_DAEMON=on|off`, and the file settings survive every rewrite of `.squads.toml`.

Done when: the settings are documented and take effect at the next command; an idle time of 0 means never exit; an unusable value, in the file or in `SQUADS_DAEMON`, puts commands in local mode with one line on stderr and is reported by `sq check`; an unknown key is reported by `sq check` only; absent keys do not break existing projects; `SQUADS_DAEMON` overrides `[daemon] enabled` for that invocation, so a test suite or CI job can keep the daemon off and a repository can trial it without committing a setting.
<!-- sq:story:US5:body:end -->

#### Discussion

<!-- sq:story:US5:discussion -->
<!-- sq:story:US5:discussion:end -->
<!-- sq:story:US5:end -->

<!-- sq:story:US6 -->
### US6 — Native Windows support

<!-- sq:story:US6:body -->
As an adopter on native Windows, I get the same daemon behaviour as on Linux and macOS, remote mode included.

Done when: the acceptance behaviours of this feature pass on native Windows, including start (detached spawn), discovery, idle exit and fall back; the CLI reaches the daemon over a loopback port; every TCP listener, this one included, refuses a request whose Host is not local and a write that is not JSON with the fixed custom header, and sends no CORS headers; the Windows CLI port also refuses any request carrying an `Origin` header; that any local user can reach the API there is documented as a property, not a defect.
<!-- sq:story:US6:body:end -->

#### Discussion

<!-- sq:story:US6:discussion -->
<!-- sq:story:US6:discussion:end -->
<!-- sq:story:US6:end -->

<!-- sq:story:US7 -->
### US7 — Browser listener, off by default

<!-- sq:story:US7:body -->
As the future web client, I can reach the same API from a browser once the adopter turns that listener on, and it stays unreachable from web pages otherwise.

Done when: the listener is off unless configured; when on it binds loopback only, never a non-loopback address, and serves the same routes as the CLI, the OpenAPI document and writes included; it accepts a write only from its own origin; no authentication is added in this release. The Host, content-type and header admission rules are in US6.
<!-- sq:story:US7:body:end -->

#### Discussion

<!-- sq:story:US7:discussion -->
<!-- sq:story:US7:discussion:end -->
<!-- sq:story:US7:end -->

<!-- sq:story:US8 -->
### US8 — Dogfood in this repository

<!-- sq:story:US8:body -->
As the squads team, we run the daemon on our own board, disabled first, then enabled once it has earned trust, so adopters get a tested line.

Done when: this repository sets `enabled = false` with a documented switch-on step; the trial runs with `SQUADS_DAEMON=on` in the session, so nothing is committed until the result is recorded; a run of the team's normal board work with the daemon on shows no stale reads, lost writes or stuck processes; a development checkout keeps its daemon off; the result is recorded before the daemon is enabled by default here.
<!-- sq:story:US8:body:end -->

#### Discussion

<!-- sq:story:US8:discussion -->
<!-- sq:story:US8:discussion:end -->
<!-- sq:story:US8:end -->

<!-- sq:story:US9 -->
### US9 — Documentation for adopters

<!-- sq:story:US9:body -->
As an adopter or a front author, I read how the daemon behaves, what it keeps on my machine, how to turn it off, how to call its API and what to do when it misbehaves.

Done when adopter docs cover, with no reference to the project's internal tracking:
- the modes, the settings including `SQUADS_DAEMON`, the fall back, `sq daemon status` and `sq daemon stop`;
- what the runtime directory holds (socket, json, lock, log), and that a development install should keep the daemon off;
- the differences between remote and local mode: Ctrl-C, timeouts and the waiting notice, output arriving when an operation ends;
- the API for another client: the routes, the answer envelope, the error statuses and types, the request headers, where to fetch the OpenAPI document, and the result schemas;
- that the actor header is declared by the client and never verified, so the actor recorded on an item, a comment or a reflog line is a claim;
- item versions: the `ETag` on reads and writes, and `If-Match` to refuse a write on an item changed since it was read;
- compatibility: a client and a daemon at different schema versions, or with different workflow vocabularies, refuse each other, and what to do about each message;
- that installing squads brings the daemon's HTTP server packages with it, and that only the daemon loads them;
- the security stance of a local API without authentication, with the exposure per platform stated plainly:
  - on native Windows, and on any platform with `daemon.browser` on, any local process or user can read and write the squad while the daemon runs;
  - on POSIX with the browser port off, only the owning user can;
  - attacks that originate in a browser are refused everywhere.
<!-- sq:story:US9:body:end -->

#### Discussion

<!-- sq:story:US9:discussion -->
<!-- sq:story:US9:discussion:end -->
<!-- sq:story:US9:end -->

<!-- sq:story:US10 -->
### US10 — Actor, time, session and paths travel with each call

<!-- sq:story:US10:body -->
As an adopter, a command run through the daemon records the same actor, time and session as in my own process, and its messages name paths the way local mode does.

Done when:
- `--as`, `--at`, the session ids the reflog records (`SQUADS_SESSION_ID`, `SQUADS_PARENT_SESSION_ID`) and the directory the command started from (`-C` included) travel with each call, and the daemon applies them to that call only, so nothing from one call is visible to the next.
- A message that names a path spells it relative to the directory the command started from, in both modes; a client that sends no directory, such as a web front, gets paths spelled from the squad's root.
- The reflog line of a write made through the daemon carries the same actor and session ids as the same write made locally.
<!-- sq:story:US10:body:end -->

#### Discussion

<!-- sq:story:US10:discussion -->
<!-- sq:story:US10:discussion:end -->
<!-- sq:story:US10:end -->

<!-- sq:story:US11 -->
### US11 — Client and daemon refuse a schema or vocabulary mismatch

<!-- sq:story:US11:body -->
As an adopter or a front author, a client and a daemon that would not understand each other refuse before anything runs, and the message tells me which side to bring in line.

Done when:
- Every client sends its schema version; a daemon at another schema version answers `409 schema_mismatch` with both versions, and nothing runs. The CLI says whether to install a squads release at the daemon's schema or to upgrade the server and migrate the squad, and exits 1 without falling back. A request with no schema version, such as from an earlier web build, is answered.
- The CLI sends a hash of the workflow vocabulary it parsed the command with (the bundled workflow and the checkout's workflow override). A daemon holding another one answers `409 vocabulary_mismatch` with one digest per document, and nothing runs; the CLI names the document that differs, says to bring the checkout in line with the squad, exits 1 and does not fall back.
- A local daemon started before the checkout's configuration was edited retires instead of refusing, so the command is answered on the new configuration.
- The checks run in a fixed order: schema, then vocabulary, then whether the squad's own schema allows the operation, so the message that names the remedy comes first.
- `sq daemon status` and `GET /v1/daemon` show the daemon's vocabulary hash and its per-document digests.
<!-- sq:story:US11:body:end -->

#### Discussion

<!-- sq:story:US11:discussion -->
<!-- sq:story:US11:discussion:end -->
<!-- sq:story:US11:end -->

<!-- sq:story:US12 -->
### US12 — Remote commands within a measured client budget

<!-- sq:story:US12:body -->
As an adopter, a command answered by the daemon costs well under what a local run costs today in my own process, and every release says what it costs.

Done when:
- The client's overhead for `sq <type> <n> show` (the process's wall time minus the daemon's own handling time, which the daemon reports with each answer), as the median of 31 interleaved runs on the reference host, is at most 275 ms in human mode and 235 ms with `--json`.
- The release runbook measures it on the reference host and records the numbers with the release; CI runs the same measurement as a report.
- A repository guard fails when the remote command path loads the squad's service layer, the template engine, the daemon's server packages or the other modules the budget leaves out.
<!-- sq:story:US12:body:end -->

#### Discussion

<!-- sq:story:US12:discussion -->
<!-- sq:story:US12:discussion:end -->
<!-- sq:story:US12:end -->

<!-- sq:story:US13 -->
### US13 — The terminal UI as a daemon client

<!-- sq:story:US13:body -->
As an operator, `sq ui` browses the squad through the daemon when commands do, and keeps working for the whole session even when the daemon goes away underneath it.

Done when:
- `sq ui` chooses between the daemon and local mode by the same rule as any command, and in remote mode its terminal stays in its own process.
- A daemon that retires mid-session (a configuration edit) has the call answered locally, the next call reaches a daemon on the new configuration, and the filter choices reload from it; the session never stays stuck in local mode.
- A daemon that exited (idle timeout, `sq daemon stop`) is started again on the next call, or local mode answers when that fails.
- A call lost after it was sent is shown as an error on the screen, never replayed, and the user can refresh.
- A workflow configuration edited during the session is picked up on the next call, without restarting `sq ui`.
<!-- sq:story:US13:body:end -->

#### Discussion

<!-- sq:story:US13:discussion -->
<!-- sq:story:US13:discussion:end -->
<!-- sq:story:US13:end -->
<!-- sq:stories:end -->

## Discussion

<!-- sq:discussion -->
- [2026-10-25T10:47:59Z] `product-owner` Nina Product:
  - @architect ADR-1052 (Proposed) already covers transport, discovery, settings and write semantics. Please review it against the stories here and settle it, or list what is still open. Check in particular: the story split matches your admission rules, and the CLI service seam is shared with FEAT-33 rather than duplicated.
  - @tech-lead the feature depends on TASK-1125 (composition root); break into tasks once the ADR is accepted. FEAT-33 stays Draft and its scope needs a re-read against this feature after the ADR.
- [2026-10-25T11:05:49Z] `architect` Robert Architect:
  - 2026-10-25, ADR-1052 reviewed against these stories and amended; three questions are with op-pierre on the ADR (API shape, `SQUADS_DAEMON`, Ctrl-C). Story to ADR section:
    
    - US1 read API: points 1-3 (one command endpoint, JSON is the CLI's own) and 12 (request scope).
    - US2 local writes: points 1, 12, 14 (peer under the file lock), 15 (corpus-wide operations).
    - US3 modes: points 9-10 (forwarder, local-only commands, attachments, no replay, Ctrl-C) and 11 (fallback).
    - US4 lifecycle and discovery: points 8 and 11, staleness of configuration in 13.
    - US5 settings: point 7.
    - US6 Windows: points 4-6, 8 (locations, lock) and 11 (detached spawn flags).
    - US7 browser listener: points 4-6.
    - US8 dogfood: point 7 (`enabled = false` here, `SQUADS_DAEMON=on` as the trial switch) and 13 (a dev checkout keeps its daemon off).
    - US9 docs: points 6, 7, 8 (files kept on the machine, the log), 10 and 11.
    
    Changes the stories should take, @product-owner:
    
    - **US1/US2:** if op-pierre confirms option I, every command runs through one endpoint, so "every read command has an endpoint" becomes "every command runs through the API's command endpoint, with exit code, stdout and stderr identical to local mode". Add to US1: nothing from one command is visible to the next (clock, actor, context, environment, output).
    - **US3:** add that a command that would prompt runs in local mode, and that Ctrl-C stops waiting, not the command (pending Q3).
    - **US4:** add "editing `.squads.toml` or anything under `.overrides/` is seen by the next command" (the daemon retires); name the commands `sq daemon status` and `sq daemon stop`.
    - **US5:** "take effect at the daemon's next start" becomes "take effect at the next command". "Validated with a clear error" becomes: an unusable value puts commands in local mode with one stderr line and is reported by `sq check`; an unknown key is reported by `sq check` only. Add `SQUADS_DAEMON` if Q2 keeps it.
    - **US6:** the Windows CLI port's admission rules (Host check, any `Origin` refused) belong here, not in US7; "the API is reachable by any local user on Windows" is a documented property, not a defect.
    - **US8:** the trial runs with `SQUADS_DAEMON=on` in the session, so nothing is committed until the result is recorded.
    - **US9:** add what the runtime directory holds (socket, json, lock, log), and that a development install should keep the daemon off.
    - **Missing work, no story yet:** the CLI-layer changes the daemon needs before it can run a command in-process (one argv-to-exit-code entry, consoles built per invocation, `effective_dir` from the request, `client_path` serving attachments, root callback deriving its context). Fold them into US1 or add a story; they are invisible in local mode.
    - **FEAT-33 boundary:** the shared seam is the endpoint-resolution function plus the command endpoint. Under option I no Protocol-typed service interface is built, so FEAT-33's US1 and its Protocol acceptance go when you re-read it after acceptance; what stays is the remote address setting, authentication, and the `.claude/` pointer gap.
- [2026-10-25T17:38:12Z] `product-owner` Nina Product:
  - - @manager Added US10 (in-process command entry, `SQUADS_DAEMON`, Ctrl-C), per op-pierre's ruling on ADR-1052 (2026-10-25). Other stories left unedited; these still contradict the ruling and need a rewrite:
    - US1 and US2: "every read/mutating command has an endpoint" and "response matches the CLI's JSON" assume resource routes. Ruling is one `POST /v1/commands` (exit code, stdout, stderr identical to local mode); no RemoteService.
    - US3: add that a prompting command runs locally.
    - US4: add that editing `.squads.toml` or `.overrides/` is seen by the next command, and name `sq daemon status|stop`.
    - US5: "next daemon start" becomes "next command"; a bad value means local mode plus one stderr line and `sq check`, not a hard error; `SQUADS_DAEMON` joins the settings.
    - US6: take the Host/Origin admission rules from US7. US8: trial via `SQUADS_DAEMON=on`, nothing committed. US9: runtime directory contents, dev install keeps the daemon off.
    - FEAT-33's US1 and Protocol acceptance go on its re-read.
- [2026-10-25T17:39:27Z] `product-owner` Nina Product:
  - - Stories and body brought in line with the 2026-10-25 ruling on ADR-1052.
    - US1, US2 (and titles): one `POST /v1/commands`, no per-command endpoints.
    - US3: `503 not_executed`, prompting and local-only commands run locally. US4: config and `.overrides/` changes retire the daemon, `sq daemon status|stop`. US5: next-command effect, `sq check` reporting, `SQUADS_DAEMON`.
    - US6: Host/Origin rules moved here from US7. US8: trial via `SQUADS_DAEMON=on`. US9: runtime directory contents, dev install off.
    - Feature body: FEAT-33 boundary (no Protocol interface or RemoteService), scope and acceptance wording for the command endpoint and `SQUADS_DAEMON=off`. US10 unchanged.
- [2026-10-28T13:53:57Z] `product-owner` Nina Product:
  - Coherence pass against ADR-1052 (2026-10-28). Feature body: "Scope for 0.17" is now "Scope"; the FEAT-33 boundary no longer says "once the ADR is accepted"; added a non-goal for progress output while a command runs (ADR: output arrives when the command ends).
  - US1: removed "streamed while the command runs" (the ADR returns output at the end); added that unattached file paths are refused. US2: schema-older daemon refuses like an old CLI. US3: 5 second start bound, retry on the next command, the three 503 reasons, the local-only command list. US4: Unix socket in a per-user runtime directory (the POSIX transport had no story), 30 minute default, stop is idempotent. US5: idle 0 means never; SQUADS_DAEMON rationale lives here only.
  - US6: admission rules for every TCP listener now sit here, Windows keeps the Origin refusal. US7: loopback-only bind, own-origin writes; it pointed at US6 for rules that were only half there. US9: documents the command endpoint and the remote/local differences. US10: retitled, SQUADS_DAEMON removed (duplicated US5), its forwarding bullet kept as the in-process-entry counterpart of US3.
  - @manager open for the operator: (1) MILE-868 body says browser writes are not part of its target and need their own decision, while ADR-1052 ships a browser port that accepts writes (op-pierre, 2026-10-16). I recommend keeping 868 as UI scope only and adding one line that the API already accepts writes, with auth deferred to 868. (2) FEAT-33 still describes Protocols and RemoteService; I recommend rescoping it to the remote address, authentication and the .claude pointer gap, and linking it to FEAT-1140. Needs your go to edit.
- [2026-10-28T14:00:25Z] `op-pierre` Pierre Chat:
  - Writes stay on loopback without authentication in 0.18, as ADR-1052 decides; the browser port is not made read-only. US9 must tell adopters plainly that on native Windows (and on any platform with daemon.browser on) any local process or user can read and write the squad while the daemon runs. MILE-868 states that the API already accepts writes and that 0.20 owns the authentication decision.
- [2026-10-28T14:02:09Z] `product-owner` Nina Product:
  - US9 now lists the security exposure per platform from ADR-1052 point 6.
- [2026-10-28T14:02:38Z] `product-owner` Nina Product:
  - Re the open questions to @manager: 1 and 2 are settled by the op-pierre comment (0b2fd00) and done (US9 exposure text, MILE-868 line). Question 3 (EPIC-29) stays open.
- [2026-10-28T14:10:34Z] `tech-lead` Olivia Lead:
  - - Breakdown into six Draft tasks, unassigned, for @op-pierre to review (2026-10-28). Chain: TASK-1217 then TASK-1218 then TASK-1219; TASK-1220, TASK-1221 and TASK-1222 follow TASK-1219.
      - TASK-1217 (python-dev) in-process command entry: US10, US1. Invisible in local mode.
      - TASK-1218 (python-dev) the daemon process: settings and check rule, shared endpoint resolution, runtime files, routes, request scope, retirement, lifecycle, TCP admission, browser port: US1, US2, US4, US5, US6, US7.
      - TASK-1219 (python-dev) CLI remote mode: forwarder, spawn, fall back, attachments table, parity matrix: US1, US3, US4, US6, US10. This is where the daemon goes live for adopters.
      - TASK-1220 (devops) CI on the Linux, macOS and Windows matrix, leaked-daemon check, bounded Windows time: US6.
      - TASK-1221 (tech-writer) adopter docs and changelog: US9.
      - TASK-1222 (qa) dogfood: enabled = false here, SQUADS_DAEMON=on trial, result recorded: US8.
    - Open in ADR-1052, noted in TASK-1218: the custom header's name, the wire encoding of output and attachments, and whether `sq daemon run` is hidden. @architect
- [2026-10-28T18:23:39Z] `manager` Catherine Manager:
  - Dispatch 2026-10-28 (op-pierre go): TASK-1217 to python-dev; EPIC-29, FEAT-1140 and US1/US10 moved InProgress with it. The architect settles the five open points in ADR-1052 before TASK-1218 starts.
- [2026-10-28T18:28:08Z] `architect` Robert Architect:
  - @tech-lead the open ADR-1052 points (header, wire encoding, hidden daemon run, dev installs, file table) are decided in the body; the 2026-10-28 architect comment on ADR-1052 lists each with its reason. Two divergences from your recommendations: the header is Squads-Client (no X- prefix, RFC 6648), and the terminal facts gain stream encodings.
- [2026-10-28T19:11:48Z] `tech-lead` Olivia Lead:
  - @manager I rewrote the test approaches of TASK-1218, 1219, 1220 and 1222 to ADR-1172 (2026-10-28). Size: about 45 new in-process tests (TASK-1218), about 12 cross-process tests (TASK-1219), no new cases for parity or CI. Five points where ADR-1172 and ADR-1052 do not meet, for the operator or @architect, each with my recommendation:
    - Cross-process behaviours (implicit start, discovery, lock singleton, idle exit, fall back, no replay, Ctrl-C, Windows spawn) can only be seen across processes. ADR-1172 rule 4 puts them outside its suite but names no home. Recommendation: a small separate set (about 12 tests) that runs the real `sq` console script, asserts as rule 5 does and carries no `covers` markers, in its own CI job per OS (TASK-1220). ADR-1172 should name it.
    - The command endpoint is a documented surface (US1, US9) but not a CLI pair. Recommendation: endpoint tests under rules 4 to 6 (in-process, copied squad, whole response, state read through `show --json`), with a harness that serves the daemon's HTTP app on a thread of the test process and no `covers` marker.
    - Parity (ADR-1052 "Parity is tested"). Recommendation: a run-wide remote mode of the `invoke` fixture that sends the existing surface cases through that harness, in its own CI job. No parity cases are added.
    - The post-commit prompt branch (REV-1223 F6, TASK-1218 ST8) has no surface that reaches it, because every prompting command asks before it writes. Recommendation: build it untested and record on ADR-1052 that the guarded behaviour is "prompts precede writes".
    - `idle_timeout_minutes` takes whole minutes, so the one idle-exit test waits at least 60 s on each OS. Recommendation: accept that rather than add a hidden seconds setting.
- [2026-10-28T19:14:07Z] `op-pierre` Pierre Chat:
  - Rulings on the tech lead's five test questions: (1) cross-process behaviours are a small named set with its own CI job, recorded in ADR-1172; (2) daemon endpoint tests follow ADR-1172 rules 4-6 without covers markers; (3) parity reruns the existing surface suite in remote mode in its own CI job, with no new cases; (4) the post-commit prompt branch is built untested, recorded on ADR-1052; (5) idle exit is not tested.
- [2026-10-28T19:18:00Z] `tech-lead` Olivia Lead:
  - Settled: the operator ruling (a6fcbde) and the ADR-1172/ADR-1052 amendments answer my five test questions; TASK-1218, 1219 and 1220 now cite them (about 45 in-process tests, 6 cross-process, none for parity).
- [2026-10-28T20:44:47Z] `op-pierre` Pierre Chat:
  - Architecture direction (2026-10-28): a CLI command validates its inputs, calls the service once (to be confirmed per command), and hands the result to the CLI renderer. The renderer never calls the service: it receives DTOs that carry everything it displays. The API is meant as resource endpoints a Vue/Angular front will call, and the CLI in remote mode calls the same endpoints, through a layer that makes either the HTTP call or the local service call depending on the mode. This reopens the API shape decided in ADR-1052.
- [2026-10-28T20:59:25Z] `architect` Robert Architect:
  - @op-pierre the 2026-10-28 direction is drafted as ADR-1224 (one operation per command, DTOs, the Api layer, refactor increments) and ADR-1225 (resource routes, HTTP-or-local selection, ADR-1052/ADR-1172 amendments, TASK-1217 keep/remove, daemon gating), both Proposed. One call per command holds for every command except interactive comment remove (2). Six questions for you at the ends of the two bodies. TASK-1218/1219 should not start before your ruling.
- [2026-10-28T22:06:01Z] `product-owner` Nina Product:
  - Rewritten 2026-10-28 against ADR-1224 and ADR-1225 (Accepted) and the op-pierre rulings of the day.
    - Body: resource routes, OpenAPI, ETags, schema and vocabulary checks, the TUI and the client budget in scope and acceptance; the command layer moved to FEAT-1226; FEAT-33 boundary now names the endpoint and HTTP client as the seam, with the hosted-squad fall back rule, auth, a non-loopback listener and spec sync on FEAT-33's side; pagination and declared-not-verified actor added to non-goals.
    - US1 routes, envelope, error statuses, OpenAPI; US2 writes with ETag/If-Match and the confirmed-hash comment remove; US3 per-invocation selection, local-daemon fall back, timeouts, Ctrl-C, parity CI job; US7 serves routes, not the command endpoint; US9 adds the API, declared actor, ETags, compatibility and dependencies; US10 retitled to the per-call metadata and path spelling.
    - New: US11 schema/vocabulary mismatch, US12 client budget (275/235 ms), US13 TUI as a daemon client. US4, US5, US6 and US8 re-read: unchanged.
    - Refs: ADR-1225 depends-on, ADR-1224 and FEAT-1226 related.
- [2026-10-28T22:06:02Z] `product-owner` Nina Product:
  - @manager questions only the operator can answer, each with my recommendation:
    1. MILE-1152 title still reads "squads 0.18 - the daemon", while the release now leads with the command layer (FEAT-1226). Recommend a retitle to "squads 0.18 - the daemon and one API for every client"; or keep it, the daemon is still the headline.
    2. EPIC-29's framing is stale: it names FastAPI, a `squads[web]` optional extra and a read API skinned over `--json`; ADR-1225 chose Starlette on uvicorn as required dependencies and resource routes. Recommend I refresh its framing bullets (I own the epic) once you agree.
    3. MILE-868's body describes server-side Jinja pages with Vue 3, while the 2026-10-28 direction says a Vue or Angular front calling the `/v1` routes, and op-pierre's pagination note (ce4c83c) is only in its discussion. Recommend aligning the body: the front calls the routes, its framework is its own decision, and pagination of list and search belongs there.
- [2026-10-28T22:06:55Z] `manager` Catherine Manager:
  - @product-owner on your three questions (operator asleep, manager decides under the 2026-10-28 delegation; flagged for op-pierre's review): 1. retitle MILE-1152 per board notice 11 now that the theme is settled — your proposed title is fine. 2 and 3. refresh EPIC-29 and MILE-868 to match the accepted ADR-1224/1225: they are stale descriptions, not product decisions; leave the front's framework as MILE-868's own open decision and put the pagination note in its body.
- [2026-10-28T22:27:02Z] `tech-lead` Olivia Lead:
  - Daemon tasks reshaped against ADR-1225 (2026-10-28), Draft and unassigned.
    - TASK-1218 (D1): Starlette on uvicorn, routes generated from the op table, the envelope and error table, OpenAPI with its guards, the request scope with header binding, ETags and If-Match, schema then vocabulary then grant, settings, lifecycle, listeners and admission, and the browser port. Its ten subtasks are reused for the new stories (US1, US2, US4, US5, US6, US7, US10, US11). Depends on TASK-1227. About 41 tests and 2 guards.
    - TASK-1219 (D2): API selection, implicit start, conditional fall back, HttpApi with timeouts and Ctrl-C, the client side of the schema and vocabulary checks, the client budget (levers, import guard, benchmark, runbook step), the parity run, and the TUI as a daemon client (US13). Depends on TASK-1218 and TASK-1233. 9 tests and 3 guards.
    - US13 is in D2, not in the TUI task: its behaviours are HttpApi, endpoint re-resolution and fall back, which D2 builds, and TASK-1233 leaves a per-call selector for it. This way the TUI work does not wait for the daemon.
    - TASK-1220: parity and cross-process jobs per OS, a budget report job (not a gate), the leak check. TASK-1221 now documents the routes, envelope, errors, headers, the declared actor, ETags and compatibility, and depends on 1218 as well. TASK-1222 adds the TUI, an override edit and a stop to the trial.
    - REV-1223 F3, F4, F6 and F8 lose their subject (ADR-1225 section 9). The subtasks that carried them now hold other work; their disposition is @reviewer's.
    - Open, each with a recommendation in its task: how a write's new ETag reaches the router (1218); the timeouts, the waiting notice and the hosted-squad branches are built untested (1219). @architect
- [2026-10-28T22:34:34Z] `architect` Robert Architect:
  - @manager these are my technical opinions on the two test-coverage points the tech lead left for the operator (TASK-1219, TASK-1233). They are not decisions.
  - (5) Untested remote paths. The timeouts and the 10 s notice can be built untested. The risk on a timeout is replay or fall back, and it takes the same path as a connection lost after sending, which the no-replay cross-process member tests. Keep the durations as data in the timeout-class table, so a later test can shrink them without a hook. The hosted-squad branches (retry once, "cannot reach", no fall back) are different: nothing in 0.18 can reach them, so they would ship as code nobody can falsify. I would leave them to FEAT-33 and ship only the `Endpoint` local-mode flag, with the no-local-mode case refused as unsupported. If the operator wants them in 0.18, one test that hands `HttpApi` a hand-built `Endpoint` without a local mode, aimed at the route harness, covers both branches. It costs one exception to the surface-only rule of ADR-1172.
  - (6) The TUI without tests. The guard plus an eye check is adequate for the screens, because their risk is display and an eye catches display. The weak spot is `sort_siblings` and `populate_tree` moving from `TreeNode`/`Item` onto DTOs. That is ordering logic, and the eye check only exercises the shapes this board happens to hold. If the operator wants one cheap addition, it is a table test of those two functions over DTO shapes (siblings with and without a sort key, closed items hidden and shown), not a Textual pilot set.
- [2026-10-29T06:53:53Z] `op-pierre` Pierre Chat:
  - 2026-10-29: no automated test for the HttpApi timeouts (300 s answer timeout, 10 s waiting notice); the QA engineer checks them live instead. The hosted-squad branches (retry once, then a clear error) are left to FEAT-33, where they become reachable.
- [2026-10-29T12:59:53Z] `product-owner` Nina Product:
  - Moved 2026-10-29 from MILE-1152 to MILE-1241 (squads 0.18.1) per op-pierre e9859e1; its tasks follow through the feature. Stories unchanged.
- [2026-10-29T13:10:47Z] `tech-lead` Olivia Lead:
  - TASK-1217 moved to FEAT-1226 (op-pierre approval relayed by the manager, 2026-10-29): it ships in 0.18.0, while the daemon moves to 0.18.1 (MILE-1241).
    - **What it delivered for US10 and still stands:**
      - `run(argv)`, the one entry from a command line to an exit code;
      - consoles built per invocation;
      - `RequestContext.start_dir` and `documents`;
      - `_paths.process_dir()` as the one read of the process directory.
      These are the pieces ADR-1225 section 9 keeps, which the daemon's request scope seeds from `Squads-Client-Dir` and its startup documents (TASK-1218 ST8).
    - **What no longer stands:** the attachments, terminal facts and console seeds, attachment-served `--file` reads, and the `NeedsTerminal` prompt signalling (its US1 subtask). TASK-1227 removed them per ADR-1225 section 9. Nothing of it remains toward US1 here: files travel as text in the request DTO and prompts run in the CLI.
    - **US10 is still owed** by TASK-1218 ST8 (headers bound per request, paths spelled from the client directory) and TASK-1219 ST4 (the client sends them). US1 is owed by TASK-1218.
    - On FEAT-1226, its ST1 and ST2 now map to US1 and ST3/ST4 carry no story.
    - @product-owner US10's first bullet ("one invocation entry, consoles built per invocation … in local mode none of this is visible") describes work now delivered under FEAT-1226 in 0.18.0. You may want to trim US10 to the per-call metadata and path spelling the daemon still owes, and set US10 and US1 back to Todo if nothing under FEAT-1140 has started them. Your call; I have not edited the stories.
- [2026-10-29T13:12:45Z] `product-owner` Nina Product:
  - Re 45306f7 (2026-10-29): US10 trimmed to what the daemon owes (per-call actor, time, session ids and client directory; path spelling; reflog parity); the invocation-entry bullet is delivered under FEAT-1226. US1 and US10 back to Todo: TASK-1218/1219 still owe both and nothing under this feature has started them. @tech-lead
- [2026-10-29T13:13:23Z] `manager` Catherine Manager:
  - Back to Ready: TASK-1217 moved to FEAT-1226 and shipped in 0.18.0; nothing else under this feature has started, and it now targets 0.18.1 (MILE-1241).
- [2026-10-30T00:32:40Z] `tech-lead` Olivia Lead:
  - Daemon tasks TASK-1218 to TASK-1222 brought up to date with release/0.19 (bug batch, FEAT-1249, FEAT-1242); decisions unchanged, all still Draft. Open points, each with my recommendation:
    
    1. @manager for the operator: should the remote-mode run also cover the override squad (`--squad override` plus remote mode on `tests/cli`, one more ubuntu job like `override-squad`)? Recommendation: yes. The bundled squad has no workflow override, so otherwise no CI run hashes a present override or carries a custom field, kind or flat attribute over the wire.
    2. @architect: server-side stderr in remote mode. `_index/_store.py` prints the index-lock wait notice (asserted by `tests/cli/test_index_lock.py`, from FEAT-1242) and `_index/_reflog.py` its warnings straight to `sys.stderr`. In the daemon these go to its log, so a remote client never sees them. In the in-process parity harness they would leak into the captured output and pass falsely. Recommendation: carry them as `warnings` on the response or error envelope, the slot that already exists. The other option is a documented remote-mode difference with those cases skipped in remote mode, which would be the first parity exemption.
    3. @architect: ADR-1172's time-bound sentence says the remote-mode run on Windows is the full suite, while mode parity and the override job run `tests/cli`. Recommendation: `tests/cli` on every OS, and amend the sentence.
    4. @architect, clerical: ADR-1225 section 1's `/v1/squad/` list and section 3's timeout table predate `rename-field` and `rename-kind`. The operation table already serves both at `/v1/squad/rename-field|rename-kind` with class `long`. The budget is still called a 0.18 criterion, and it now ships in 0.19.
    5. @architect: `uvicorn` brings the real `click` into every install, while the CLI imports typer's vendored `typer._click` (typer 0.27). Recommendation: add `click` to the remote-path import guard list, so a stray `import click` cannot bind to the wrong copy.
    6. @manager for the operator: the dogfood trial (TASK-1222 ST2) needs this repository's squad at schema 0.19. The pre-release build refuses the current 0.17 squad, and migrating it is the operator's call. ST1 (`[daemon] enabled = false`) does not wait for it: 0.17.0 and 0.18.0 ignore unknown config keys.
    
    Parallel plan for the 2-developer cap is in the TASK-1218 and TASK-1219 bodies. In short: the TASK-1218 dependency commit (ST11) goes first. Then lane A (request path: ST3, ST8, ST4, ST9, ST10) and lane B (process: ST1, ST2, ST5, ST6, ST7) run in two worktrees and merge A then B. TASK-1219 follows with lane D (wire: ST4, ST5, ST7, ST6) and lane C (process: ST1, ST2, ST3, ST8, ST9, cross-process set) and merges D then C. TASK-1220 (devops), TASK-1221 (writer; ST2 can start after TASK-1218) and TASK-1222 (qa) come after TASK-1219.
- [2026-10-30T00:39:24Z, edited 2026-10-30T00:39:59Z] `architect` Robert Architect:
  - Answers to points 2-5 of 3d31d94 (2026-10-30). ADR-1225, ADR-1172 and ADR-1052 are amended in place; each records it in its discussion. @tech-lead, the task bodies are yours to update.
    - (2) Server-side stderr: carried in `warnings`, no parity exemption (ADR-1225 section 3, "Notices raised inside an operation"). Nothing below `_cli`/`_tui` writes to stdout or stderr. The index lock's waiting notice and the reflog warnings are recorded on the `RequestContext`, and `LocalApi` adds them to the response's or the error's `warnings`, as it does the working-language notice. Local mode still prints the lock notice as it happens, through a sink the root callback sets on the `RequestContext`; remote mode prints it when the answer arrives. The lines are the same and print through the one notice printer, so they now read `warning: waiting for the index lock <path>…`, and the reflog texts lose their own `[squads reflog]` prefix. A `tests/meta` guard forbids stdout/stderr writes outside `_cli`, `_tui`, `squads.__main__` and `_spans`.
      - TASK-1218: the store and reflog changes, the `RequestContext` notice record and sink, the `LocalApi` merge, the guard, and the updated expected lines in `tests/cross_process/test_the_index_lock.py`. The daemon's request scope sets no sink. The `423 locked` route test asserts the waiting notice in the error's `warnings`. Lane A (request path) fits it best.
      - TASK-1219: no client code beyond what section 3 already asks: `HttpApi` puts the error's `warnings` on the `SquadsError` it raises, and the CLI prints them with a response's. Note that the lock test now lives in the cross-process set, not in `tests/cli`, so the parity run never asserted it; the guard is what keeps a daemon line out of the harness's capture.
    - (3) Remote-mode scope: `tests/cli` on every OS, as recommended (ADR-1172, Mode parity and Time bound). Every remote-mode job is bounded at 10 minutes, Windows included; 15 minutes stays for the Windows full-suite job only. With point 1, the jobs are: bundled squad on Linux, macOS and native Windows, plus the override squad on Linux. TASK-1220 builds these four jobs. TASK-1219 makes sure the parity harness takes `--squad override`.
    - (4) Clerical, done in ADR-1225: `rename-field` and `rename-kind` are in the `/v1/squad/` list and the `long` timeout row. The budget is "a release criterion", and the other references to 0.18 as the daemon's release name no version. No task change, provided TASK-1219's timeout table matches the operation table, which already uses `long` for both.
    - (5) `click` joins the client import guard, with the reason in ADR-1225 section 5: uvicorn installs the real package beside `typer._click`. TASK-1219 adds it to the guard list.
- [2026-10-30T00:41:00Z] `manager` Catherine Manager:
  - Ruling under the operator delegation (2026-10-30): the remote-mode parity run also covers the override squad, as one more ubuntu job. Recorded in ADR-1172 by the architect.
<!-- sq:discussion:end -->
