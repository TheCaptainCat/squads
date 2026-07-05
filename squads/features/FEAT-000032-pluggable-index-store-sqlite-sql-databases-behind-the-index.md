---
id: FEAT-32
sequence_id: 32
type: feature
title: 'Pluggable index store: SQLite / SQL databases behind the index'
status: Draft
parent: EPIC-31
author: product-owner
priority: medium
refs:
- FEAT-13
- BUG-22:depends-on
- FEAT-17:depends-on
description: Abstract the index behind a store interface and offer SQLite (and real
  databases via SQLAlchemy) as alternatives to .squads.json — the .md files stay the
  only source of truth
subentities:
- local_id: US1
  title: Real transactions for parallel sq calls without global file lock
  status: Todo
- local_id: US2
  title: Indexed store keeps list/tree/search fast at thousands of items
  status: Todo
- local_id: US3
  title: Store switching via config plus sq repair, reversible both ways
  status: Todo
created_at: '2026-06-10T15:24:10Z'
updated_at: '2026-06-23T10:01:14Z'
---
<!-- sq:body -->
## Problem

The index is a single JSON file guarded by one filelock: every `sq` invocation deserializes the
whole world, mutates, and atomically rewrites it. That's perfect for today's squad sizes and
delightfully debuggable — and it will degrade with scale (large squads re-serialize everything per
write) and with concurrency (a team of agents hammering one lock serializes on it). The storage
engine is also welded in: there is no seam to put anything else behind the index.

## Value

Because of invariant #1 — **frontmatter is the source of truth; the index is a rebuildable
cache** — the index's storage engine is exactly the kind of thing we're allowed to swap freely.
Making that a real seam buys:

- **Concurrency**: real transactions instead of one global file lock, for the many-agents case.
- **Scale**: indexed queries for list/tree/search/backrefs at thousands of items (FEAT-17's
  scale test gives us the benchmark).
- **Optionality**: SQLite first (single file, zero server, fits the local-first spirit); SQLAlchemy
  as the dialect layer so a real database (Postgres, …) is configuration, not a rewrite, for
  whoever needs one squad shared across machines someday.

The durable contract is untouched: `.md` files remain the only thing a squad *is*; any index
backend must be rebuildable from them with `sq repair`.

## Scope

- Extract a **store interface** from today's `IndexStore` (transactions, get/add/delete, counter
  allocation — including its high-water-mark rules, BUG-22) with the JSON file store as the
  default, behaviour-identical implementation.
- A **SQLite store** as the first alternative; SQLAlchemy as the access layer so other databases
  are dialect configuration. Ships as an optional extra (`squads[db]`) if the dependency is heavy
  — design ADR decides (stdlib sqlite3 vs SQLAlchemy-from-day-one).
- **Backend selection in `.squads.toml`**, switching via `sq repair` rebuild into the chosen
  store — the move is reversible in both directions, by construction.
- A **store conformance test suite** run against every implementation (same philosophy as
  FEAT-16's backend conformance suite): identical observable behaviour, including locking
  semantics, counter monotonicity, and crash-recovery via repair.
- Design considerations for the ADR: what's git-friendly (a binary sqlite file in the repo is
  not — maybe the non-JSON stores imply gitignoring the index), file layout under the squad dir,
  and whether `check` should report which store is active.

## Acceptance

- The store interface exists; the JSON store passes the conformance suite with zero behaviour
  change (full existing test suite green, untouched).
- A SQLite-backed squad passes the same conformance suite and the full CLI test matrix.
- `sq repair` rebuilds any configured store from frontmatter alone; switching stores back and
  forth loses nothing.
- Counter integrity rules (never regress) hold in every store.
- The stability contract (FEAT-13) states that the index storage is an implementation detail
  outside the durable promise.
<!-- sq:body:end -->

## User Stories

_Add with `sq feature 32 add-story "As a <role>, I want … so that …"`; track with `sq feature 32 story <n> update --status <Status>`._

<!-- sq:summary -->
| Story | Status | Assignee | Title |
| --- | --- | --- | --- |
| US1 | Todo |  | Real transactions for parallel sq calls without global file lock |
| US2 | Todo |  | Indexed store keeps list/tree/search fast at thousands of items |
| US3 | Todo |  | Store switching via config plus sq repair, reversible both ways |
<!-- sq:summary:end -->

<!-- sq:stories -->

<!-- sq:story:US1 -->
### US1 — Real transactions for parallel sq calls without global file lock

<!-- sq:story:US1:head -->
**Status:** ⚪ Todo
<!-- sq:story:US1:head:end -->

<!-- sq:story:US1:body -->
**Acceptance:** a concurrency test with N parallel writers shows no lost updates and no global-lock serialization on the SQLite store; JSON store behaviour unchanged.

As a team running many agents in parallel, I want the index behind real transactions, so that concurrent sq calls stop serializing on one file lock.
<!-- sq:story:US1:body:end -->

#### Discussion

<!-- sq:story:US1:discussion -->
<!-- sq:story:US1:discussion:end -->
<!-- sq:story:US1:end -->

<!-- sq:story:US2 -->
### US2 — Indexed store keeps list/tree/search fast at thousands of items

<!-- sq:story:US2:head -->
**Status:** ⚪ Todo
<!-- sq:story:US2:head:end -->

<!-- sq:story:US2:body -->
**Acceptance:** on the FEAT-17 ~1000-item fixture, list/tree/search/backrefs on the SQLite store meet the scale test's time bounds.

As an owner of a large squad, I want an indexed store keeping list/tree/search fast at thousands of items, so that scale doesn't degrade the daily loop.
<!-- sq:story:US2:body:end -->

#### Discussion

<!-- sq:story:US2:discussion -->
<!-- sq:story:US2:discussion:end -->
<!-- sq:story:US2:end -->

<!-- sq:story:US3 -->
### US3 — Store switching via config plus sq repair, reversible both ways

<!-- sq:story:US3:head -->
**Status:** ⚪ Todo
<!-- sq:story:US3:head:end -->

<!-- sq:story:US3:body -->
**Acceptance:** store chosen in .squads.toml; sq repair rebuilds the configured store from frontmatter alone; a squad switched json→sqlite→json is byte-equivalent in its .md files and behaviour-equivalent in every command.

As a user choosing a store, I want switching to be config plus sq repair — reversible both ways, so that the .md files remain the only thing I must never lose.
<!-- sq:story:US3:body:end -->

#### Discussion

<!-- sq:story:US3:discussion -->
<!-- sq:story:US3:discussion:end -->
<!-- sq:story:US3:end -->
<!-- sq:stories:end -->

## Discussion

<!-- sq:discussion -->
<!-- sq:discussion:end -->
