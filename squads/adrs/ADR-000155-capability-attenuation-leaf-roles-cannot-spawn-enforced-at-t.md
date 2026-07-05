---
id: ADR-155
sequence_id: 155
type: decision
title: 'Capability attenuation: leaf roles cannot spawn; enforced at the backend'
status: Accepted
parent: EPIC-121
author: architect
priority: high
refs:
- FEAT-122
- BUG-152:fixes
description: Spawn authority reserved to manager+tech-lead via per-role tool lists;
  identity-aware profiles gated on FEAT-000125
created_at: '2026-06-21T21:40:15Z'
updated_at: '2026-06-22T09:58:26Z'
modified_session: verify-sess-001
---
<!-- sq:body -->
## Status

Proposed — parent context EPIC-121; governs FEAT-122; resolves BUG-152.

## Context

squads roles are **prose constraints**: a role's skill file describes what the role *should* do,
but every squads-managed agent session boots with the same full toolset regardless of role. A
developer spawned to write Python holds the same spawn authority as the manager coordinating the
team. Role limits are advisory, not structural.

This flat-capability model caused a concrete incident. **BUG-152** (motivating incident): a
`python-dev` subagent spawned by the manager, instead of doing its task, re-delegated to another
`python-dev` subagent ("big task, better call a subagent"); the child inherited the identical
scope + toolset and repeated the decision, cascading ~6 levels deep with no forward progress. The
2026-06-15 self-review (EPIC-121) was the same class of failure on a different axis: a session
held authority its role should not exercise.

There are two distinct failure modes here, and conflating them has held up the slice:

- **Capability** — a leaf specialist *carries* a tool it should not (the Agent/Task spawn tool).
  This is BUG-152. It needs no verified identity: the constraint binds to the agent **type** at
  launch, not to a self-declared slug at sq-time.
- **Identity / attribution** — a session *claims* a privileged role it was not spawned as (the
  `--as reviewer` self-review), or we need to prove a review lineage was independent. This needs
  trustworthy identity and lineage, which **FEAT-125** owns.

Feasibility (confirmed against the Claude Code subagent contract and our backend): Claude Code
subagent definitions support a `tools:` allowlist and a `disallowedTools:` denylist in YAML
frontmatter; omitting `tools:` inherits all tools. The harness enforces a subagent's own tool
restrictions **when that subagent runs**, bound to the agent type the spawner names — so a leaf
whose definition denies `Agent` *structurally cannot* spawn, even if it lies about who it is. This
is real enforcement, not advice. The spawn tool was renamed `Task` → `Agent` in 2.1.63 (`Task`
still works as an alias).

By contrast, squads runs as a CLI **below** the spawn layer: it never sees the Task/Agent event,
so an sq-runtime check cannot observe or block a spawn. The enforcement boundary therefore cannot
live in sq.

## Decision

1. **Enforcement lives at the Claude Code backend, via per-role tool lists — not an sq-runtime
   check.** The capability boundary is expressed in the subagent definition the harness loads,
   bound to the agent **type** at spawn time. The seam:
   - add a capability field to `RoleDef` in `src/squads/_roles/_catalog.py` (e.g.
     `can_spawn: bool`, default `False`);
   - `generate_role_entry` in `src/squads/_backends/_claude_code/_backend.py` renders the agent
     pointer via `templates/claude/pointer_agent.md.j2`, which already emits the agent frontmatter;
   - emit `disallowedTools: Agent` from that template for non-spawner roles
     (`{% if not can_spawn %}disallowedTools: Agent{% endif %}`).

   sq stays the CLI; the backend owns the session contract. (A global `settings.json` deny rule is
   a possible belt-and-suspenders backstop, but per-role capability belongs in the agent
   definition, not in global settings.)

   **Boundary caveat.** This binds an agent launched **by type** (`Agent(slug)` / `claude
   --agent`). It does **not** govern an arbitrary main-thread session a human starts and then
   drives with `--as <role>` in prose — that path is governed by the operator's own session
   settings. For the BUG-152 cascade (manager spawns `python-dev` by type) this is exactly the
   right and sufficient boundary.

2. **First attenuation cut: "all tools minus Agent/Task."** Spawn authority is reserved to
   `manager` and `tech-lead` only (the orchestrating roles in the loop). Every other role — all
   `*-dev`, `reviewer`, `qa`, `architect`, `product-owner`, `tech-writer`, `devops` — is a **leaf**
   that cannot spawn. Concretely: `can_spawn = True` for `manager` and `tech-lead`, `False` for all
   others; non-spawners' rendered agent files deny `Agent`. This is the structural fix for
   BUG-152: a leaf that does not hold the tool cannot self-spawn, regardless of how it reasons
   about its task. It is independent of FEAT-125 and unblocks the bug immediately.

3. **Identity-aware capability profiles are gated on FEAT-125.** The richer per-role capability
   profile — lane enforcement ("a developer cannot mutate items outside its assigned lane"),
   separation-of-duties, and any check that must verify *who* an actor really is — requires
   trustworthy identity to enforce against, and is explicitly **out of this slice**. FEAT-125
   can, in 1.x, offer only **recorded-but-not-tamper-evident** lineage: there is no Claude Code
   surface that injects a platform session handle (`{session_id, parent_session_id}`) into a
   subagent's environment for sq to read, so the strongest feasible mechanism is a spawner-minted
   nonce the child echoes — readable and copyable, i.e. it moves the self-declaration problem one
   hop up the chain. Signed/cryptographic identity is **deferred until a platform capability
   exists**. Given the epic's threat model (accidental/uncontrolled autonomy, not malicious
   agents), recorded lineage is good enough for forensics, but it is not a foundation to build
   capability *enforcement* on — hence the gate.

## Consequences

- **Positive.** BUG-152's recursive-spawn cascade is closed structurally and immediately, with
  no identity work and no sq-runtime machinery. Role constraints on spawn authority become
  structural rather than advisory. The boundary is small, testable (assert a rendered dev agent
  file denies `Agent`), and visible via `sq role <slug> show`.
- **Scoping.** FEAT-122's leaf-no-spawn slice (its US2) ships on type-bound tool lists alone and
  does **not** depend on FEAT-125; its existing `depends-on FEAT-000125` ref is too strong for
  the whole feature and should be re-pointed at the narrower lane-enforcement slice (flagged to
  Catherine; not changed here per scope).
- **Negative / limits.** Enforcement does not cover human-driven `--as <role>` main-thread
  sessions, only type-launched subagents. Lane enforcement and separation-of-duties remain
  advisory until FEAT-125 lands a trustworthy identity primitive. The first cut is coarse
  ("minus spawn"); finer per-tool attenuation is left for the richer profile work.
- **Follow-ups.** `tech-lead`'s legitimate need to spawn a dev when breaking down a task is
  preserved (it keeps `can_spawn`). When/if a richer profile is built, it extends the same
  `RoleDef`→`pointer_agent.md.j2` seam rather than introducing an sq-side check.
<!-- sq:body:end -->

## Discussion

<!-- sq:discussion -->
- [2026-06-21T21:45:57Z] Pierre Chat:
  - Accepted. Proceed: build Slice A (leaf-no-spawn) first as a full loop, then Slice B.
- [2026-06-22T09:58:26Z] Catherine Manager:
  - Verification probe: confirming session lineage records on the reflog (Catherine).
<!-- sq:discussion:end -->
