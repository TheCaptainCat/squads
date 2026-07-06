---
id: FEAT-319
sequence_id: 319
type: feature
title: MCP connector — drive a hosted squad from the Claude apps
status: Draft
parent: EPIC-29
author: product-owner
refs:
- FEAT-33
subentities:
- local_id: US1
  title: As an operator, I can connect my hosted squad to a Claude app as a remote
    MCP connector via OAuth
  status: Todo
- local_id: US2
  title: As an app, I get a small curated set of MCP tools for core squads operations,
    not every CLI verb
  status: Todo
- local_id: US3
  title: As an operator, MCP access is authenticated and scoped to my squad
  status: Todo
- local_id: US4
  title: As a maintainer, the MCP endpoint is a third frontend over the service layer,
    matching CLI behaviour
  status: Todo
created_at: '2026-07-07T08:01:07Z'
updated_at: '2026-07-07T08:01:50Z'
---
<!-- sq:body -->
# MCP connector for a hosted squad

Expose a hosted squad as a **remote MCP connector** so the Claude apps (claude.ai, Desktop, mobile)
can drive it — search, read, create, transition, comment — as an authenticated connector, the same
way they connect to other remote services today.

## Positioning

This is deliberately scoped to the **hosted** case:

- **Local squad → the CLI.** `sq` is the daily driver on your own machine. No MCP, no server.
- **Hosted squad → MCP.** The webapp server exposes an OAuth'd `/mcp` endpoint that the Claude apps
  connect to as a connector.

MCP is the mechanism *because* the Claude apps reach remote services through remote MCP connectors
(with OAuth), not through generic REST — so a hosted squad that wants to be first-class inside the
apps has to speak MCP.

## Where it lives

MCP is **not** a standalone service and **not** its own epic — it's an **endpoint of the webapp
server** (this epic). Architecturally it's a *third frontend over `_services`*, alongside the CLI and
the web UI: three faces (CLI · web UI · MCP connector), one service core, no business logic
duplicated. The server the web view runs on already brings the HTTP surface, hosting, and auth that
the MCP endpoint needs.

## Dependency & scope

This rides on the hosted webapp server — it can't start until that server exists (see the remote-mode
work in this epic). No ADR yet: the endpoint's mechanics (transport, OAuth provider, session model)
are downstream of the webapp's own architecture, which isn't designed. This feature captures intent
and the positioning decision; the mechanics land when the server work begins.

## Shape (intent, not spec)

- An `/mcp` route on the webapp server speaking remote MCP over HTTP.
- **OAuth** authentication; the app completes the standard authorize/callback handshake.
- A **curated, small tool surface** — the core squads operations (search, show, list, create,
  transition, comment) — deliberately *not* a 1:1 mapping of every CLI verb, so the connector stays
  light in the client's context.
<!-- sq:body:end -->

## User Stories

_Add with `sq feature 319 add-story "As a <role>, I want … so that …"`; track with `sq feature 319 story <n> update --status <Status>`._

<!-- sq:summary -->
| Story | Status | Assignee | Title |
| --- | --- | --- | --- |
| US1 | Todo |  | As an operator, I can connect my hosted squad to a Claude app as a remote MCP connector via OAuth |
| US2 | Todo |  | As an app, I get a small curated set of MCP tools for core squads operations, not every CLI verb |
| US3 | Todo |  | As an operator, MCP access is authenticated and scoped to my squad |
| US4 | Todo |  | As a maintainer, the MCP endpoint is a third frontend over the service layer, matching CLI behaviour |
<!-- sq:summary:end -->

<!-- sq:stories -->

<!-- sq:story:US1 -->
### US1 — As an operator, I can connect my hosted squad to a Claude app as a remote MCP connector via OAuth

<!-- sq:story:US1:head -->
**Status:** ⚪ Todo
<!-- sq:story:US1:head:end -->

<!-- sq:story:US1:body -->
As an operator, I want to connect my hosted squad to a Claude app as a remote MCP connector via OAuth so I can drive it from the app.

**Acceptance**
- The webapp server exposes an `/mcp` route speaking remote MCP over HTTP.
- The connector authenticates via OAuth (standard authorize/callback handshake completed by the app).
- Once connected, the app can list the squad's exposed MCP tools.
<!-- sq:story:US1:body:end -->

#### Discussion

<!-- sq:story:US1:discussion -->
<!-- sq:story:US1:discussion:end -->
<!-- sq:story:US1:end -->

<!-- sq:story:US2 -->
### US2 — As an app, I get a small curated set of MCP tools for core squads operations, not every CLI verb

<!-- sq:story:US2:head -->
**Status:** ⚪ Todo
<!-- sq:story:US2:head:end -->

<!-- sq:story:US2:body -->
As an app, I want a small curated set of MCP tools for the core squads operations so the connector stays light in my context.

**Acceptance**
- Tools cover the essentials: search, show/get an item, list, create, transition/update status, comment.
- The surface is intentionally bounded — documented what is exposed and what is deliberately not — rather than a 1:1 mapping of every CLI verb.
- Tool schemas are typed (structured args and results), not free-text.
<!-- sq:story:US2:body:end -->

#### Discussion

<!-- sq:story:US2:discussion -->
<!-- sq:story:US2:discussion:end -->
<!-- sq:story:US2:end -->

<!-- sq:story:US3 -->
### US3 — As an operator, MCP access is authenticated and scoped to my squad

<!-- sq:story:US3:head -->
**Status:** ⚪ Todo
<!-- sq:story:US3:head:end -->

<!-- sq:story:US3:body -->
As an operator, I want MCP access authenticated and scoped to my squad so a connector only sees what I am authorized for.

**Acceptance**
- Requests without a valid OAuth token are rejected.
- A token is scoped to a specific hosted squad / operator identity.
- Ties into the control-plane / permissions model if and when that exists.
<!-- sq:story:US3:body:end -->

#### Discussion

<!-- sq:story:US3:discussion -->
<!-- sq:story:US3:discussion:end -->
<!-- sq:story:US3:end -->

<!-- sq:story:US4 -->
### US4 — As a maintainer, the MCP endpoint is a third frontend over the service layer, matching CLI behaviour

<!-- sq:story:US4:head -->
**Status:** ⚪ Todo
<!-- sq:story:US4:head:end -->

<!-- sq:story:US4:body -->
As a maintainer, I want the MCP endpoint to be a third frontend over `_services` so its behaviour matches the CLI and web UI with no duplicated logic.

**Acceptance**
- MCP handlers call the shared service layer; no business logic is reimplemented in the endpoint.
- For a given operation, validation and invariants match the CLI path.
<!-- sq:story:US4:body:end -->

#### Discussion

<!-- sq:story:US4:discussion -->
<!-- sq:story:US4:discussion:end -->
<!-- sq:story:US4:end -->
<!-- sq:stories:end -->

## Discussion

<!-- sq:discussion -->
<!-- sq:discussion:end -->
