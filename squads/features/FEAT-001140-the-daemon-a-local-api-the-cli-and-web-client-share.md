---
id: FEAT-1140
sequence_id: 1140
type: feature
title: 'The daemon: a local API the CLI and web client share'
status: Draft
parent: EPIC-29
author: product-owner
priority: high
refs:
- FEAT-33
- ADR-1052:depends-on
- TASK-1125:depends-on
- MILE-1152:targets
description: A local process serving squad state over one API, used by the CLI in
  remote mode and later the browser; local mode stays
subentities:
- local_id: US1
  title: Every command runs through one command endpoint
  status: Todo
- local_id: US2
  title: Local writes through the command endpoint
  status: Todo
- local_id: US3
  title: CLI remote and local modes
  status: Todo
- local_id: US4
  title: Daemon lifecycle and discovery
  status: Todo
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
  title: In-process command entry, SQUADS_DAEMON and Ctrl-C
  status: Todo
created_at: '2026-10-25T10:47:24Z'
updated_at: '2026-10-25T21:16:33Z'
---
<!-- sq:body -->
## Problem

Every `sq` invocation starts cold: it builds the CLI, loads the vocabulary and 
reads the squad again, then exits. Nothing is kept between two commands, and 
there is no way for anything other than the CLI to ask a running process about 
the squad. The browser frontend (MILE-868) needs exactly that, and the CLI 
itself would benefit from the same door.

## What the daemon gives an adopter

- A local process that serves squad state over an API on the adopter's own 
machine, and answers the same questions the CLI answers today.
- A CLI that uses it without being asked: the first command starts the daemon, 
later commands are answered by it, and the daemon exits by itself after a quiet 
period.
- Local mode kept as it is: with the daemon switched off, or when it cannot 
start, the CLI reads and writes the squad directly, as today.
- One API for every client. The CLI's remote mode and the future browser 
frontend call the same endpoints (op-pierre ruling, 2026-10-16); there is no 
second protocol.

## Scope for 0.17

- The local API: one command endpoint that runs the CLI's own commands, plus daemon status and stop, covering reads and local 
single-user writes, and everything local mode does including migrate, repair, 
repad and renumber.
- The CLI's two modes, remote (answered by the daemon) and local (direct), with 
the fall back from the first to the second when the daemon cannot start.
- The daemon's lifecycle: implicit start, discovery, staleness, idle exit, stop,
and settings in `.squads.toml`.
- Native Windows supported, remote mode included.
- This repository dogfooding the daemon, switched off at first and enabled once 
it has earned trust.
- The browser-facing listener exists but is off by default.

The transport, the protocol, the discovery scheme and the write semantics are 
decided by the architect in ADR-1052; this feature states outcomes and leaves 
those choices to it.

## Non-goals

- The browser frontend (MILE-868, 0.19). It consumes this API and is not built 
here.
- Authentication and authorization. The API assumes a trusted local caller.
- Remote or multi-user access, and anything that needs the daemon reachable 
beyond the adopter's machine.
- Cutting the fixed startup cost of a local invocation (FEAT-916, Done): the 
daemon is measured against that lean baseline, not a substitute for it.

## Boundary with FEAT-33

FEAT-33 is the client side of a squad hosted elsewhere. This feature delivers the server side on one machine and the first working use of that seam: the CLI talks to a daemon on localhost through one command endpoint, which the web client shares. No Protocol-typed service interface or second service implementation is built; the shared seam is the endpoint-resolution function plus the command endpoint. FEAT-33 keeps the remote address setting, authentication and the pointer gap in `.claude/`, and its scope is re-read against this feature once the ADR is accepted.

## Acceptance criteria

- On a machine with the daemon enabled, running any `sq` command starts a daemon
if none is running, and the command's output is identical to local mode, 
including `--json`.
- A second command is answered by the same daemon; stopping it, or leaving it 
idle for the configured time, ends the process and removes its runtime files.
- With the daemon disabled in `.squads.toml` or by `SQUADS_DAEMON=off`, `sq` never starts or contacts one.
- When the daemon cannot start and the squad is on the machine, the command 
still succeeds in local mode and one line on stderr says why.
- A write made through the daemon is visible to a plain local-mode command right
after, and the reverse, with no stale answer.
- Two commands started at once end up on one daemon.
- The same behaviour holds on Linux, macOS and native Windows.
- A client other than the CLI can read and write the squad by running commands through the documented command endpoint.
- This repository runs with the daemon disabled and a documented step to enable 
it.
<!-- sq:body:end -->

## User Stories

_Add with `sq feature 1140 add-story "As a <role>, I want … so that …"`; track with `sq feature 1140 story <n> update --status <Status>`._

<!-- sq:stories -->

<!-- sq:story:US1 -->
### US1 — Every command runs through one command endpoint

<!-- sq:story:US1:body -->
As an adopter or a tool author, I run any `sq` command through the daemon's one command endpoint and get the same exit code, stdout and stderr as in local mode, `--json` included, so a client never parses anything but the CLI's own output.

Done when: `POST /v1/commands` takes the command's arguments, the client directory, a fixed list of environment variables, terminal facts and file attachments, and answers with exit code, stdout and stderr (streamed while the command runs); every command of the CLI runs through it; errors carry the same message and exit code as in local mode; commands run one at a time, each with a fresh context, so nothing from one command is visible to the next.
<!-- sq:story:US1:body:end -->

#### Discussion

<!-- sq:story:US1:discussion -->
<!-- sq:story:US1:discussion:end -->
<!-- sq:story:US1:end -->

<!-- sq:story:US2 -->
### US2 — Local writes through the command endpoint

<!-- sq:story:US2:body -->
As the person at this machine, I create, edit, comment on and transition items, and run migrate, repair, repad and renumber, through the same command endpoint, so the CLI's remote mode does everything local mode does.

Done when: every mutating command, including migrate, repair, repad and renumber, runs through `POST /v1/commands` as a peer of a local-mode process under the squad's file lock; a write made through the daemon is seen by a local-mode command straight after and the reverse; two writers at once never corrupt the squad; no squad data is kept between commands, so edits made outside the daemon need no invalidation.
<!-- sq:story:US2:body:end -->

#### Discussion

<!-- sq:story:US2:discussion -->
<!-- sq:story:US2:discussion:end -->
<!-- sq:story:US2:end -->

<!-- sq:story:US3 -->
### US3 — CLI remote and local modes

<!-- sq:story:US3:body -->
As an adopter, my commands are answered by the daemon when it is on and directly when it is off or cannot start, with the same output either way.

The in-process entry, `SQUADS_DAEMON` and Ctrl-C are in US10.

Done when: output including --json is identical across modes; a failed daemon start falls back to local mode with one line on stderr; the answer `503 not_executed` is the only one after which the client runs the command itself; a connection lost after a request was sent is reported as an error and never replayed locally; a command that would prompt, or is local-only, runs in local mode; with no local squad the command fails with a clear message.
<!-- sq:story:US3:body:end -->

#### Discussion

<!-- sq:story:US3:discussion -->
<!-- sq:story:US3:discussion:end -->
<!-- sq:story:US3:end -->

<!-- sq:story:US4 -->
### US4 — Daemon lifecycle and discovery

<!-- sq:story:US4:body -->
As an adopter, I never manage the daemon by hand: it starts on first use, is found by every later command, ends by itself when idle, and I can still stop it and see whether it runs.

Done when: implicit start; one daemon per squad, squads version and install directory, even when two commands start together; stale leftovers from a dead daemon are detected and cleaned; idle exit after the configured time; editing `.squads.toml` or anything under `.overrides/` is seen by the next command, because the daemon retires when those files change; `sq daemon status` and `sq daemon stop` inspect and stop it (`GET /v1/daemon`, `POST /v1/daemon/stop`).
<!-- sq:story:US4:body:end -->

#### Discussion

<!-- sq:story:US4:discussion -->
<!-- sq:story:US4:discussion:end -->
<!-- sq:story:US4:end -->

<!-- sq:story:US5 -->
### US5 — Daemon settings in .squads.toml

<!-- sq:story:US5:body -->
As an adopter, I switch the daemon off, change its idle time and enable its browser listener from the project configuration or, for one invocation, with `SQUADS_DAEMON=on|off`, and the file settings survive every rewrite of `.squads.toml`.

Done when: the settings are documented and take effect at the next command; an unusable value puts commands in local mode with one line on stderr and is reported by `sq check`; an unknown key is reported by `sq check` only; absent keys do not break existing projects; `SQUADS_DAEMON` overrides `[daemon] enabled`.
<!-- sq:story:US5:body:end -->

#### Discussion

<!-- sq:story:US5:discussion -->
<!-- sq:story:US5:discussion:end -->
<!-- sq:story:US5:end -->

<!-- sq:story:US6 -->
### US6 — Native Windows support

<!-- sq:story:US6:body -->
As an adopter on native Windows, I get the same daemon behaviour as on Linux and macOS, remote mode included.

Done when: the acceptance behaviours of this feature pass on native Windows, including start (detached spawn), discovery, idle exit and fall back; the Windows loopback port refuses any request whose Host is not local and any request carrying an `Origin` header; that any local user can reach the API there is documented as a property, not a defect.
<!-- sq:story:US6:body:end -->

#### Discussion

<!-- sq:story:US6:discussion -->
<!-- sq:story:US6:discussion:end -->
<!-- sq:story:US6:end -->

<!-- sq:story:US7 -->
### US7 — Browser listener, off by default

<!-- sq:story:US7:body -->
As the future web client, I can reach the same API from a browser once the adopter turns that listener on, and it stays unreachable from web pages otherwise.

Done when: the listener is off unless configured; when on it serves the same endpoints as the CLI, the command endpoint included; no authentication is added in this release. The Host and Origin admission rules are in US6.
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
As an adopter, I read how the daemon behaves, what it keeps on my machine, how to turn it off and what to do when it misbehaves.

Done when: adopter docs cover the modes, the settings including `SQUADS_DAEMON`, the fall back, `sq daemon status` and `sq daemon stop`, what the runtime directory holds (socket, json, lock, log), that a development install should keep the daemon off, and the security stance of a local API without authentication, with no reference to the project's internal tracking.
<!-- sq:story:US9:body:end -->

#### Discussion

<!-- sq:story:US9:discussion -->
<!-- sq:story:US9:discussion:end -->
<!-- sq:story:US9:end -->

<!-- sq:story:US10 -->
### US10 — In-process command entry, SQUADS_DAEMON and Ctrl-C

<!-- sq:story:US10:body -->
As an adopter, the same `sq` command gives the same result whether it runs in my process or is forwarded to the daemon, and I can choose which with one environment variable.

US3 already covers output parity across modes, the fall back to local mode and no replay after a sent request. This story covers what US1-US9 do not state.

Done when:
- A command runs in-process as one request: one argv-to-exit-code entry, a console built per invocation, the directory taken from the request (`-C` included), file attachments served from the request, and the root callback deriving its context from the request. Nothing from one command is visible to the next (clock, actor, context, environment, output). In local mode none of this is visible.
- The CLI forwards a command to the daemon through the one command endpoint, and the daemon runs the same command path the local CLI runs. No second client or service interface is built.
- `SQUADS_DAEMON=on` or `off` overrides `[daemon] enabled` for that invocation, so a test suite or CI job can keep the daemon off and a repository can trial it without committing a setting.
- Ctrl-C in remote mode stops only the client wait: a command the daemon has already started runs to completion and is not replayed. In local mode Ctrl-C ends the process. Both behaviours are documented.
<!-- sq:story:US10:body:end -->

#### Discussion

<!-- sq:story:US10:discussion -->
<!-- sq:story:US10:discussion:end -->
<!-- sq:story:US10:end -->
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
<!-- sq:discussion:end -->
