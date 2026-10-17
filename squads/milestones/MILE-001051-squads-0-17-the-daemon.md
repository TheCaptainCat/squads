---
id: MILE-1051
sequence_id: 1051
type: milestone
title: squads 0.17 - the daemon
status: Draft
author: product-owner
created_at: '2026-10-16T11:23:46Z'
updated_at: '2026-10-16T11:25:09Z'
---
<!-- sq:body -->
The daemon release: a local process that serves squad state over an API on localhost, and a CLI that can talk to it. This milestone holds the work that makes that line usable on one machine, for one person. The web epic carries the larger outcome and the framing; the browser frontend builds on this milestone.

**Belongs here**

- The local API. It serves and listens on localhost with no authentication. The transport (an HTTP port versus a Unix socket) is open and goes to an ADR before the API is built; this milestone does not presuppose the answer.
- The CLI's two modes: remote mode, where a command is answered by a running daemon, and local mode, which is today's behaviour of reading the squad directly.
- The daemon logic: its lifecycle (start, stop, discovery, staleness) and what it keeps warm between calls.
- Writes through the daemon. The CLI's remote mode needs them, so mutation reaches the API. They are local and single-user: the actor is the person at that machine, and nothing here opens a write path to a shared URL.
- This repo dogfooding the line, with daemon mode disabled at first and enabled once it has earned trust.

**Does not belong here**

- The browser frontend, which has its own milestone and consumes this API.
- Remote or multi-user access, and anything that needs the daemon reachable beyond localhost.
- Authentication and authorization. The API assumes a trusted local caller.
- Cutting the fixed startup cost of every invocation unless it is chosen to ride this release; it is useful with or without a daemon.
- Engine or vocabulary changes the API merely consumes.

Membership works through incoming `targets` refs; the roll-up below inverts them.

<!-- sq:view:milestone_rollup -->
<!-- sq:body:end -->

## Discussion

<!-- sq:discussion -->
- [2026-10-16T11:24:10Z] `product-owner` Nina Product:
  - @manager Proposal for the operator, nothing created yet.
    
    - Epic: yes, a new epic for the daemon line, separate from EPIC-29. EPIC-29's outcome is a browsable web view; the daemon is infrastructure that outlives it (CLI speed, remote mode, the TUI and editor could consume it). Keeping them apart lets 0.17 close on its own outcome and EPIC-29 stay the browser epic.
    - Features under it, each with stories: (1) local API on localhost, no auth, thin over the frozen --json shapes, reads and local single-user writes; (2) CLI remote and local modes, including the choice and fallback between them; (3) daemon lifecycle and warm state (start, stop, discovery, staleness); (4) dogfood rollout, daemon mode disabled here at first.
    - ADR first, architect-owned: transport (HTTP port versus Unix socket), plus daemon discovery and the write semantics. The API feature depends on it.
    - Order follows Pierre's sequence: API, then CLI modes, then daemon logic, with the dogfood last. Pierre's sequence puts the frontend fourth; it stays in MILE-868, which now depends on this milestone.
    - FEAT-916 (cut the fixed startup cost): recommend targeting 0.17 as a candidate, not a commitment. Pro: Pierre's own note says it is picked up alongside the daemon work, it is local CLI work with measurements already on the record, and it sets the honest baseline the daemon must beat (about 0.7s fixed cost, of which the daemon buys back only the remainder). Con: it does not depend on the daemon and could slip without blocking it. Recommendation: target it, sequence it first in the release so the daemon's value is measured against the lean baseline. It currently sits under EPIC-31; keep that parent, the milestone link is a targets ref, not a parent change. Operator to rule.
    - EPIC-29 keeps the browser features; its framing text still describes the server and read API, so it needs a refresh once the new epic exists (not done here).
- [2026-10-16T11:25:09Z] `op-pierre` Pierre Chat:
  - 2026-10-16: the CLI's remote mode and the browser frontend must hit the same API endpoints. One API, two clients; no separate daemon protocol.
<!-- sq:discussion:end -->
