---
id: MILE-1241
sequence_id: 1241
type: milestone
title: squads 0.18.1 - the daemon
status: Draft
author: product-owner
refs:
- MILE-1152:depends-on
- EPIC-29
description: The daemon serving the command layer's operations as resource routes,
  with dependencies upgraded and tested
created_at: '2026-10-29T12:59:12Z'
updated_at: '2026-10-29T12:59:50Z'
---
<!-- sq:body -->
The daemon release: a local process that serves the squad as resource routes on the adopter's own machine, and a CLI and terminal UI that call those routes or read the squad directly, with the same output either way. It builds on the command layer of 0.18.0, whose operations the routes serve. It makes that line usable on one machine, for one person; the browser frontend (MILE-868) builds on the same routes.

Scope is carried by two features:

- **FEAT-1140**, the daemon: the resource routes and their errors, the OpenAPI document, the CLI's remote and local modes, item versions on writes, the schema and vocabulary checks, the terminal UI as a daemon client, the client budget, the daemon's lifecycle and settings, and native Windows. Decided in ADR-1052 and ADR-1225.
- **FEAT-1242**, dependencies current and tested: the versions an adopter installs are the versions the suite runs, with the daemon's new server dependencies among them.

The release is ready when the terminal UI works through the API in both modes, the client budget (at most 275 ms of client overhead in human mode and 235 ms with `--json` for `sq <type> <n> show` on the reference host) is met and recorded, the CLI's tests pass in both modes on Linux, macOS and native Windows, and the declared lower bounds of every dependency are the versions the suite ran.

Authentication, a squad hosted on another machine (FEAT-33), pagination and the frontend itself are out of scope.

Membership works through incoming `targets` refs; the roll-up below inverts them.

<!-- sq:view:milestone_rollup -->
<!-- sq:body:end -->

## Discussion

<!-- sq:discussion -->
- [2026-10-29T12:59:50Z] `product-owner` Nina Product:
  - Created 2026-10-29 per op-pierre e9859e1 on MILE-1152: the daemon (FEAT-1140, its tasks TASK-1218 to 1222 following through the feature) and the dependency upgrade (FEAT-1242). Depends on MILE-1152 for the command layer.
<!-- sq:discussion:end -->
