---
id: FEAT-000122
sequence_id: 122
type: feature
title: Per-role capability attenuation
status: Done
parent: EPIC-000121
author: product-owner
priority: low
refs:
- FEAT-000125
subentities:
- local_id: US1
  title: Full structured capability profile per role (Slice B — gated on FEAT-000125)
  status: Done
- local_id: US2
  title: Leaf roles structurally blocked from spawning agents (Slice A — fixes BUG-000152)
  status: Done
created_at: '2026-06-15T11:56:09Z'
updated_at: '2026-06-22T13:49:32Z'
---
<!-- sq:body -->
## Lane-rules spec for Slice B (product-owner draft, 2026-06-22)

This section records the lane rules that Slice B must enforce.  It is the input
for the architect's enforcement-model ADR, authored and approved before any
build.

### Background: advisory posture

Slice B lane enforcement is **advisory** (per ADR-000158 and the FEAT-000125
reframe).  The actor identity available at sq-invocation time is a
self-declared `--as` slug plus an optional environment-sourced session nonce
that is readable and copyable.  Enforcement can catch the honest mistake — an
agent acting outside its lane by accident — but it cannot stop a deliberate
forger.  All checks in this slice MUST be framed and documented as
"warn-and-proceed" and MUST NOT claim enforcement-grade or tamper-evident
semantics.

### 1. Create lanes

Derived from `_interactions.py` (the team playbook) and the CLAUDE.md team
workflow section.  For each role, the item types it is **in-lane to author**
via `sq create`:

| Role | In-lane create types | Notes |
|---|---|---|
| `product-owner` | `feature`, `epic` | Epics and features are the PO's primary deliverable.  Story add-on commands (add-story) are an extension of feature authorship. |
| `tech-lead` | `task` | Tasks only; a task's parent must be a feature (existing `sq check` rule).  Tech-lead may also co-author `guide` items (see playbook). |
| `architect` | `decision`, `guide` | ADRs and cross-cutting guides are the architect's output.  The architect has a playbook role on `epic` items (shapes them technically) but does not create them. |
| `reviewer` | `review` | Opens a review and logs findings. |
| `qa` | `bug` | Files defect reports. |
| `*-dev` (any dev) | none that create a new top-level item | Devs implement on tasks.  A dev that discovers a defect files a `bug` only through the QA role; the playbook explicitly tells devs to "file a newly-found defect as a bug" — but the `--author` for the bug should be `qa`.  (If a dev-authored bug is more pragmatic in practice, this rule should be relaxed in the ADR.) |
| `tech-writer` | `guide` | Polishes and publishes guides authored by architect. |
| `devops` | none defined in playbook | Devops interacts with the infrastructure layer, not with squads item types directly.  Out-of-lane creates should warn. |
| `manager` | all types | The manager is an orchestrator and may author any item for coordination purposes (e.g. filing a feature for triage, creating an epic to group incoming work). |

**Multi-type roles:** `tech-lead` legitimately authors tasks AND co-authors
guides.  `architect` legitimately authors decisions AND guides.  `manager`
is exempt across all types.

**The `*dev` create-lane gap:** the playbook has no in-lane create for devs
beyond "fix it inside a task."  If a dev needs to file a bug, it should call
`--author qa` (or the operator registers the dev as also holding qa rights).
The ADR should decide whether to allow dev-authored bugs with a warning, or to
require the qa slug.

### 2. Mutate lanes

"Mutate" covers: status transitions, body edits, metadata updates (assignee,
priority, parent), and sub-entity mutations (add/update subtask, story, finding).

**Three options with clear trade-offs:**

**Option A — Creates laned, mutations unrestricted (minimal friction)**
Only the `sq create` author check is enforced.  Anyone may transition or edit
any existing item.  This matches today's sq check scope and adds zero friction
to the normal work loop (tech-lead moving a feature to InProgress, QA closing a
bug, manager reassigning a task mid-sprint).

*Recommendation target:* lowest possible friction for an advisory system.
Mutations are cooperative; the actor field in the reflog already records who did
what for forensics.

**Option B — Status transitions laned (moderate friction)**
Status transitions are additionally checked: only the role that owns the item
type's lifecycle transitions may advance it.  Example: only `reviewer` may move
a review to Approved; only `qa` may move a bug to Verified.  Body edits and
metadata remain unrestricted.  The manager is always exempt.

*Trade-off:* higher fidelity lifecycle ownership; adds friction when the
tech-lead or manager needs to close out an item the owning role has already
vacated.

**Option C — All mutations laned (highest friction)**
Only the assignee (plus manager and tech-lead) may transition or edit an item.
This is the strictest dial and the highest friction: any agent reading and
commenting on a foreign item would need an override.  Not recommended for an
advisory system.

**Recommendation: Option A for Slice B.**  The advisory posture means the
value of mutation restrictions is marginal relative to the friction they add.
The reflog already provides full audit coverage.  Status-transition laning
(Option B) can be introduced in a later slice if real incidents show the need
without pre-emptively breaking the work loop.  The ADR should record this
decision explicitly so it is not re-litigated ad-hoc.

### 3. Advisory behavior: warn-and-proceed

An out-of-lane action should:

1. **Emit a visible warning** naming the action taken, the acting role, and
   the role that owns this lane.  Example: "Warning: `python-dev` is not the
   in-lane author for `feature` items (expected: `product-owner`).  Proceeding
   anyway."
2. **Complete the action** — never hard-block.  The operator or manager can
   always instruct a role to act outside its lane for a legitimate reason; a
   hard stop makes that impossible without a bypass flag, which adds complexity
   without commensurate safety (recall: advisory, not enforcement-grade).
3. **Record the warning in the reflog** alongside the operation, so the
   forensic trail is complete.

This must never be presented as a security boundary.  The warning text and
any docs MUST include language like "advisory lane check" or "best-effort,
not forge-proof."

A `--no-lane-check` (or equivalent) override flag is not required in the first
cut; the system proceeds anyway by design.

### 4. Operators and manager exemptions

- **Operators (`op-*` slugs):** humans acting via `--as op-<slug>` are exempt
  from lane checks.  An operator may author any item type; they coordinate
  freely.  Lane checks apply only to agent role slugs.
- **Manager (`manager` slug):** exempt from all lane checks.  The manager
  orchestrates the whole team and must be able to create, transition, and edit
  any item without friction.
- **Tech-lead (`tech-lead` slug):** exempt from mutation-lane checks (if any
  are introduced in a future slice) on any item type they legitimately supervise
  (features, tasks, epics).  Create-lane rules still apply: a tech-lead
  authoring a feature gets a warning, since that is the product-owner's lane.

### 5. Acceptance criteria for Slice B

All checks in this slice are **advisory** — they warn and proceed; they never
hard-block.

**AC-B1 — Create-lane warning.**  When a role authors an item type outside its
in-lane create list (table in §1), `sq create` emits a visible warning naming
the acting role and the expected in-lane role.  The item is still created
successfully.

**AC-B2 — Warning in the reflog.**  The out-of-lane warning (AC-B1) is recorded
in the reflog alongside the create operation, tagged as an advisory lane check,
so the forensic trail is complete.

**AC-B3 — Manager and operator exemption.**  `manager` and `op-*` slugs receive
no lane warning on any create or mutation.  Tech-lead receives no lane warning
for task creation.

**AC-B4 — Identity is advisory.**  The actor used for the lane check is the
self-declared `--as` slug (or the recorded session actor).  The feature
MUST NOT claim that this check is tamper-evident or forge-proof; docs and any
CLI output must use "advisory" or "best-effort" language.

**AC-B5 — Lane table is derivable.**  The in-lane create table is derived from
`_interactions.py` and the CLAUDE.md team workflow conventions; it is not
hard-coded as a magic string list.  Adding a new playbook entry for a role
extends its lane without a separate config change.

**AC-B6 — No regression on mutations (Option A).**  If Option A is chosen,
no mutation (status transition, body edit, metadata update) triggers a lane
check.  Mutations remain unrestricted in Slice B.

**AC-B7 — `sq role <slug> show` surfaces the create lane.**  The in-lane
create types for a role are visible from `sq role <slug> show`, consistent with
how `can_spawn` is surfaced for Slice A.
<!-- sq:body:end -->

## User Stories

_Add with `sq feature 122 add-story "As a <role>, I want … so that …"`; track with `sq feature 122 story <n> update --status <Status>`._

<!-- sq:summary -->
| Story | Status | Assignee | Title |
| --- | --- | --- | --- |
| US1 | Done |  | Full structured capability profile per role (Slice B — gated on FEAT-000125) |
| US2 | Done |  | Leaf roles structurally blocked from spawning agents (Slice A — fixes BUG-000152) |
<!-- sq:summary:end -->

<!-- sq:stories -->

<!-- sq:story:US1 -->
### US1 — Full structured capability profile per role (Slice B — gated on FEAT-000125)

<!-- sq:story:US1:head -->
**Status:** 🟢 Done
<!-- sq:story:US1:head:end -->

<!-- sq:story:US1:body -->
As a squad manager, I want each worker role to declare its create lane and have out-of-lane creates surface a visible advisory warning, so that I can detect accidental lane violations in the reflog without blocking legitimate cross-lane coordination.

**Scope (Slice B):** extends the RoleDef capability model to a per-role create lane, checked at sq-create time against the actor slug (self-declared / env-sourced — best-effort, untrusted). All checks are advisory: they warn and proceed, never hard-block.

**Acceptance (testable):**

- AC-B1: When a role slugged actor (not manager, not op-*) authors an item type outside its in-lane create list, sq create emits a visible warning naming the acting role and the expected in-lane role. The item is still created successfully (exit 0).

- AC-B2: The out-of-lane warning is recorded in the reflog alongside the create operation, tagged as an advisory lane check.

- AC-B3: manager slug and op-* slugs receive no warning. tech-lead receives no warning for task creation.

- AC-B4: The lane check uses the self-declared --as slug (or env session actor). Any CLI output and docs must use 'advisory' or 'best-effort' language; no tamper-evident or forge-proof claim may appear.

- AC-B5: The in-lane create mapping is derived from _interactions.py PLAYBOOK (not a hard-coded string list); adding a new RoleGuide entry extends the lane automatically.

- AC-B6 (if Option A mutation stance is adopted): no status transition, body edit, or metadata update triggers a lane check in Slice B.

- AC-B7: sq role <slug> show surfaces the role's in-lane create types, consistent with the can_spawn surfacing in Slice A.

**Gate:** FEAT-000125 is Done. Slice B may proceed once the architect's enforcement-model ADR is approved.
<!-- sq:story:US1:body:end -->

#### Discussion

<!-- sq:story:US1:discussion -->
<!-- sq:story:US1:discussion:end -->
<!-- sq:story:US1:end -->

<!-- sq:story:US2 -->
### US2 — Leaf roles structurally blocked from spawning agents (Slice A — fixes BUG-000152)

<!-- sq:story:US2:head -->
**Status:** 🟢 Done
<!-- sq:story:US2:head:end -->

<!-- sq:story:US2:body -->
As any leaf-role agent (dev, qa, reviewer, architect), I want the system to prevent me from invoking the Agent/Task spawn tool, so that I cannot accidentally (or autonomously) re-delegate work that was assigned to me.

**Scope:** all roles where can_spawn is False — includes all developer roles (python-dev, etc.), qa, reviewer, and architect. Manager and tech-lead retain spawn authority.

**Acceptance:**

- Every leaf-role agent definition carries disallowedTools: Agent in its backend-rendered frontmatter.

- A leaf-role session launched via squads cannot invoke the Agent or Task spawn tool; enforcement is at the backend/session level (agent definition), not merely advised in the skill file.

- The can_spawn flag is visible via sq role <slug> show for each role.

- Attempting to spawn from a leaf role produces a clear error, not a silent no-op.

**Fixes:** BUG-000152 (python-dev self-spawn cascade). No dependency on FEAT-000125 — tool binding is type-bound at spawn time.
<!-- sq:story:US2:body:end -->

#### Discussion

<!-- sq:story:US2:discussion -->
<!-- sq:story:US2:discussion:end -->
<!-- sq:story:US2:end -->
<!-- sq:stories:end -->

## Discussion

<!-- sq:discussion -->
- [2026-06-17T20:12:08Z] Pierre Chat:
  - Prioritised: real-world incident BUG-000152 (a python-dev subagent self-spawned ~6 levels deep) is the motivating case for this feature — leaf specialists must not carry the Agent/Task spawn tool. Picking this up very soon.
- [2026-06-21T21:34:54Z] Robert Architect:
  - Q2 enforcement boundary — CONFIRMED feasible at the Claude Code backend, and it's a small change. Claude Code subagent definitions support a 'tools:' allowlist and a 'disallowedTools:' denylist in YAML frontmatter; omitting tools inherits all tools. Denying the spawn tool is literally one line: disallowedTools: Agent (the Task tool was renamed Agent in 2.1.63; Task still works as an alias). The harness enforces the subagent definition's own tool restrictions when that subagent runs — so a leaf role whose definition denies Agent structurally cannot spawn. This is real enforcement, not advice.
  - Q2 where it lives — exactly where the open question/scope guessed: src/squads/_backends/_claude_code/_backend.py::generate_role_entry, which renders the agent pointer via templates/claude/pointer_agent.md.j2. That template already emits the agent frontmatter (name/description/model/color/skills). The change is (a) add a capability field to RoleDef in src/squads/_roles/_catalog.py (e.g. can_spawn: bool, default False; True for manager/tech-lead), and (b) add a {% if not can_spawn %}disallowedTools: Agent{% endif %} line to pointer_agent.md.j2. No sq-runtime check needed; sq stays the CLI, the backend owns the session contract. (A coarser belt-and-suspenders option: settings.json deny rules, but per-role lives correctly in the agent definition, not global settings.)
  - Q2 boundary caveat — enforcement sits at the SUBAGENT DEFINITION the harness loads from .claude/agents/<slug>.md. It binds when an agent is launched by type (claude --agent / Agent(slug)). It does NOT bind an arbitrary main-thread session a human starts and then says '--as architect' in prose; that path is governed by the operator's own session settings, not our pointer. For the BUG-000152 cascade (manager spawns python-dev BY TYPE) this is exactly the right and sufficient boundary.
- [2026-06-21T21:35:15Z] Robert Architect:
  - Q3 THE DEPENDENCY VERDICT — Catherine's hypothesis is CORRECT. FEAT-000122's leaf-no-spawn slice does NOT require FEAT-000125. The agent TYPE determines the toolset at spawn time: when the manager spawns subagent_type=python-dev, the harness loads .claude/agents/python-dev.md and applies its disallowedTools BEFORE the child runs a single turn. Withholding the spawn tool needs no verified identity, because the constraint is bound to the type at launch, not checked against a self-declared slug at sq-time. The child can't spawn even if it lies about who it is — it simply doesn't hold the tool.
  - Q3 cont'd — identity (125) only matters for the BROADER threat: 'an agent CLAIMS a privileged role it wasn't spawned as' (the --as reviewer self-review of 2026-06-15) and 'verify a review lineage was independent.' That is real and worth doing, but it is a DIFFERENT failure mode from BUG-000152. BUG-000152 is a capability problem (leaf carries Agent tool); the self-review incident is an identity/attribution problem. Capability attenuation defends the first WITHOUT identity; only the cross-role-claim and separation-of-duties cases (122's later acceptance bullet 'developer cannot do squad ops outside its lane', plus FEAT-124) genuinely lean on 125.
  - Q3 ref recommendation — the FEAT-000125 depends-on ref is TOO STRONG for the whole of 122 and should be relaxed, NOT removed (I am not touching it per scope — flagging for Catherine). Accurate shape: 122's US2 (reviewer/leaf structurally blocked from spawning) depends on NOTHING — ships on type-bound tool lists alone. 122's 'lane enforcement' acceptance (dev can't mutate items outside its assignment) is where verified identity helps and where a depends-on 125 is legitimate. Suggest re-pointing the dependency at that narrower slice or downgrading to a plain 'relates-to' ref.
  - Q4 RECOMMENDATION — carve a thin slice out of 122: 'Leaf specialists do not carry the spawn (Agent/Task) tool.' Implement it now to close BUG-000152: add can_spawn to RoleDef (manager+tech-lead True, all others incl. devs/reviewer/qa/architect False), emit disallowedTools: Agent in pointer_agent.md.j2 for non-spawners, surface it in 'sq role <slug> show', add a backend test asserting the rendered agent file denies Agent for a dev. This is independent of 125 and unblocks the bug immediately. Keep 122's richer capability-profile model (US1 structured profile, lane enforcement) tied to 125 as designed.
  - Q4 ADR — YES, this warrants a formal decision item, because it sets a durable boundary the rest of the epic builds on. The ADR should DECIDE: (1) enforcement lives at the Claude Code backend via per-role tool lists in the agent definition, not as an sq-runtime check; (2) the first attenuation cut is 'all tools minus Agent/Task' for non-orchestrator roles, with spawn authority reserved to manager + tech-lead; (3) capability profiles requiring identity-aware checks (lane enforcement, separation of duties) are explicitly gated on FEAT-000125 and out of the standalone slice. I can author this ADR on Catherine's go.
- [2026-06-21T21:40:11Z] Nina Product:
  - Relaxed the FEAT-000125 ref from depends-on to related. The leaf-no-spawn slice (Slice A, US2) binds a tool denylist to the agent type at spawn time — it requires no verified identity, only a can_spawn flag in RoleDef and a disallowedTools line in the agent template. FEAT-000125 identity/lineage is only relevant for the richer lane-enforcement slice (Slice B), which is explicitly gated on it. The depends-on ref was blocking the whole feature; a plain related ref is accurate for that narrower coupling.
- [2026-06-22T09:04:45Z] Nina Product:
  - Per the June 2026 reframe of FEAT-000125: squads is a passive CLI tool invoked by agents — it has no spawn moment and cannot mint, inject, or propagate identity. The strongest guarantee available is a spawner-minted nonce, recorded-not-signed (see ADR-000158).
  - Consequence for Slice B (lane enforcement via actor identity): lane enforcement built on the FEAT-000125 actor record can only ever be **advisory** — catching the accidental case (an agent that misbehaves without actively forging its lineage), not stopping a deliberate forger. Whoever scopes Slice B should frame its checks as 'catch the accident, not stop the adversary,' consistent with ADR-000155's gate on signed identity. Do not ship Slice B as enforcement-grade until a platform-level signed identity capability exists.
  - Related: FEAT-000125 (reframed to best-effort lineage observability), ADR-000158 (design), ADR-000155 (capability-attenuation gate).
- [2026-06-22T12:13:10Z] Nina Product:
  - Lane-rules spec filed — Slice B input for the architect's enforcement-model ADR.
  - **Create lanes (derived from _interactions.py + CLAUDE.md):** product-owner → feature/epic; tech-lead → task (+ co-author guide); architect → decision/guide; reviewer → review; qa → bug; *-dev → none (author bug via --author qa); tech-writer → guide; devops → none defined; manager → exempt (all types). Manager and op-* slugs bypass all checks.
  - **Mutate stance: recommend Option A (creates laned, mutations unrestricted).** Advisory posture makes mutation restrictions marginal relative to friction cost. The reflog provides full audit coverage. Status-transition laning (Option B) noted as an option if future incidents justify it — the ADR should decide and record this explicitly.
  - **Advisory behavior:** warn-and-proceed. Emit a visible warning naming acting role + expected lane owner; complete the action; record the warning in the reflog. Never hard-block. All output and docs must use 'advisory' / 'best-effort' language — not enforcement-grade.
  - **Dev bug-author gap:** the playbook has no in-lane create for devs. Recommend allowing dev-authored bugs with a warning (same advisory posture) rather than requiring the qa slug — @architect please decide and record in the ADR.
  - See body for the full lane table, Option A/B/C trade-off analysis, and AC-B1 through AC-B7 testable acceptance criteria. @architect: this is the input for the lane enforcement ADR.
- [2026-06-22T12:16:51Z] Robert Architect:
  - Slice B enforcement-model ADR filed: **ADR-000163** — Advisory create-lane enforcement. Adopts Nina's lane-rules spec (§1–§5, AC-B1..AC-B7) verbatim; does not redefine it.
  - Six decisions: (1) **creates only** (Option A) — mutations unlaned this cut, Option B recorded as a future upgrade; (2) lane **derived from _interactions.py PLAYBOOK**, one source, test-locked to the §1 table — no duplicate; (3) **warn-and-proceed** in the service layer, warning rides back on CreateResult.lane_warning → CLI prints it escaped via e(), exit 0, also into the create op's reflog delta, JSON-aware (no service-layer printing); (4) keyed on the **untrusted self-declared author/--as slug**; session (FEAT-125) is forensic context only, never the decision basis; advisory/best-effort everywhere, no security claim; (5) **manager + op-* exempt** (checked before lookup); tech-lead needs no carve-out — 'task' is already in its derived lane; (6) surface the create lane in **sq role show** alongside can_spawn (AC-B7).
  - **Open question resolved (dev-authored bugs):** ALLOWED with the standard advisory warning (expected owner: qa); we do NOT require --author qa. It's just one instance of the general out-of-lane-but-allowed rule — no special-case code path, keeps the dev create-lane empty.
  - Status **Proposed** — goes to @op-pierre for approval before any build. Once approved, @tech-lead can break it down against US1 (AC-B1..AC-B7); see the 'For the tech-lead' section in the ADR body for the three additive seams and the derivation-brittleness mitigation.
<!-- sq:discussion:end -->
