---
id: FEAT-123
sequence_id: 123
type: feature
title: Exclusive work leases / claims
status: Draft
parent: EPIC-121
author: product-owner
priority: low
refs:
- FEAT-125:depends-on
subentities:
- local_id: US1
  title: Clear conflict error on concurrent item mutation
  status: Todo
- local_id: US2
  title: Manager visibility into all active leases
  status: Todo
created_at: '2026-06-15T11:56:12Z'
updated_at: '2026-06-16T09:52:28Z'
---
<!-- sq:body -->
## Problem

On 2026-06-15, two agent lineages worked the same FEAT-24 files simultaneously — one
the architect's self-spawned implementation agent, one the separately-spawned python-dev — with no
awareness of each other and no conflict detection (see EPIC-121). The `assignee` field on the
item was set, but it is just a metadata field: nothing prevents a second agent from picking up and
editing the same surface.

squads today has no concept of **exclusivity**. An item can have an `assignee`, but that assignee
is a hint for coordination, not a lock. Any agent can read, update, or body-set any item at any
time. In a single-threaded workflow this is fine. In a multi-agent team with concurrent spawning,
it is a latent race condition on every mutating operation.

## Value

If `sq claim` (or `sq <type> <n> status InProgress --claim`) creates an **exclusive lease** — a
time-bounded claim that is visible to other agents and enforced by the index — then:

- a second agent attempting to mutate the same item gets an immediate, clear conflict signal
  rather than silently overwriting,
- the manager can see what is locked and by whom (`sq leases`),
- lease expiry handles the "agent crashed without releasing" case automatically.

## Scope (exploratory — not a design commitment)

- A lease record associated with an item: holder (agent identity or session), acquired timestamp,
  expiry, and the operation that established it.
- Lease acquisition: atomically within the `IndexStore.transaction()` — cannot be set by two
  concurrent callers.
- Lease visibility: surfaced in `sq <type> <n> show`, `sq leases`, and the reflog.
- Conflict signal: a mutation attempt by a non-holder raises a clear `SquadsError` (or returns a
  structured failure in `--json` mode) rather than silently proceeding.
- Lease release: on item close/Done, on explicit `sq release`, or on expiry.
- Tie-in: depends on FEAT-125 (real agent identity) for the lease holder to be meaningful
  rather than another self-declared slug.

## Acceptance (draft — subject to triage)

- `sq claim FEAT-<n>` acquires an exclusive lease; a second `sq claim` on the same item from a
  different identity fails with a structured error.
- Lease holder, timestamp, and expiry are visible in `sq <type> <n> show`.
- A mutating operation (body, status, comment) by a non-holder is rejected while a lease is held.
- Leases expire after a configurable TTL; an expired lease is auto-released on the next access.
- `sq leases` lists all active leases.

## Open questions

- What is the right granularity? Per-item, or per-file-surface (body vs. comment vs. sub-entity)?
  A comment by a non-holder seems legitimate even while the item is leased; a body overwrite does not.
- How does the lease interact with the manager role, which legitimately needs to update items
  across the team? Does the manager get override authority?
- Lease expiry: what is a sensible default TTL for an AI agent session? Seconds? Minutes?
- Does this require FEAT-125 for the lease holder to be tamper-evident, or is a session-local
  token sufficient?
- What happens to leases when `sq repair` runs? Repair is an emergency command; it probably needs
  to clear all leases unconditionally.
<!-- sq:body:end -->

## User Stories

_Add with `sq feature 123 add-story "As a <role>, I want … so that …"`; track with `sq feature 123 story <n> update --status <Status>`._

<!-- sq:summary -->
| Story | Status | Assignee | Title |
| --- | --- | --- | --- |
| US1 | Todo |  | Clear conflict error on concurrent item mutation |
| US2 | Todo |  | Manager visibility into all active leases |
<!-- sq:summary:end -->

<!-- sq:stories -->

<!-- sq:story:US1 -->
### US1 — Clear conflict error on concurrent item mutation

<!-- sq:story:US1:head -->
**Status:** ⚪ Todo
<!-- sq:story:US1:head:end -->

<!-- sq:story:US1:body -->
As any agent, I want to see a clear conflict error when I attempt to mutate an item already claimed by another agent, so that I do not silently overwrite concurrent work.

**Acceptance:** `sq claim <ID>` acquires an exclusive lease atomically within the index transaction; a second `sq claim` on the same item from a different identity fails with a structured error (and a machine-readable code in `--json` mode); body, status, and comment mutations by a non-holder are rejected while a valid lease is held; expired leases are auto-released on next access.
<!-- sq:story:US1:body:end -->

#### Discussion

<!-- sq:story:US1:discussion -->
<!-- sq:story:US1:discussion:end -->
<!-- sq:story:US1:end -->

<!-- sq:story:US2 -->
### US2 — Manager visibility into all active leases

<!-- sq:story:US2:head -->
**Status:** ⚪ Todo
<!-- sq:story:US2:head:end -->

<!-- sq:story:US2:body -->
As a squad manager, I want to list all active leases, so that I can see which items are locked, by whom, and when the lease expires.

**Acceptance:** `sq leases` lists every currently active lease with holder identity, acquired timestamp, and expiry; the list includes the leased item ID and type; output is machine-readable with `--json`; expired leases do not appear.
<!-- sq:story:US2:body:end -->

#### Discussion

<!-- sq:story:US2:discussion -->
<!-- sq:story:US2:discussion:end -->
<!-- sq:story:US2:end -->
<!-- sq:stories:end -->

## Discussion

<!-- sq:discussion -->
<!-- sq:discussion:end -->
