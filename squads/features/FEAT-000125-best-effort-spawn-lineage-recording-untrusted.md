---
id: FEAT-125
sequence_id: 125
type: feature
title: Best-effort spawn-lineage recording (untrusted)
status: Done
parent: EPIC-121
author: product-owner
priority: low
refs:
- FEAT-24
- ADR-158
subentities:
- local_id: US1
  title: Structured actor record in the reflog (slug + session + parent)
  status: Done
- local_id: US2
  title: Spawn-tree view in sq reflog
  status: Done
created_at: '2026-06-15T11:56:19Z'
updated_at: '2026-06-22T12:01:00Z'
---
<!-- sq:body -->
## Reframe note

This feature was originally scoped as "Real agent identity and spawn lineage" and promised that session identity would be "issued at spawn time and cannot be self-set by the agent" (tamper-evident, verification-grade). That framing was corrected in June 2026: **`sq` is a passive CLI tool that agents invoke; it has no spawn moment and cannot mint, inject, or propagate identity.** Spawning is the Claude Code / Task-tool layer's job, not squads'. The most squads can do is read an id from its invocation environment *if one is present* and record it. This reframe adjusts the scope accordingly.

## Problem

Every mutating operation in squads records an `actor` — but that actor is a **self-declared `--as` slug** (e.g. `--as reviewer`) or defaults to `actor=system`. The reflog (FEAT-24) captures this field faithfully, but faithful recording of an untrusted input is not the same as trustworthy identity. The 2026-06-15 incident proved the cost: REV-118 carried `author: reviewer` and the reflog recorded it as such, making the self-review indistinguishable from an independent one at every observable surface (see EPIC-121).

Beyond authorship, squads is blind to **spawn lineage** — the tree of who spawned whom. Spawn events happen in the Claude Code / Task-tool layer, below sq's view. squads never sees the spawn event and cannot participate in it.

## Value

squads can become observability infrastructure for lineage without needing to own identity. If an orchestrator cooperates — minting a session nonce at spawn time and passing it to the child via env vars — squads can **record** that nonce on every operation, surface it in the reflog, and render a spawn-tree view. This makes uncontrolled autonomy (recursive self-spawn, self-review) **visible and attributable** after the fact. That forensic win is achievable today, with zero platform dependency.

This is **observability for forensics, not verification.** The guarantee is explicitly untrusted: the nonce is readable and copyable by the agent that holds it. A self-declared slug remains a self-declaration; nothing in squads is tamper-evident or enforcement-grade. squads records what it is given. Setting and propagating the session id is the agent/orchestrator layer's job (via spawn-time env vars or skill-level conventions), entirely outside squads.

## Scope

- **Structured actor record.** Extend the recorded actor from a bare slug to an optional structured record: `{slug, session_id, parent_session_id}`. squads reads `SQUADS_SESSION_ID` and `SQUADS_PARENT_SESSION_ID` from its invocation environment at the CLI root callback — once, via `_actor.py` — if present. The slug override path (`--as` / `--author`) continues to set the human-facing slug; the session fields come only from the environment and are not settable by a later CLI flag.
- **Additive, dual-form, back-compatible.** Reflog lines gain two optional sibling fields (`session_id`, `parent_session_id`); the `actor` field stays a flat slug string for back-compat. Item frontmatter gains optional `created_session` / `modified_session` sub-objects. Absence means legacy slug-only origin; both forms remain valid forever. A schema version bump marks the additive fields.
- **Spawn-tree view.** `sq reflog --tree` renders a nested tree of operations grouped by spawn lineage for a time window. Operations with no/unknown `parent_session_id` appear as root nodes. The 2026-06-15 self-review would produce a visibly non-independent subtree.
- **`show --full` surfacing.** `sq <type> <n> show --full` surfaces the creating and last-modifying actor's session identity (slug + session_id + parent) where recorded.
- **Honest guarantee in docs.** The guarantee is documented as "attributable, accident-evident — not forge-proof." No check built on this model may claim enforcement-grade or tamper-evident semantics.

Relates to ADR-158 (Agent identity & spawn lineage: spawner-minted session nonce, recorded-not-signed).

## Acceptance

- Every `sq` mutating operation records a structured actor: `{slug, session_id, parent_session_id}` — where session fields are populated from `SQUADS_SESSION_ID` / `SQUADS_PARENT_SESSION_ID` if present in the invocation environment, and `None` otherwise.
- The session fields are read from the environment once at CLI startup; they are not settable by any later CLI flag.
- `sq reflog --tree` renders a spawn-tree view grouped by session lineage; operations with no/unknown parent appear as root nodes.
- `sq <type> <n> show --full` surfaces the session identity (not just the slug) for the creating and last-modifying actor, where recorded.
- The model is backward-compatible: existing reflog entries (slug-only) and item frontmatter remain valid with no migration required.
- All documentation and any check built on this model explicitly describes the guarantee as best-effort / recorded-not-signed; no tamper-evidence or enforcement-grade claim is made.
<!-- sq:body:end -->

## User Stories

_Add with `sq feature 125 add-story "As a <role>, I want … so that …"`; track with `sq feature 125 story <n> update --status <Status>`._

<!-- sq:summary -->
| Story | Status | Assignee | Title |
| --- | --- | --- | --- |
| US1 | Done |  | Structured actor record in the reflog (slug + session + parent) |
| US2 | Done |  | Spawn-tree view in sq reflog |
<!-- sq:summary:end -->

<!-- sq:stories -->

<!-- sq:story:US1 -->
### US1 — Structured actor record in the reflog (slug + session + parent)

<!-- sq:story:US1:head -->
**Status:** 🟢 Done
<!-- sq:story:US1:head:end -->

<!-- sq:story:US1:body -->
As any agent or operator, I want the reflog to record a structured actor (slug + optional session ID + optional parent session ID) on every mutating operation, so that I can trace which session performed which operations and reconstruct spawn lineage for forensic review.

**Acceptance:**
- Every `sq` mutating operation records `{slug, session_id, parent_session_id}` in the reflog entry; `session_id` and `parent_session_id` are optional and populated only when the corresponding env vars (`SQUADS_SESSION_ID`, `SQUADS_PARENT_SESSION_ID`) are present at invocation time.
- The session fields are read once at CLI startup from the environment; they are not overridable by any later CLI flag.
- The model is backward-compatible: existing reflog entries (slug-only) remain valid and parse with `session_id=None, parent_session_id=None`.
- `sq <type> <n> show --full` surfaces the session identity for the creating and last-modifying actor, where recorded.
- The guarantee is explicitly best-effort and recorded-not-signed: a self-declared or copied session id is indistinguishable from an authentic one; no tamper-evidence claim is made.
<!-- sq:story:US1:body:end -->

#### Discussion

<!-- sq:story:US1:discussion -->
<!-- sq:story:US1:discussion:end -->
<!-- sq:story:US1:end -->

<!-- sq:story:US2 -->
### US2 — Spawn-tree view in sq reflog

<!-- sq:story:US2:head -->
**Status:** 🟢 Done
<!-- sq:story:US2:head:end -->

<!-- sq:story:US2:body -->
As a squad manager, I want `sq reflog` to render a spawn-tree view, so that I can trace which agent lineage performed which operations and identify structurally non-independent work (e.g. a self-review) by inspecting the recorded spawn edges.

**Acceptance:**
- `sq reflog --tree` (or equivalent flag) renders a nested tree of operations grouped by spawn lineage over the existing time-window filter.
- Operations with no or unknown `parent_session_id` appear as root nodes.
- The tree is reconstructed from the recorded `session_id` / `parent_session_id` edges in the reflog; a missing intermediate session (truncated log) degrades gracefully to a forest rather than an error.
- The 2026-06-15 incident (architect self-reviewing its own code) would produce a visibly non-independent subtree in this view.
- The view makes no tamper-evidence claim: the tree reflects what was recorded, and a deliberately copied session id would appear as a legitimate edge. The display label or docs note the best-effort nature of the lineage data.
<!-- sq:story:US2:body:end -->

#### Discussion

<!-- sq:story:US2:discussion -->
<!-- sq:story:US2:discussion:end -->
<!-- sq:story:US2:end -->
<!-- sq:stories:end -->

## Discussion

<!-- sq:discussion -->
- [2026-06-21T21:34:40Z] Robert Architect:
  - Q1 identity primitive — feasibility read (grounded in Claude Code subagent docs + our _backends/_claude_code). There IS a real session identity handle in the platform: every subagent runs in its own session, and the spawn relationship (parent -> child) is known to the harness, not to sq. BUT sq has no API to read it: the spawn happens in the Task/Agent-tool layer below sq's view (as the epic notes). So in 1.x squads cannot READ a platform-issued session token at sq-invocation time — there is no documented Claude Code surface that injects {session_id, parent_session_id} into the subagent's env for sq to pick up.
  - Q1 cont'd — strongest FEASIBLE mechanism today is the nonce-propagation path already sketched in scope: the spawner (manager/tech-lead) mints a spawn_id+parent_id and passes it to the child via the spawn prompt or an env var, and the child echoes it on every sq op (e.g. --session / SQUADS_SESSION). Its actual guarantee is MERELY RECORDED, not tamper-evident: the nonce is readable and copyable by the agent that holds it, so it just moves the self-declaration problem one hop up the chain (the open question answers itself — a plain env nonce is NOT sufficient for tamper-evidence). Cryptographic/signed identity would need a platform capability that does not exist in 1.x.
  - Q1 verdict — given the epic's stated threat model (accidental/uncontrolled autonomy, NOT malicious agents), a recorded-not-signed lineage is GOOD ENOUGH for forensics: it makes the 2026-06-15 self-review visibly non-independent in a spawn-tree view, which is the actual ask. Frame US1/US2 honestly as 'attributable, tamper-evident-against-accident' — do not over-promise cryptographic identity. Recommend keeping this feature scoped to the reflog/lineage observability win and explicitly deferring signed identity to a future platform-dependent feature.
- [2026-06-22T07:45:02Z] Robert Architect:
  - Design pinned: ADR-158 (Agent identity & spawn lineage). Resolves the 'enforcement mechanism TBD' gap — buildable without re-deciding architecture.
  - Mechanism: spawner mints {session_id, parent_session_id}, child receives via SQUADS_SESSION_ID/SQUADS_PARENT_SESSION_ID env vars, ingested once at the CLI root callback into _actor.py (the single actor chokepoint). Reflog gains two additive optional fields (actor stays a flat slug string — back-compat); items gain optional created/modified session fields. Immediate-parent-only; full chain reconstructed by walking edges. sq reflog --tree and show --full both feasible against this model.
  - Honest guarantee: recorded-not-tamper-evident. Good enough for the accidental-autonomy threat (makes the 2026-06-15 self-review a visibly non-independent subtree); NOT forge-proof. Signed identity deferred to a future platform capability. Unlocks FEAT-122 Slice B lane enforcement as 'catch the accident,' not 'stop the adversary' (consistent with ADR-155's gate).
- [2026-06-22T09:04:56Z] Nina Product:
  - Scope reframe complete (per Catherine's delegation, incorporating Pierre's correction).
  - Title changed to 'Best-effort spawn-lineage recording (untrusted)'. Body, acceptance, and both user story bodies rewritten to reflect that: (1) squads reads identity from the invocation environment if present — it does not generate or propagate it; (2) the guarantee is forensic observability, not verification; (3) no tamper-evidence or 'cannot be self-set' claim survives. ADR-158 linked as related.
  - US1 and US2 survive structurally but drop all verification/tamper-evidence language. US1: record slug + optional session/parent read from env, back-compatible. US2: render spawn tree from recorded edges, roots = no/unknown parent, best-effort label required.
  - Slice B advisory note filed on FEAT-122. @tech-lead: when you scope Slice B, treat it as accident-detection only, not enforcement-grade. @manager: reframe recorded and ready for triage.
<!-- sq:discussion:end -->
