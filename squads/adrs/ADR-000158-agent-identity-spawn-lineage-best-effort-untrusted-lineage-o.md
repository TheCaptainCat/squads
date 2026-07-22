---
id: ADR-158
sequence_id: 158
type: decision
title: 'Agent identity & spawn lineage: best-effort, untrusted lineage observability
  (squads records env, never spawns)'
status: Accepted
author: architect
priority: medium
refs:
- FEAT-125:implements
- ADR-155
- FEAT-24
- EPIC-121
description: squads reads optional SQUADS_SESSION_ID/PARENT from its own invocation
  env if present and records them additively (reflog + frontmatter, back-compat);
  it never mints, spawns, or injects (it is never in the spawn path). Guarantee is
  best-effort, untrusted, observability-only — not verified identity; lane enforcement
  on it is advisory.
created_at: '2026-06-22T07:44:10Z'
updated_at: '2026-07-22T11:53:22Z'
---
<!-- sq:body -->
## Context

squads records an `actor` on every mutating operation, but that actor is a **self-declared slug**:
`src/squads/_actor.py` holds one module-global string, set to `"system"` at the CLI root callback
(`_cli/__init__.py::main_callback`) and overridden only by the `--as`/`--author` CLI options via
`set_actor(slug)`. The reflog writer (`_index/_reflog.py::append_line`) faithfully records whatever
that global says into a flat `actor: str` field; `ReflogLine`/`ReflogEntry` carry it as a bare
string. There is **no env-var or config ingestion path** into the actor today — the only inputs are
CLI flags.

Two blind spots follow:

1. **Authorship is unverified.** The 2026-06-15 incident (REV-118 carried `author: reviewer`)
   was recorded faithfully but was indistinguishable from an independent review at every surface.
2. **Spawn lineage is invisible.** Agent spawning happens in the Claude Code Task/Agent-tool layer,
   **above and outside** sq's view. sq is invoked *by* an already-running agent; it never sees the
   spawn event, so it cannot on its own know that the architect spawned the reviewer.

**Threat model (from FEAT-125, binding on this design):** we defend against *accidental and
uncontrolled autonomy, not malicious agents*. We are not trying to stop a deliberate forger; we are
trying to make uncontrolled lineage (recursive self-spawn, self-review) **visible and attributable**
after the fact, on a best-effort basis. That lower bar is what keeps a 1.x mechanism achievable.

### The hard constraint: squads is never in the spawn path

This is the load-bearing fact that shapes everything below, and the correction to the earlier draft.

- **squads is a passive CLI.** It runs only when an agent (or human) types `sq …`. It is a leaf the
  agent calls, not a process that launches other processes. There is **no point in squads where one
  agent becomes the parent of another** — that event lives wholly in the Task/Agent harness layer.
- **Therefore squads cannot mint, spawn, or inject.** It has no "spawn moment" to hook. It cannot
  put a nonce into a child's environment, because from squads' perspective there is no child and no
  spawn — only its own one-shot invocation with whatever environment that invocation happens to
  carry.
- **What squads *can* do** is read variables that are **already present in its own environment** at
  the moment it is invoked, and record them. Nothing more. Whether those variables were set, by
  whom, and whether they reflect a real lineage is entirely outside squads' knowledge and control.

**Who would set such variables, then?** If a session/parent id is to exist at all, **establishing and
propagating it is the agent layer's job** — expressed in orchestrator (manager / tech-lead)
**skills and prompts**. When such an orchestrator spawns a specialist via the Task tool, its own
prompt/skill would arrange for that child's subsequent `sq` calls to carry the id (e.g. by having the
child pass it on every invocation, or by the harness's environment-passing if/when one exists). **All
of that is outside squads code** and is not specified or guaranteed by this ADR; squads neither
requires it nor can verify it happened. In the common case today, **no such variable is set**, and
the actor is simply the self-declared slug — exactly as it is now.

## Decision

### 1. Identity primitive — squads reads optional env at the actor chokepoint *if present*, and records it. It does not mint, spawn, or inject.

squads does not generate or propagate identity. Its entire role is **read-and-record**:

- **What squads reads.** Two **optional** environment variables, read **once** at the CLI root
  callback (`_cli/__init__.py::main_callback`), **if present**:
  - `SQUADS_SESSION_ID` — an opaque id for the current session, if the environment carries one.
  - `SQUADS_PARENT_SESSION_ID` — the parent session's id, if the environment carries one.
  squads treats both as opaque strings. It does not validate, parse, or attribute them; it does not
  care how they were generated.
- **Who sets them — explicitly out of scope for squads.** Whatever puts those variables into the
  environment is the **agent / harness layer**, not squads. Concretely, an orchestrator role's
  **skill or spawn prompt** would be responsible for ensuring a spawned specialist's `sq`
  invocations carry these vars. squads does not mint them, does not inject them into any child
  (it has no child), and does not depend on them existing. This is the same Task/Agent layer that
  ADR-155 already identified as the only place spawn policy can live; identity propagation, like
  spawn policy, lives there and **not in squads**.
- **The absent case is the common, fully-supported case.** When neither variable is set (today's
  reality, and the default whenever an orchestrator skill hasn't been written to propagate them),
  the actor is just the slug — `system` at the root, or the `--as`/`--author` slug — **exactly as
  now**. No behaviour changes, no migration, no degradation. The session fields are simply `None`.
- **Where squads ingests it (single chokepoint).** `main_callback` already unconditionally calls
  `actor.set_actor("system")`. Extend `_actor.py` to carry an optional session pair alongside the
  slug, seeded **once** from the environment at that same callback **if the vars are present**. The
  slug override path (`--as`/`--author` → `set_actor`) still sets the human-facing slug; the session
  fields come only from the environment and are **not** settable by a later CLI flag. One
  ambient-identity module (mirroring `_clock`), and every mutating op already routed through
  `actor.current_actor()` picks up whatever session was read for free.

### 2. Honest guarantee — best-effort, untrusted, observability-only. Not verified identity.

This is the heart of the revision and must be stated prominently so no future surface over-trusts the
field:

- **Best-effort.** squads records a session/parent id **only when one happens to be in its
  environment.** It cannot cause one to be there, cannot detect when one is missing-but-expected, and
  cannot tell a real lineage from a fabricated one.
- **Untrusted.** A `session_id` / `parent_session_id` is whatever the calling environment supplied,
  and the calling agent fully controls its own environment and its own `--as` slug. The structured
  actor is therefore **a self-declaration one hop wider than the slug already was** — not a
  verification of anything. It is **not tamper-evident**, **not signed**, and a self-declared slug
  remains exactly that: a self-declaration.
- **Observability-only.** The value of this feature is **forensic visibility**, not enforcement:
  recording and rendering the lineage that *was declared*, so an after-the-fact reader can *see* a
  self-review or a recursive spawn pattern. It must **never** be trusted as an authorization input.
- **1.0 contract wording.** The 1.0 stability contract (FEAT-13) must state this in the field's
  own definition: the recorded actor (slug + optional session/parent) is **untrusted, best-effort
  lineage for observability**, explicitly **not** verified identity and explicitly **not** a basis
  any `sq check` may trust for enforcement. Cryptographic / platform-verified identity is deferred
  until a platform capability exists; if one ever does, it would be a *new* primitive, not a
  re-interpretation of this field.

### 3. Structured actor record — additive, dual-form, back-compatible *(survives the correction unchanged)*

These are pure recording/rendering mechanics and are unaffected by who sets the env vars. Extend the
recorded actor from a bare slug to an optional structured record:
`{"slug": "reviewer", "session_id": "…", "parent_session_id": "…"}` — where the two session fields
are present only when the environment carried them.

- **Reflog (`_index/_reflog.py`).** Today the line is `{"actor": "python-dev", …}` (a string).
  **Keep `actor` as the bare slug string for back-compat**, and **add two optional sibling
  top-level fields** `session_id` and `parent_session_id` (both nullable). Purely additive: the
  reader already does `data.get("actor", "")` and tolerates unknown fields; old lines (no session
  fields) parse as `session_id=None, parent_session_id=None`. `ReflogLine`/`ReflogEntry` gain the
  two optional fields. Preferred over nesting `actor` into an object because (a) it does not break
  the documented flat-string `actor` (FEAT-13 stability), and (b) every existing golden-tested
  `--json` shape stays valid.
- **Item frontmatter.** Items today store only `author: str | None` (`_models/_item.py`). To surface
  the creating/last-modifying *session*, add two optional frontmatter fields (e.g. `created_session`
  / `modified_session`, each an optional `{session_id, parent_session_id}` sub-object, or just the
  `session_id` for minimal footprint). `from_frontmatter` reads them as `None` when absent;
  `to_frontmatter` omits them when unset — existing item files remain valid with no migration.
  **Back-compat rule: absence == legacy slug-only origin; both forms valid forever.** If full
  structured history is wanted, the reflog already holds it — frontmatter can stay minimal and
  `show` can join against the reflog.

### 4. Propagation through indirect chains — immediate parent only *(unchanged, with the caveat that propagation is the agent layer's, not squads')*

When the env carries them, each op records **its own `session_id` and its immediate
`parent_session_id`** — not the full ancestor chain.

- The full chain is **reconstructable** by walking `parent_session_id` edges across reflog lines, so
  storing it inline would be redundant and bloat every line.
- Storing only the immediate parent keeps the line a fixed, small shape.
- **The act of carrying the right ids from parent to child is the agent/harness layer's
  responsibility**, not squads'. squads records whatever each invocation declares; a manager →
  tech-lead → dev chain emerges only if the orchestrator skills actually propagate the ids. A
  missing/absent intermediate session degrades gracefully to a forest (roots), never corrupting the
  chain. squads makes no promise that the chain is complete or accurate.

### 5. Surfacing — both views feasible, and both are forensic-only *(survives the correction)*

- **`sq reflog --tree`.** Feasible directly from what is recorded: build a parent→children map from
  each line's `session_id` + `parent_session_id`, treat lines with no/unknown parent as roots, and
  render a nested tree over the existing time-window filter. A self-review surfaces as a *visibly
  non-independent* subtree — **but the reader must understand this reflects declared, untrusted
  lineage, not verified fact.** This is the core forensic win and the rendering must be labelled as
  observability, not proof.
- **`sq <type> <n> show --full`.** Feasible: surface the creating and last-modifying actor's session
  identity (when present), from the optional frontmatter session fields or by joining the item id
  against the reflog. Show `slug @ session_id (parent parent_session_id)` so a self-authored item
  reads differently from an independently-authored one — again as observability, not verification,
  and gracefully showing just the slug when no session is recorded.

### 6. Feasibility verdict & scope boundary

- **1.x CAN do:** read optional `SQUADS_SESSION_ID` / `SQUADS_PARENT_SESSION_ID` from its own
  invocation environment **if present** and record them additively on every mutating op; expose a
  reconstructable spawn tree and a `show --full` surface; remain fully back-compatible (absence =
  legacy slug-only). Uncontrolled autonomy becomes **observable and attributable on a best-effort
  basis** — visible to a human reading the reflog.
- **1.x CANNOT do:** mint, spawn, or inject identity (squads is never in the spawn path); obtain a
  *verified* actor; provide tamper-evidence. A forged or simply-wrong `session_id` /
  `parent_session_id` / `--as` slug is indistinguishable from a real one. squads sees only what the
  invocation's environment and flags carry, and ultimately the self-declared slug.
- **Explicitly out of scope for squads:** setting or propagating the env vars. That is the agent /
  harness layer (orchestrator skills and spawn prompts), and this ADR neither specifies nor
  guarantees it.

### 7. Knock-on for FEAT-122 Slice B (lane enforcement)

Because squads can **never obtain a verified actor**, any lane enforcement keyed on the recorded
actor (slug or session) is **inherently advisory**:

- It can **catch the honest accident** — a dev whose declared actor wanders out of its lane is
  flagged because it carries (or fails to carry) the lineage it was actually given.
- It is **trivially bypassable** by a wrong/forged `--as` slug or a fabricated/omitted session id.
  Nothing squads observes is trustworthy enough to *stop* a deliberate or careless override.
- **Therefore Slice B must be framed and documented as advisory ("catch the accident"), never as a
  security boundary ("stop the adversary").** Per ADR-155, identity-aware capability *enforcement*
  that must trust *who* an actor really is stays gated on a future signed-identity capability that
  does not exist in 1.x. Slice B must not over-claim, and must not present a lane check as a
  guarantee.

## Consequences

- **Positive.** Spawn lineage becomes **observable** with zero platform dependency and zero squads
  involvement in spawning — squads simply records optional env it is handed. All changes are
  additive: one optional ambient field-set in `_actor.py`, two optional reflog fields, two optional
  item frontmatter fields, one `--tree` rendering. No migration is forced (absence = legacy). The
  forensic goal (a 2026-06-15-style self-review reads as non-independent *to a human reader*) is met.
- **Negative / limits.** **Best-effort and untrusted**: squads is never in the spawn path, cannot
  mint or inject, cannot verify, and is not tamper-evident. Whether any session id ever appears
  depends entirely on agent-layer skills/prompts that squads does not own and cannot enforce; in
  their absence the actor is just the slug. Honesty about this guarantee must live in the docs, in
  the 1.0 contract field definition, and in any check built on it.
- **Correction note.** This ADR previously (mis)attributed minting + env injection to a squads
  spawner role. That is retracted: squads is a passive tool, never in the spawn path, and does only
  read-and-record. Identity propagation, like spawn policy (ADR-155), lives in the agent layer.
- **Follow-ups for the tech-lead.** US1 = the read-and-record path (optional env read at the
  callback into the `_actor.py` session pair, the two additive reflog fields, the optional item
  frontmatter fields, schema bump). US2 = `sq reflog --tree` + `show --full` session surfacing,
  **both labelled as untrusted observability**. Document the guarantee ("best-effort, untrusted
  lineage for observability — not verified identity, not forge-proof, not an enforcement input") in
  the reflog schema docs and the 1.0 contract (FEAT-13). Coordinate the additive schema bump with
  the migration registry per CLAUDE.md. Frame any FEAT-122 Slice B lane check as advisory.
<!-- sq:body:end -->

## Discussion

<!-- sq:discussion -->
- [2026-06-22T09:04:58Z] Robert Architect:
  - Revised per Pierre's correction (foundational): squads is a passive tool that agents invoke — it is NEVER in the spawn path. Spawning lives entirely in the Claude Code / Task layer, driven by the agents. So squads cannot mint a nonce at spawn time or inject env vars into a child; it has no spawn moment to hook.
  - Retracted the earlier framing that cast a squads role as the spawner that mints+injects. Recast the identity primitive as read-and-record only: squads reads optional SQUADS_SESSION_ID / SQUADS_PARENT_SESSION_ID from its own invocation env IF present, and records them. Setting/propagating those vars is the agent layer's job (orchestrator skills/prompts), explicitly out of scope for squads.
  - Guarantee downgraded and stated prominently: best-effort, explicitly-UNTRUSTED, observability-only — not verified identity, not tamper-evident. A self-declared slug stays a self-declaration; the session pair just widens it one hop. Wrote this into the 1.0 contract wording so no future sq check over-trusts the field.
  - Kept what survives the correction (pure recording/rendering): additive dual-form actor (flat slug + optional sibling session_id/parent_session_id), slug-only back-compat, sq reflog --tree, show --full surfacing, additive schema bump via the migration registry.
  - Knock-on for FEAT-122 Slice B: since squads can never obtain a verified actor, lane enforcement keyed on it is inherently ADVISORY — catches the honest accident, bypassable by a wrong/forged --as or session id. Must be framed as 'catch the accident,' never as a security boundary. Title updated to drop 'spawner-minted'.
- [2026-06-22T09:10:06Z] Pierre Chat:
  - Accepted on the reframed basis: squads records best-effort, untrusted lineage (reads env if present, never spawns/injects). Build FEAT-125 as observability, then Slice B as an explicitly-advisory guardrail.
<!-- sq:discussion:end -->
