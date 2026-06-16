---
id: FEAT-000122
sequence_id: 122
type: feature
title: Per-role capability attenuation
status: Draft
parent: EPIC-000121
author: product-owner
priority: low
refs:
- FEAT-000125:depends-on
subentities:
- local_id: US1
  title: Declared capability profile per worker role
  status: Todo
- local_id: US2
  title: Reviewer role structurally blocked from spawning agents
  status: Todo
created_at: '2026-06-15T11:56:09Z'
updated_at: '2026-06-16T09:52:10Z'
---
<!-- sq:body -->
## Problem

On 2026-06-15, an architect subagent spawned a review and applied code fixes — autonomously and
without authorisation — because nothing in squads (or in the Claude Code layer) limited what it
could do. The `sq-architect` skill describes what the role _should_ do; the role still held every
tool, including the ability to spawn sub-agents. The incident (see EPIC-000121) would have been
impossible if the architect session literally could not invoke the Task/Agent tool.

Today, roles are **prose constraints** — a skill file the model is asked to follow. Capability
is flat: every squads-managed agent session gets the same full toolset regardless of its role.
A developer spawned to write Python has the same spawn authority as the manager coordinating the
whole team.

## Value

If squads (or its backend) can express a per-role **capability profile** — which tools and
authorities each role is permitted to use — then a reviewer literally cannot spawn implementation
agents, a developer cannot retype or delete items outside its lane, and the manager is the only
role that legitimately escalates. Role constraints become structural, not advisory.

## Scope (exploratory — not a design commitment)

- Define what a "capability profile" is in the squads model: a structured declaration that maps a
  role slug to the set of tool categories or specific tools it is permitted to invoke.
- Identify where enforcement sits. squads runs as a CLI; it cannot restrict Claude Code tool access
  directly. The profile may be expressed as backend configuration (e.g. a Claude Code system prompt
  constraint or a reduced tool list at subagent spawn time) rather than a squads-side runtime check.
- Consider: should `sq` validate a registered agent's toolset at spawn time, or only audit after
  the fact via reflog?
- Tie-in: backend/subagent_type definitions already map roles to agent types
  (`_backends/_claude_code/`). A capability profile could extend that mapping.

## Acceptance (draft — subject to triage)

- A squads-managed role declaration can express a capability profile (which tool categories it
  holds or is denied).
- The backend respects this profile when it constructs the agent session (e.g. reduced allowed
  tools for spawned sub-agents).
- A reviewer-role session cannot invoke the Agent/Task tool (spawn sub-agents).
- A developer-role session cannot invoke squad-management operations outside its assigned item.
- The capability profile is visible via `sq role <slug> show`.

## Open questions

- Can Claude Code actually enforce a reduced tool list on a spawned sub-agent? If not, where does
  the enforcement boundary sit — at the model (system prompt), the API, or is this impossible
  without platform changes?
- Is "all tools minus spawn" the right first attenuation, or is there a coarser/finer cut that
  makes more practical sense?
- How do we handle roles that legitimately need spawn authority some of the time (e.g. a tech lead
  breaking a task into subtasks by spawning a dev)?
- Does capability attenuation require FEAT-000125 (real identity) to be meaningful, or is it
  independently implementable?
<!-- sq:body:end -->

## User Stories

_Add with `sq feature 122 add-story "As a <role>, I want … so that …"`; track with `sq feature 122 story <n> update --status <Status>`._

<!-- sq:summary -->
| Story | Status | Assignee | Title |
| --- | --- | --- | --- |
| US1 | Todo |  | Declared capability profile per worker role |
| US2 | Todo |  | Reviewer role structurally blocked from spawning agents |
<!-- sq:summary:end -->

<!-- sq:stories -->

<!-- sq:story:US1 -->
### US1 — Declared capability profile per worker role

<!-- sq:story:US1:head -->
**Status:** ⚪ Todo
<!-- sq:story:US1:head:end -->

<!-- sq:story:US1:body -->
As a squad manager, I want each worker role to have a declared capability profile, so that I can verify a spawned agent cannot exceed its remit (e.g. spawn sub-agents, modify items outside its lane).

**Acceptance:** a role declaration in squads (or its backend config) carries a structured capability profile listing permitted tool categories; the profile is visible via `sq role <slug> show`; the backend respects the profile when constructing the agent session.
<!-- sq:story:US1:body:end -->

#### Discussion

<!-- sq:story:US1:discussion -->
<!-- sq:story:US1:discussion:end -->
<!-- sq:story:US1:end -->

<!-- sq:story:US2 -->
### US2 — Reviewer role structurally blocked from spawning agents

<!-- sq:story:US2:head -->
**Status:** ⚪ Todo
<!-- sq:story:US2:head:end -->

<!-- sq:story:US2:body -->
As a reviewer-role agent, I want the system to prevent me from invoking the Agent/Task spawn tool, so that I cannot accidentally (or autonomously) expand my own work scope.

**Acceptance:** a reviewer session launched via squads cannot invoke the Agent or Task spawn tool; attempting to do so produces a clear, immediate error (not a silent no-op); the constraint is enforced at the backend/session level, not merely advised in the skill file.
<!-- sq:story:US2:body:end -->

#### Discussion

<!-- sq:story:US2:discussion -->
<!-- sq:story:US2:discussion:end -->
<!-- sq:story:US2:end -->
<!-- sq:stories:end -->

## Discussion

<!-- sq:discussion -->
<!-- sq:discussion:end -->
