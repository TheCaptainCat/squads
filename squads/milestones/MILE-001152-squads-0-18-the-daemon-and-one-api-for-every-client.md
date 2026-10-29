---
id: MILE-1152
sequence_id: 1152
type: milestone
title: squads 0.18 - the daemon and one API for every client
status: InProgress
author: product-owner
description: Resource routes the CLI, terminal UI and web client share, with the daemon
  behind them and JSON output on every command
created_at: '2026-10-25T21:16:14Z'
updated_at: '2026-10-28T22:07:56Z'
---
<!-- sq:body -->
The daemon release: a local process that serves the squad as resource routes on the adopter's own machine, and a CLI and terminal UI that call those routes or read the squad directly, with the same output either way. It makes that line usable on one machine, for one person; the browser frontend (MILE-868) builds on the same routes.

Scope is carried by two features, in this order:

- **FEAT-1226**, the command layer: every command calls one operation and renders its result, `--json` on every command that prints one, results that carry their own display, and the terminal UI reading through the same API. Decided in ADR-1224.
- **FEAT-1140**, the daemon: the resource routes and their errors, the OpenAPI document, the CLI's remote and local modes, item versions on writes, the schema and vocabulary checks, the terminal UI as a daemon client, the daemon's lifecycle and settings, and native Windows. Decided in ADR-1052 and ADR-1225.

The release is ready when every command runs on its operation, the terminal UI works through the API in both modes, the client budget (at most 275 ms of client overhead in human mode and 235 ms with `--json` for `sq <type> <n> show` on the reference host) is met and recorded, and the CLI's tests pass in both modes on Linux, macOS and native Windows.

Authentication, a squad hosted on another machine (FEAT-33), pagination and the frontend itself are out of scope.

Membership works through incoming `targets` refs; the roll-up below inverts them.

<!-- sq:view:milestone_rollup -->
<!-- sq:body:end -->

## Discussion

<!-- sq:discussion -->
- [2026-10-28T13:48:28Z] `manager` Catherine Manager:
  - 0.18 opened 2026-10-28 by op-pierre; FEAT-1140 is the scope, its dependencies (ADR-1052, TASK-1125) are settled.
- [2026-10-28T20:45:29Z] `op-pierre` Pierre Chat:
  - Scope (2026-10-28): 0.18 carries both the DTO refactor (one service call per command where possible, renderer fed DTOs and never calling the service) and the daemon's resource endpoints with the CLI's HTTP-or-local layer. See the op-pierre direction on FEAT-1140.
- [2026-10-28T21:58:00Z] `op-pierre` Pierre Chat:
  - 2026-10-28: the manager drives 0.18 overnight. Order: product owner scope, then tech lead breakdown; move to Ready if coherent; then the dev/review loop, the DTO refactor first and the daemon after.
- [2026-10-28T22:06:05Z] `product-owner` Nina Product:
  - Body and summary aligned 2026-10-28 with the new scope: FEAT-1226 (command layer, first) and FEAT-1140 (daemon), the release gate from ADR-1225 (every command on its operation, TUI in both modes, the 275/235 ms client budget, tests in both modes on three OSes), FEAT-33 and pagination out of scope. Title question raised on FEAT-1140.
- [2026-10-28T22:07:56Z] `product-owner` Nina Product:
  - Retitled 2026-10-28 to "squads 0.18 - the daemon and one API for every client" per board notice 11, decided by the manager (FEAT-1140, 027ea69).
<!-- sq:discussion:end -->
