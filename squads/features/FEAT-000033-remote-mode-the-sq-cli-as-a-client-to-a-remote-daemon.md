---
id: FEAT-33
sequence_id: 33
type: feature
title: 'Remote mode: the sq CLI as a client to a remote daemon'
status: Draft
parent: EPIC-29
author: product-owner
priority: medium
refs:
- FEAT-15
- FEAT-13
- FEAT-1140:depends-on
- ADR-1225
description: 'The CLI and terminal UI as clients of a squad hosted on another machine:
  a client-side address, authentication, no local fall back, built on the daemon''s
  routes'
subentities:
- local_id: US1
  title: Hosted squad refuses callers it cannot identify
  status: Todo
- local_id: US2
  title: 'Parity: where the squad lives never changes how I work'
  status: Todo
- local_id: US3
  title: Hosted squad address set on the client; local is the default
  status: Todo
- local_id: US4
  title: Clear errors when the hosted squad is restarting or unreachable
  status: Todo
- local_id: US5
  title: A checkout out of line with the hosted squad is refused
  status: Todo
- local_id: US6
  title: Agents on another machine load their persona from the squad
  status: Todo
created_at: '2026-06-10T15:33:16Z'
updated_at: '2026-10-28T22:06:04Z'
---
<!-- sq:body -->
## Problem

The CLI answers only from a squad on the invoking machine, or from the local daemon of FEAT-1140 that serves that squad. `sq` cannot be pointed at a squad hosted on another machine, nothing says who is allowed to talk to one, and a daemon listens only on loopback. The natural endgame of this epic is a squads server that the CLI, the terminal UI and the browser are all clients of.

## Value

- **One tool, two places.** Operators and agents keep their muscle memory and scripts: the same `sq` grammar works against the local squad or a hosted one. Where the squad lives is configuration, not a different tool.
- **Parity is the promise.** A command gives the same output and exit code against a hosted squad as locally, `--json` included, because the CLI parses and renders in the user's own process either way. The one visible difference: paths in messages are spelled from the squad's root, since the server has no view of the client's directories.
- **Only the right people get in.** A hosted squad is reachable by the people who are meant to reach it, and by nobody else.

## Scope

This feature builds on FEAT-1140: the daemon's resource routes, and the HTTP client the CLI and the terminal UI already use for a local daemon. Endpoint resolution is the seam: it gains a source ahead of the local daemon, an address the client's own settings name, and returns an endpoint with no local mode. No second client or service interface is built.

- **Remote address setting**: a setting on the client names the hosted squad a checkout talks to, and is not committed with the squad. With no setting, a squad behaves exactly as it does with FEAT-1140.
- **Listening beyond the machine**: a daemon that serves a hosted squad accepts connections from other machines, which today's loopback-only listeners never do.
- **Authentication**: the server identifies who is calling and refuses the rest; credentials are configured on the client without being committed. It builds on the authentication mode MILE-868 decides for the browser port, and it turns the actor a request declares, today an unverified claim, into an identified one.
- **No fall back for a hosted squad**: there is no local squad to answer instead. A server that is restarting gets the call once more, then a clear error; an unreachable server is a clear error; nothing runs locally. The terminal UI follows the same rule.
- **Workflow configuration**: a checkout must carry the same workflow vocabulary and overrides as the hosted squad, and FEAT-1140's vocabulary and schema checks refuse a stale checkout before anything runs. A way to synchronise that configuration between a checkout and the hosted squad is planned here, once remote mode exists (op-pierre, 2026-10-28).
- **The `.claude/` pointer gap**: agent pointer files and managed skills are generated on the machine that holds the squad. An agent on another machine loads its persona by running `sq role <slug> show`, which the CLI answers from the hosted squad (op-pierre, 2026-07-10), not through a local file include.

Settled by FEAT-1140 and its decisions, so not open here: client and server version skew (different schema versions refuse each other), and what corpus-wide operations mean remotely (they run on the server through their routes; `init` and `adopt` stay local).

## Acceptance

- With the remote address set, commands run against the hosted squad, and their output and exit codes match local mode, apart from how paths in messages are spelled.
- A squad with no remote address set behaves exactly as with FEAT-1140.
- A caller without valid credentials is refused, and the refusal tells the person what to fix.
- A restarting or unreachable server, and a failed authentication, produce clean, actionable errors, and nothing runs locally.
- A checkout whose workflow configuration or schema differs from the hosted squad's is refused before anything runs, with a message naming the remedy.
- An agent working against a hosted squad loads its persona and its managed skills.
<!-- sq:body:end -->

## User Stories

_Add with `sq feature 33 add-story "As a <role>, I want … so that …"`; track with `sq feature 33 story <n> update --status <Status>`._

<!-- sq:stories -->

<!-- sq:story:US1 -->
### US1 — Hosted squad refuses callers it cannot identify

<!-- sq:story:US1:body -->
As a squad owner, I want the server of a hosted squad to refuse callers it cannot identify, so that only the people meant to reach the squad do.

Done when: every request to a hosted squad carries credentials configured on the client and never committed with the squad; a request without valid ones is refused before anything runs, and the CLI's message says what to fix; the actor recorded on a write is the identified caller, not a claim; the mechanism is the authentication mode decided for the browser port (MILE-868), applied to every listener that reaches beyond the machine.
<!-- sq:story:US1:body:end -->

#### Discussion

<!-- sq:story:US1:discussion -->
<!-- sq:story:US1:discussion:end -->
<!-- sq:story:US1:end -->

<!-- sq:story:US2 -->
### US2 — Parity: where the squad lives never changes how I work

<!-- sq:story:US2:body -->
As an operator or agent on a hosted squad, I want every command and flag to give the same output and exit code as in local mode, so that where the squad lives never changes how I work.

Done when: every command that runs against a local daemon runs against a hosted squad with the same output and exit code, `--json` included; paths in messages are spelled from the squad's root; `init` and `adopt` stay local, and corpus-wide operations run on the server; the CLI's surface suite passes against a hosted squad.
<!-- sq:story:US2:body:end -->

#### Discussion

<!-- sq:story:US2:discussion -->
<!-- sq:story:US2:discussion:end -->
<!-- sq:story:US2:end -->

<!-- sq:story:US3 -->
### US3 — Hosted squad address set on the client; local is the default

<!-- sq:story:US3:body -->
As a squad owner, I want the hosted squad's address set on the client, with local mode as the default, so that remote is an explicit choice and existing squads are untouched.

Done when: a client setting, outside what the squad commits, names the hosted squad's address for a checkout; with it unset, the CLI behaves exactly as with FEAT-1140 (local daemon or local mode); with it set, no local daemon is started or consulted for that squad; the setting is documented beside the daemon settings.
<!-- sq:story:US3:body:end -->

#### Discussion

<!-- sq:story:US3:discussion -->
<!-- sq:story:US3:discussion:end -->
<!-- sq:story:US3:end -->

<!-- sq:story:US4 -->
### US4 — Clear errors when the hosted squad is restarting or unreachable

<!-- sq:story:US4:body -->
As an operator, I want a hosted squad that is restarting or unreachable to give me a clear error, so that I never wonder whether my command ran somewhere else.

Done when: a server that answers that it is restarting gets the call once more at the re-resolved address, and a second refusal fails with a message saying to re-run in a moment; a server that cannot be reached fails with a message naming the address and the cause; both exit 1 and nothing runs locally; the terminal UI shows the same errors and keeps its session open for a refresh.
<!-- sq:story:US4:body:end -->

#### Discussion

<!-- sq:story:US4:discussion -->
<!-- sq:story:US4:discussion:end -->
<!-- sq:story:US4:end -->

<!-- sq:story:US5 -->
### US5 — A checkout out of line with the hosted squad is refused

<!-- sq:story:US5:body -->
As an operator, I want a checkout that does not match the hosted squad's configuration to be refused before anything runs, so that a command is never parsed with a vocabulary the squad does not hold.

Done when: a checkout whose workflow vocabulary differs from the hosted squad's is refused with a message naming the document that differs and saying to bring the checkout in line; a client at another schema version is refused with a message saying which side to upgrade; neither falls back; a way to synchronise the workflow configuration between a checkout and the hosted squad is designed once remote mode exists.
<!-- sq:story:US5:body:end -->

#### Discussion

<!-- sq:story:US5:discussion -->
<!-- sq:story:US5:discussion:end -->
<!-- sq:story:US5:end -->

<!-- sq:story:US6 -->
### US6 — Agents on another machine load their persona from the squad

<!-- sq:story:US6:body -->
As an agent on another machine than the squad's, I want to load my persona and managed skills from the hosted squad, so that I work the same way as an agent on the squad's own machine.

Done when: the agent files `sq sync` generates tell the agent to run `sq role <slug> show` to load its persona, rather than including a local file; managed skills reach an agent on a client machine the same way; the same generated files work against a local and a hosted squad.
<!-- sq:story:US6:body:end -->

#### Discussion

<!-- sq:story:US6:discussion -->
<!-- sq:story:US6:discussion:end -->
<!-- sq:story:US6:end -->
<!-- sq:stories:end -->

## Discussion

<!-- sq:discussion -->
- [2026-06-14T20:32:56Z] `manager` Catherine Manager:
  - Remote-mode gap (flagged by Pierre, 2026-06-14): the Claude Code backend writes thin pointer files in .claude/ that use Claude Code's @-include to load the real role/skill body from local disk — .claude/agents/<role>.md → @squads/agents/roles/ROLE-…md (pointer_agent.md.j2:22) and .claude/skills/<name>/SKILL.md → @squads/agents/skills/<name>.md (pointer_skill.md.j2:8). In remote mode squads/agents/… won't be on the operator's disk, but subagents still boot locally, so those includes dangle.
  - Resolution lives here, not in 1.0: this is purely a backend concern behind the AgentBackend ABC, and .claude/ is non-contract (ADR-75). When remote mode lands, sq sync should materialize SELF-CONTAINED pointers — inline the role/skill body fetched from the server — instead of @-referencing local paths. No frozen surface is affected. @architect to own the approach (likely a follow-on ADR) when FEAT-33 starts.
- [2026-07-10T09:35:54Z] `op-pierre` Pierre Chat:
  - Agent persona loading for remote mode: do NOT rely on the @file embed of the role in .claude/agents/<name>.md — @path is local-filesystem-only (and really a CLAUDE.md-only import), so it breaks when the squad data lives on a remote host. Instead, the generated agent file must instruct the agent that it MUST run `sq role <slug> show` to load its persona. The CLI resolves local-or-remote, so the same agent file works in both modes. (Verified against Claude Code: ! command-exec is not supported in subagent files, only in SKILL.md; so a plain 'run this command' instruction in the agent prompt — which the agent executes via its Bash tool — is the backend-agnostic path, and it already matches what CLAUDE.md's impersonation section tells agents to do.)
- [2026-10-25T17:38:53Z] `architect` Robert Architect:
  - ADR-1052 supersedes this feature's RemoteService and Protocol-typed service interface (op-pierre ruling, 2026-10-25): both CLI remote mode and the web client call one POST /v1/commands endpoint, so neither is built. The body still describes them; @product-owner please rescope it against ADR-1052 (the remote-squad case keeps its seam in the endpoint resolution).
- [2026-10-28T13:54:02Z] `product-owner` Nina Product:
  - @manager this body is superseded in part by ADR-1052 and FEAT-1140 (no Protocol interface, no RemoteService; the command endpoint is the seam). Needs the operator-approved rescope before the tech lead plans from it; FEAT-1140 records the boundary.
- [2026-10-28T14:02:37Z] `product-owner` Nina Product:
  - Rescoped per op-pierre's 2026-10-25 ruling: Protocol-typed RemoteService dropped; builds on the FEAT-1140 command endpoint (depends-on added). Keeps the remote address setting, authentication and the .claude/ pointer gap; stories US1-US3 reworded to match.
- [2026-10-28T14:03:10Z] `product-owner` Nina Product:
  - Title and summary reworded to match the rescoped body.
- [2026-10-28T21:31:30Z] `op-pierre` Pierre Chat:
  - 2026-10-28: once a real remote mode exists, plan a way to synchronise the specs (overrides and vocabulary) between the client's repository and the server. Until then the client must already carry the same ones, checked by the vocabulary hash of ADR-1225.
- [2026-10-28T22:06:04Z] `product-owner` Nina Product:
  - Re-read 2026-10-28 against ADR-1225 and op-pierre 1549816.
    - Body: builds on FEAT-1140's routes and HTTP client, with endpoint resolution as the seam; no fall back for a hosted squad (one retry on restart, clear error when unreachable, TUI included); a listener beyond loopback; auth built on MILE-868's mode; the checkout must match the squad's vocabulary, with spec sync planned here; the pointer gap resolved per op-pierre 2cd0509. Version skew and remote corpus-wide operations moved to "settled".
    - US1 and US3 retitled (hosted squad, client-side address); US1-US3 got Done-when bodies; new US4 restart/unreachable errors, US5 stale checkout refused, US6 agents load their persona. Summary updated; ADR-1225 linked.
<!-- sq:discussion:end -->
