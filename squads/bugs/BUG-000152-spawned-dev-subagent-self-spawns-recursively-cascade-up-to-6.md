---
id: BUG-000152
sequence_id: 152
type: bug
title: Spawned dev subagent self-spawns recursively (cascade up to 6 levels)
status: Open
author: op-pierre
assignee: qa
priority: high
refs:
- FEAT-000122
description: A spawned specialist re-delegates instead of working, cascading same-role
  subagents many levels deep
created_at: '2026-06-17T20:08:34Z'
updated_at: '2026-06-17T20:12:08Z'
---
<!-- sq:body -->
**Observed.** Elias (python-dev) was spawned by the manager with a large implementation task. Instead of doing the work, he spawned another python-dev subagent, reasoning roughly "this is a big task, better call a subagent." The child inherited the same scope and toolset and did exactly the same thing — the spawn cascaded about 6 levels deep before any real work happened.

**Repro.** 1) As manager, spawn a developer (e.g. python-dev) as a subagent with a broad/large task and the default all-tools loadout (which includes the Agent/Task spawn tool). 2) Observe the agent's reasoning: a "big" task is read as a cue to delegate rather than to do. 3) The agent spawns a same-role subagent; the child inherits the identical scope + tools and repeats the decision. Recursion continues with no natural floor.

**Expected.** A spawned specialist does the work itself. Delegation-by-spawning is the *manager's* (or a coordinating tech-lead's) job in the orchestration loop — a leaf specialist must not spawn further same-role subagents, and spawn depth should be bounded regardless.

**Actual.** Unbounded recursive self-spawning (~6 levels deep), burning tokens and wall-clock while producing no forward progress on the task.

**Root cause / fix directions (for triage).** Spawned specialists carry the full toolset including Agent/Task, and nothing in their role/skill text tells them that *when spawned as a subagent they do the work and do not re-delegate*. Candidate fixes, not mutually exclusive: (a) add an explicit 'you are a leaf — do the work, don't spawn' instruction to the role/skill definitions a subagent boots with; (b) withhold the Agent/Task tool from leaf specialist agent types so only orchestrators can spawn; (c) enforce a spawn-depth bound in the harness as a backstop. Relates to the existing orchestration-loop guidance ('the spawn is the handoff') and the team's constrain-subagent-spawning principle.
<!-- sq:body:end -->

## Discussion

<!-- sq:discussion -->
- [2026-06-17T20:09:25Z] Pierre Chat:
  - Filing this from a real incident I hit: Elias was given a big task and started spawning himself in cascade, up to ~6 levels deep, each time saying it was a big task so better to call a subagent. I want this prevented.
- [2026-06-17T20:12:08Z] Pierre Chat:
  - Decision: fix this the structural way — option (2), per-role capability attenuation (withhold the spawn tool from leaf specialists). Tracked as FEAT-000122, which we'll pick up very soon. Option (1) instruction-tightening is optional interim mitigation.
<!-- sq:discussion:end -->
