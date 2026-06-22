---
id: BUG-000152
sequence_id: 152
type: bug
title: Spawned dev subagent self-spawns recursively (cascade up to 6 levels)
status: Verified
author: op-pierre
assignee: qa
priority: high
refs:
- FEAT-000122
description: A spawned specialist re-delegates instead of working, cascading same-role
  subagents many levels deep
created_at: '2026-06-17T20:08:34Z'
updated_at: '2026-06-21T22:27:41Z'
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
- [2026-06-21T22:27:41Z] Mara Tester:
  - QA verification complete. BUG-000152 is closed — the recursive self-spawn mechanism is no longer possible for leaf specialist roles.
  - **Verification evidence:**
  - **1. Full test suite:** 862 passed, 1 skipped. All 19 tests in tests/test_can_spawn.py green, covering three seams: RoleDef.can_spawn catalog field values, rendered pointer frontmatter (YAML-parsed), and sq role show surfacing.
  - **2. End-to-end render (sq init --roles all on a fresh squad):** All 8 generated .claude/agents/*.md files parse as valid YAML. Leaf roles (architect, devops, qa, reviewer, product-owner, tech-writer) all carry disallowedTools: Agent. Orchestrators (manager, tech-lead) do NOT — they retain spawn authority.
  - **3. dev_role() factory:** python-dev, dotnet-dev, go-dev, rust-dev, typescript-dev all produce can_spawn=False. A rendered python-dev pointer would carry disallowedTools: Agent.
  - **4. sq role show:** All 8 roles report the correct can spawn: yes/no value — manager and tech-lead report yes, all 6 leaves report no.
  - **Mechanism closed by TASK-000156 + ADR-000155:** The disallowedTools: Agent entry in the agent frontmatter is bound at the agent TYPE at spawn time — before the child session runs. A leaf specialist cannot invoke the Agent tool regardless of what it reasons or claims; the tool is simply not available in the session. This closes the BUG-000152 path.
  - **Scope boundary (not covered by this fix):** A human running a main-thread session --as a leaf role slug in prose is out of scope — that is the identity/Slice B concern (FEAT-000125). The boundary is explicit in ADR-000155 and TASK-000156.
  - Refs: TASK-000156 (fix), ADR-000155 (decision).
<!-- sq:discussion:end -->
