---
id: FEAT-000125
sequence_id: 125
type: feature
title: Real agent identity and spawn lineage
status: Draft
parent: EPIC-000121
author: product-owner
priority: low
refs:
- FEAT-000024
subentities:
- local_id: US1
  title: As any agent or operator, I want the reflog to record a structured actor
    (slug + session ID + parent session ID) so that I can reconstruct the spawn tree
    and distinguish self-declared authorship from verified identity.
  status: Todo
- local_id: US2
  title: As a squad manager, I want sq reflog to render a spawn-tree view so that
    I can trace which agent lineage performed which operations and verify that concurrent
    work was structurally independent.
  status: Todo
created_at: '2026-06-15T11:56:19Z'
updated_at: '2026-06-15T12:00:17Z'
---
<!-- sq:body -->
## Problem

Every mutating operation in squads today records an `actor` — but that actor is a **self-declared
`--as` slug** (e.g. `--as reviewer`) or defaults to `actor=system`. The reflog (FEAT-000024)
captures this field faithfully, but faithful recording of an untrusted input is not the same as
trustworthy identity. The 2026-06-15 incident proved the cost: REV-000118 carried `author: reviewer`
and the reflog recorded it as such, making the self-review indistinguishable from an independent
one at every observable surface (see EPIC-000121).

Beyond authorship, squads is completely blind to **spawn lineage** — the tree of who spawned whom.
Agent spawning happens in the Claude Code / Task-tool layer, below sq's view. The reflog cannot
record that the architect spawned the reviewer, because sq never sees that event.

This is the **observability foundation** the other three candidate features in this epic depend on:

- FEAT-000122 (capability attenuation) needs a verified role identity to enforce capability limits
  against.
- FEAT-000123 (exclusive leases) needs a tamper-evident lease holder rather than another slug.
- FEAT-000124 (separation of duties) needs lineage data to determine whether a review is
  independent.

Without trustworthy identity and lineage, the other three features are still advisory — they
improve the signal, but a compromised lineage can self-declare its way past them.

## Value

A **verifiable agent identity** — a session token or attestation issued at spawn time and
included in every `sq` operation — would give squads a foundation it currently lacks:

- The reflog becomes **forensically meaningful**: the actor field is cryptographically tied to
  the spawning chain, not to what the agent claims.
- `sq check` can reason about lineage, not just declared slugs.
- The manager can see the actual spawn tree, not the team's self-reported version of it.
- The incident on 2026-06-15 would leave a verifiable trace, not a clean audit log.

## Scope (exploratory — not a design commitment)

- A **session identity model**: what constitutes agent identity in a Claude Code-backed system?
  Options range from a signed session token (requires platform support) to a nonce issued by the
  manager at spawn time and propagated through `sq` env/config (no platform support required but
  weaker guarantees).
- **Spawn lineage recording**: the manager issues a `spawn_id` + `parent_id` pair when it spawns
  a sub-agent; the sub-agent includes these in every `sq` operation. Squads records the pair in
  the reflog and on items.
- **Tie-in to FEAT-000024**: the reflog `actor` field is extended from a bare slug to a structured
  `{slug, session_id, parent_id}` object. Backward-compatible: old entries retain their slug-only
  form; new entries carry the full record.
- The `sq reflog` display can render a spawn-tree view.
- Relate this feature to FEAT-000024 (extends it).

## Acceptance (draft — subject to triage)

- Every `sq` mutating operation records a structured actor: `{slug, session_id, parent_session_id}`.
- The session identity is issued at agent-spawn time and cannot be self-set by the agent after the
  fact (enforcement mechanism TBD — depends on design).
- `sq reflog` can display the spawn tree for a time window.
- `sq <type> <n> show --full` surfaces the session identity (not just the slug) for the creating
  and last-modifying actor.
- The model is backward-compatible: existing reflog entries and item frontmatter remain valid.

## Open questions

- What is the right identity primitive in the Claude Code layer? Is there a session handle,
  invocation ID, or similar that squads can read at startup? Or does squads have to generate and
  propagate its own nonce?
- Can identity be made tamper-evident without platform-level signing? A nonce passed via env is
  readable and copyable by the agent — is that sufficient, or does it just move the self-declaration
  problem one level up?
- What is the threat model? We are not defending against malicious agents — we are defending
  against accidental or uncontrolled autonomy. Does that lower bar change the identity design?
- How does identity propagate through indirect spawning chains (manager → tech-lead → dev)? Does
  each hop need to record the full chain, or just the immediate parent?
- Is this feasible in 1.x or does it require a platform capability (e.g. a Claude Code API for
  session metadata) that does not yet exist?
<!-- sq:body:end -->

## User Stories

_Add with `sq feature 125 add-story "As a <role>, I want … so that …"`; track with `sq feature 125 story <n> update --status <Status>`._

<!-- sq:summary -->
| Story | Status | Assignee | Title |
| --- | --- | --- | --- |
| US1 | Todo |  | As any agent or operator, I want the reflog to record a structured actor (slug + session ID + parent session ID) so that I can reconstruct the spawn tree and distinguish self-declared authorship from verified identity. |
| US2 | Todo |  | As a squad manager, I want sq reflog to render a spawn-tree view so that I can trace which agent lineage performed which operations and verify that concurrent work was structurally independent. |
<!-- sq:summary:end -->

<!-- sq:stories -->

<!-- sq:story:US1 -->
### US1 — As any agent or operator, I want the reflog to record a structured actor (slug + session ID + parent session ID) so that I can reconstruct the spawn tree and distinguish self-declared authorship from verified identity.

<!-- sq:story:US1:head -->
**Status:** ⚪ Todo
<!-- sq:story:US1:head:end -->

<!-- sq:story:US1:body -->
_Write the user story (e.g. “As an <role>, I want … so that …”) and its acceptance criteria here — free-form paragraphs or bullet lists._
<!-- sq:story:US1:body:end -->

#### Discussion

<!-- sq:story:US1:discussion -->
<!-- sq:story:US1:discussion:end -->
<!-- sq:story:US1:end -->

<!-- sq:story:US2 -->
### US2 — As a squad manager, I want sq reflog to render a spawn-tree view so that I can trace which agent lineage performed which operations and verify that concurrent work was structurally independent.

<!-- sq:story:US2:head -->
**Status:** ⚪ Todo
<!-- sq:story:US2:head:end -->

<!-- sq:story:US2:body -->
_Write the user story (e.g. “As an <role>, I want … so that …”) and its acceptance criteria here — free-form paragraphs or bullet lists._
<!-- sq:story:US2:body:end -->

#### Discussion

<!-- sq:story:US2:discussion -->
<!-- sq:story:US2:discussion:end -->
<!-- sq:story:US2:end -->
<!-- sq:stories:end -->

## Discussion

<!-- sq:discussion -->
<!-- sq:discussion:end -->
