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
description: 'The CLI as a client of a remote daemon: a per-squad remote address,
  authentication, and the same exit code and output as local mode, built on the daemon''s
  command endpoint'
subentities:
- local_id: US1
  title: Remote daemon refuses callers it cannot identify
  status: Todo
- local_id: US2
  title: 'Parity: where the squad lives never changes how I work'
  status: Todo
- local_id: US3
  title: Remote address set per squad; local is the default
  status: Todo
created_at: '2026-06-10T15:33:16Z'
updated_at: '2026-10-28T14:03:10Z'
---
<!-- sq:body -->
## Problem

The CLI answers only from the squad on the invoking machine. The daemon of
FEAT-1140 serves commands over one command endpoint on that machine, but `sq`
cannot be pointed at a daemon that runs somewhere else, and nothing yet says
who is allowed to talk to one. The natural endgame of this epic is a squads
server the CLI itself is a client of, not just a browser.

## Value

- **One tool, two places.** Operators and agents keep their muscle memory and 
scripts: the same `sq` grammar works against the local squad or a remote one. 
Where the squad lives is configuration, not a different tool.
- **Full parity is the promise.** A command gives the same exit code, stdout 
and stderr remotely as locally, `--json` included. A remote-but-lesser mode 
would fork user behaviour and documentation.
- **Only the right people get in.** A remote squad is reachable by the people 
who are meant to reach it, and by nobody else.

## Scope

This feature builds on the command endpoint of FEAT-1140, which carries every
command and returns the CLI's own output. No second service interface and no
per-command endpoints are built here.

- **Remote address setting**: a per-squad setting names the remote daemon the 
CLI talks to. With no setting, a squad behaves exactly as it does today. An 
unreachable or refusing server gives a clean, actionable error, never a stack 
trace.
- **Authentication**: the remote daemon identifies who is calling and refuses 
the rest; credentials are configured on the client without being committed with
the squad. The actor an `--as` names over the wire is part of this decision.
- **The `.claude/` pointer gap**: agent pointer files and managed skills are 
generated on the machine that holds the squad. Remote mode says what an agent 
on another machine reads and how those files reach it.
- Design questions for the ADR: client and server version skew; what 
local-only concepts (the `-C` directory, `repair`) mean for a remote squad.

## Acceptance

- With the remote address set, commands run against the remote daemon through 
the command endpoint, and their outputs and exit codes match local mode.
- A squad with no remote address set behaves exactly as today.
- A caller without valid credentials is refused, and the refusal tells the 
person what to fix.
- Connection and authentication failures produce clean, actionable errors.
- An agent working against a remote squad finds its pointer files and managed 
skills.
<!-- sq:body:end -->

## User Stories

_Add with `sq feature 33 add-story "As a <role>, I want … so that …"`; track with `sq feature 33 story <n> update --status <Status>`._

<!-- sq:stories -->

<!-- sq:story:US1 -->
### US1 — Remote daemon refuses callers it cannot identify

<!-- sq:story:US1:body -->
As a squad owner, I want the remote daemon to refuse callers it cannot identify,
so that only the people meant to reach the squad do.
<!-- sq:story:US1:body:end -->

#### Discussion

<!-- sq:story:US1:discussion -->
<!-- sq:story:US1:discussion:end -->
<!-- sq:story:US1:end -->

<!-- sq:story:US2 -->
### US2 — Parity: where the squad lives never changes how I work

<!-- sq:story:US2:body -->
As an operator or agent on a remote squad, I want every command and flag to 
give the same exit code, stdout and stderr as in local mode, so that where the 
squad lives never changes how I work.
<!-- sq:story:US2:body:end -->

#### Discussion

<!-- sq:story:US2:discussion -->
<!-- sq:story:US2:discussion:end -->
<!-- sq:story:US2:end -->

<!-- sq:story:US3 -->
### US3 — Remote address set per squad; local is the default

<!-- sq:story:US3:body -->
As a squad owner, I want the remote daemon's address set per squad, with local 
mode as the default, so that remote is an explicit choice and existing squads 
are untouched.
<!-- sq:story:US3:body:end -->

#### Discussion

<!-- sq:story:US3:discussion -->
<!-- sq:story:US3:discussion:end -->
<!-- sq:story:US3:end -->
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
<!-- sq:discussion:end -->
