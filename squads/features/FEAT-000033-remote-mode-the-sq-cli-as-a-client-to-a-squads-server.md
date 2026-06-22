---
id: FEAT-000033
sequence_id: 33
type: feature
title: 'Remote mode: the sq CLI as a client to a squads server'
status: Draft
parent: EPIC-000029
author: product-owner
priority: medium
refs:
- FEAT-000015
- FEAT-000013
description: 'A mode switch in .squads.toml (offline default / remote): in remote
  mode every command calls remote endpoints with full feature-and-flag parity, through
  a Protocol-typed service interface the CLI depends on'
subentities:
- local_id: US1
  title: CLI decoupled from concrete Service via Python Protocols
  status: Todo
- local_id: US2
  title: 'Full offline/remote parity: transport never changes how I work'
  status: Todo
- local_id: US3
  title: Remote mode opt-in via .squads.toml; offline is the default
  status: Todo
created_at: '2026-06-10T15:33:16Z'
updated_at: '2026-06-23T09:58:01Z'
---
<!-- sq:body -->
## Problem

The CLI is welded to the local service: every command imports the concrete `Service`, which
reads and writes the squad on the invoking machine. There is no seam to point `sq` at a squad
that lives elsewhere — yet that's the natural endgame of this epic: a squads server exists, so
the CLI itself should be able to be its client, not just a browser.

## Value

- **One tool, two transports.** Operators and agents keep their muscle memory and scripts: the
  same `sq` grammar works against the local files (offline, default) or a remote squad — the mode
  is configuration, not a different tool.
- **The decoupling pays for itself immediately**, even before any server exists: a CLI that
  depends on a service *interface* instead of a concrete class is more testable and keeps the
  layering honest (`_cli → protocol ← implementations`).
- **Full parity is the promise.** Remote mode is not a subset: every command, every flag of the
  offline CLI must have a matching remote endpoint. A "remote-but-lesser" mode would fork user
  behaviour and documentation.

## Scope

- **Service interface as Python Protocols** (structural typing): the CLI types against the
  protocol(s), never the concrete service. Granularity per design — likely one protocol per
  concern, mirroring today's mixin split (items, collab, sub-entities, refs, roster,
  maintenance), composed into one `ServiceProtocol`.
- **`LocalService` keeps the mixin approach** — today's `Service` composition stays as-is and
  conforms to the protocols structurally (pyright-verified); the existing test suite stays green,
  untouched.
- **`RemoteService`**: a second implementation of the same protocols that calls HTTP endpoints.
  The server side (the endpoints themselves) is this epic's other features; this feature owns the
  client and the parity requirement: the CLI test matrix runs against both implementations and
  must pass identically (outputs, exit codes, `--json` bytes).
- **Mode in `.squads.toml`**: `offline` (default) or `remote` + the server URL; per-squad.
  Unreachable/unauthenticated server → a clean `SquadsError`, never a stack trace.
- Design questions for the ADR: actor identity over the wire (who is `--as` when remote — ties
  into this epic's auth caveat); client/server version-skew policy (the wire shapes join the
  FEAT-000013/FEAT-000015 contract conversation); what offline-only concepts (e.g. `--dir`,
  `repair`) mean in remote mode — full parity may mean "remote-executed", not "impossible".

## Acceptance

- A protocol-typed service interface exists; `_cli` imports only the protocol; `LocalService`
  (mixin-composed, unchanged behaviour) conforms — pyright strict proves it; existing tests green.
- With `mode = "remote"` in `.squads.toml`, every command and flag routes to remote endpoints; the
  full CLI test matrix passes against a reference server with outputs identical to offline mode.
- Offline remains the default; a squad with no mode setting behaves exactly as today.
- Connection and auth failures produce clean, actionable errors.
<!-- sq:body:end -->

## User Stories

_Add with `sq feature 33 add-story "As a <role>, I want … so that …"`; track with `sq feature 33 story <n> update --status <Status>`._

<!-- sq:summary -->
| Story | Status | Assignee | Title |
| --- | --- | --- | --- |
| US1 | Todo |  | CLI decoupled from concrete Service via Python Protocols |
| US2 | Todo |  | Full offline/remote parity: transport never changes how I work |
| US3 | Todo |  | Remote mode opt-in via .squads.toml; offline is the default |
<!-- sq:summary:end -->

<!-- sq:stories -->

<!-- sq:story:US1 -->
### US1 — CLI decoupled from concrete Service via Python Protocols

<!-- sq:story:US1:head -->
**Status:** ⚪ Todo
<!-- sq:story:US1:head:end -->

<!-- sq:story:US1:body -->
As a maintainer of the codebase, I want the CLI decoupled from the concrete Service behind Python Protocols, so that plugging a different service implementation (remote or otherwise) is possible without touching the commands.
<!-- sq:story:US1:body:end -->

#### Discussion

<!-- sq:story:US1:discussion -->
<!-- sq:story:US1:discussion:end -->
<!-- sq:story:US1:end -->

<!-- sq:story:US2 -->
### US2 — Full offline/remote parity: transport never changes how I work

<!-- sq:story:US2:head -->
**Status:** ⚪ Todo
<!-- sq:story:US2:head:end -->

<!-- sq:story:US2:body -->
As an operator or agent on a remote squad, I want every offline command and flag to work identically in remote mode, so that the transport never changes how I work.
<!-- sq:story:US2:body:end -->

#### Discussion

<!-- sq:story:US2:discussion -->
<!-- sq:story:US2:discussion:end -->
<!-- sq:story:US2:end -->

<!-- sq:story:US3 -->
### US3 — Remote mode opt-in via .squads.toml; offline is the default

<!-- sq:story:US3:head -->
**Status:** ⚪ Todo
<!-- sq:story:US3:head:end -->

<!-- sq:story:US3:body -->
As a squad owner, I want the mode set in .squads.toml with offline as the default, so that remote is an explicit per-squad choice and existing squads are untouched.
<!-- sq:story:US3:body:end -->

#### Discussion

<!-- sq:story:US3:discussion -->
<!-- sq:story:US3:discussion:end -->
<!-- sq:story:US3:end -->
<!-- sq:stories:end -->

## Discussion

<!-- sq:discussion -->
- [2026-06-14T20:32:56Z] Catherine Manager:
  - Remote-mode gap (flagged by Pierre, 2026-06-14): the Claude Code backend writes thin pointer files in .claude/ that use Claude Code's @-include to load the real role/skill body from local disk — .claude/agents/<role>.md → @squads/agents/roles/ROLE-…md (pointer_agent.md.j2:22) and .claude/skills/<name>/SKILL.md → @squads/agents/skills/<name>.md (pointer_skill.md.j2:8). In remote mode squads/agents/… won't be on the operator's disk, but subagents still boot locally, so those includes dangle.
  - Resolution lives here, not in 1.0: this is purely a backend concern behind the AgentBackend ABC, and .claude/ is non-contract (ADR-000075). When remote mode lands, sq sync should materialize SELF-CONTAINED pointers — inline the role/skill body fetched from the server — instead of @-referencing local paths. No frozen surface is affected. @architect to own the approach (likely a follow-on ADR) when FEAT-000033 starts.
<!-- sq:discussion:end -->
