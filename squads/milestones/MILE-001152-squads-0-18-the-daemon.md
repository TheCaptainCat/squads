---
id: MILE-1152
sequence_id: 1152
type: milestone
title: squads 0.18 - the daemon
status: InProgress
author: product-owner
description: A local API the CLI and the web client share, with the daemon behind
  it
created_at: '2026-10-25T21:16:14Z'
updated_at: '2026-10-28T13:53:34Z'
---
<!-- sq:body -->
The daemon release: a local process that serves squad state over one API on localhost, and a CLI that can talk to it. It makes that line usable on one machine, for one person; the browser frontend (MILE-868, 0.20) builds on it.

Scope is carried by the daemon feature (FEAT-1140), which holds the API, the CLI's remote and local modes, the daemon lifecycle and the local writes, and by the transport decision (ADR-1052). Authentication, remote access and the frontend itself are out of scope.

Membership works through incoming `targets` refs; the roll-up below inverts them.

<!-- sq:view:milestone_rollup -->
<!-- sq:body:end -->

## Discussion

<!-- sq:discussion -->
- [2026-10-28T13:48:28Z] `manager` Catherine Manager:
  - 0.18 opened 2026-10-28 by op-pierre; FEAT-1140 is the scope, its dependencies (ADR-1052, TASK-1125) are settled.
<!-- sq:discussion:end -->
