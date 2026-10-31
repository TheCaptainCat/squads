---
id: MILE-868
sequence_id: 868
type: milestone
title: squads 0.21 - the web frontend
status: Draft
author: product-owner
refs:
- EPIC-29
- MILE-1241:depends-on
created_at: '2026-09-02T08:03:39Z'
updated_at: '2026-10-31T08:55:43Z'
---
<!-- sq:body -->
A squad readable in a browser: the squad's state stops being visible only to whoever is sitting at the terminal. This milestone holds the work that brings the browser surface to a first usable state. The linked epic carries the outcome and the framing. The surface is built on the daemon milestone's API, which it depends on.

The front calls the daemon's resource routes under `/v1`, the same routes the CLI and the terminal UI use, and generates its types from the OpenAPI document they publish. Every result already carries its display labels and badges, so the front holds no copy of the vocabulary. The routes already accept writes on the browser port (off by default, loopback only, no authentication), with item versions that refuse a write on an item changed since it was read; the actor a request names is declared, not verified. This milestone owns the authentication decision for that port.

**Belongs here**

- The browser frontend, calling the `/v1` routes. Its framework, and whether pages are also rendered on the server, are this milestone's own open decision.
- The browse surface itself: tree, item, refs, discussion.
- The authentication decision for the browser port.
- Pagination of list and search results: their results are unpaginated until the web front needs it (op-pierre, 2026-10-28).
- Freezing the result shapes the front consumes: shapes that had no `--json` before the daemon milestone stay provisional until then.

**Does not belong here**

- The routes, the CLI's remote and local modes, and the daemon logic. They live in the daemon milestone, and this milestone consumes them.
- Write screens in the browser. Mutation reachable from a shared URL raises actor questions this milestone does not answer; they take their own decision first, and that decision is not part of the target. (The write routes of the daemon already exist and belong to the daemon milestone.)
- The other browse clients. The terminal UI and the editor extension have their own homes; only work whose reason for existing is the web surface aims here.
- Engine or vocabulary changes the web view merely consumes.

<!-- sq:view:milestone_rollup -->
<!-- sq:body:end -->

## Discussion

<!-- sq:discussion -->
- [2026-09-02T08:04:47Z] `product-owner` Nina Product:
  - Linked to the sq web epic with a plain related ref, not membership: the roll-up inverts incoming targets refs only, so the shell stays empty while the epic's outcome and framing stay one hop away instead of being restated here and drifting.
- [2026-10-16T11:22:52Z] `op-pierre` Pierre Chat:
  - 2026-10-16: split this milestone. A new milestone, squads 0.17, is the daemon release: the API (serves and listens on localhost, no authentication), the CLI's remote and local modes, and the daemon logic. This milestone keeps only the browser frontend and builds on 0.17. Transport (HTTP port vs Unix socket) is undecided and goes to an ADR.
- [2026-10-16T11:51:38Z] `op-pierre` Pierre Chat:
  - 2026-10-16: this milestone becomes squads 0.18 (the web frontend), after 0.17 (MILE-1051, the daemon).
- [2026-10-16T13:39:35Z] `op-pierre` Pierre Chat:
  - 2026-10-16: renumbered to 0.19; the backends release takes 0.18 because supported backends take priority over the web frontend.
- [2026-10-28T13:54:00Z] `product-owner` Nina Product:
  - @manager the body says browser write paths are not part of the target, but ADR-1052 (op-pierre, 2026-10-16) ships a browser port that accepts writes in 0.18, with authentication left to this milestone. Pending the operator, I suggest one line here stating the API already accepts writes and this milestone owns the authentication decision.
- [2026-10-28T14:02:07Z] `product-owner` Nina Product:
  - Body states the daemon API already accepts writes on the browser port (off by default, loopback only, no authentication) and that this milestone owns the authentication decision, per op-pierre on FEAT-1140 (2026-10-28).
- [2026-10-28T21:53:27Z] `op-pierre` Pierre Chat:
  - 2026-10-28: pagination of list and search DTOs is for later, with the web front.
- [2026-10-28T22:07:55Z] `product-owner` Nina Product:
  - Body aligned 2026-10-28 per the manager (FEAT-1140, 027ea69) with ADR-1224/ADR-1225: the front calls the /v1 routes and generates types from OpenAPI; its framework (and any server rendering) is this milestone's open decision; writes carry item versions and a declared actor; pagination (op-pierre ce4c83c) and freezing the provisional shapes now belong here.
- [2026-10-29T12:59:55Z] `product-owner` Nina Product:
  - Now depends on MILE-1241 (squads 0.18.1, the daemon) instead of MILE-1152, since the daemon moved there (op-pierre e9859e1, 2026-10-29).
- [2026-10-31T08:27:10Z] `op-pierre` Pierre Chat:
  - Multi-squad daemon (one process serving several registered squads) is deferred, to be reconsidered with the web front (2026-10-31). Today one daemon serves one squad per installation; the service layer already threads its context, the work would be in the daemon (per-squad state, squad selection per request, per-squad retirement, discovery).
- [2026-10-31T08:55:43Z] `op-pierre` Pierre Chat:
  - The VS Code extension moves to the daemon's resource routes with the web front (2026-10-31): discovery through one sq daemon status --json (or a dedicated command that starts the daemon), HTTP over the Unix socket or the loopback port with the Squads-Client header, conditional GETs on ETag for refresh, If-Match on writes, a TS client generated from /v1/openapi.json shared with the web front, schema/vocabulary refusals and 503 handled by rediscovery, and the sq --json path kept as the fallback when the daemon is off. Done once the DTOs are frozen.
<!-- sq:discussion:end -->
