---
id: FEAT-000018
sequence_id: 18
type: feature
title: Backfill architecture documentation into squads
status: Ready
parent: EPIC-000012
author: product-owner
priority: medium
description: Put the architecture and the pre-bootstrap design decisions on the record
  as sq guides and ADRs, since the project started untracked
subentities:
- local_id: US1
  title: As a new agent or contributor, I want an architecture guide readable through
    sq, so that I understand the system's shape without spelunking through git history
  status: Todo
- local_id: US2
  title: As an architect, I want the standing design decisions on record as ADRs,
    so that future work can cite, build on, or formally revisit them
  status: Todo
- local_id: US3
  title: As a team member working an item, I want guides and ADRs cross-linked by
    refs, so that the relevant context travels with the work
  status: Todo
created_at: '2026-06-10T12:49:50Z'
updated_at: '2026-06-11T07:54:54Z'
---
<!-- sq:body -->
## Problem

squads was built before it tracked itself: the architecture and every major design call — the
global ID counter, frontmatter as the source of truth, forward-only refs, marker-safe editing,
the pluggable backend ABC, the schema-version scheme — were made off the record. Today they live
only in CLAUDE.md prose, the plan document and git history. New agents and contributors have no
sq-native way to discover *why* the system is shaped the way it is, and future work has nothing
to link against when it touches one of those decisions.

## Value

This is dogfooding with a payoff: the team's own coordination layer becomes the place where its
architecture is explained and its decisions are citable. Future items can `ref` the ADR they
build on or revisit (the stability-contract and hardening features already call for new ADRs —
those should land in a record that also holds the old ones, not start one from scratch). It also
exercises the guide and decision item types for real, before 1.0 freezes how they behave.

## Scope

- **Architecture guide(s)** (`sq create guide`) covering the system's shape: the
  `_cli → _services → (index, backends, rendering)` layering, the data model
  (items / sub-entities / index), and the rendering + marker mechanism.
- **Retroactive ADRs** (`sq create decision`) for the standing calls, each stating its context
  and consequences honestly as a decision already in force — at minimum: frontmatter as source of
  truth with a rebuildable index, the single global ID counter, forward-edges-only refs,
  marker-safe editing, pluggable backends with `.claude/` as pointers, and the 0.x schema-version
  scheme.
- Cross-link everything (`ref add … --kind related`) so the guides cite the ADRs and the epic's
  other features can link to them.

This is documentation of what *is*, not a redesign — if writing an ADR exposes a decision worth
revisiting, that's a new item, not scope creep here.

## Acceptance

- An architecture guide exists as a guide item and is discoverable via `sq search`.
- Each standing decision listed above has its own ADR item with context and consequences.
- Guides and ADRs are cross-linked, and the new ADRs called for elsewhere in this epic
  (post-1.0 schema_version, Python floor) can attach to the same record.
- `sq check` stays clean.
<!-- sq:body:end -->

## User Stories

_Add with `sq feature 18 add-story "As a <role>, I want … so that …"`; track with `sq feature 18 story <n> update --status <Status>`._

<!-- sq:summary -->
| Story | Status | Assignee | Title |
| --- | --- | --- | --- |
| US1 | Todo |  | As a new agent or contributor, I want an architecture guide readable through sq, so that I understand the system's shape without spelunking through git history |
| US2 | Todo |  | As an architect, I want the standing design decisions on record as ADRs, so that future work can cite, build on, or formally revisit them |
| US3 | Todo |  | As a team member working an item, I want guides and ADRs cross-linked by refs, so that the relevant context travels with the work |
<!-- sq:summary:end -->

<!-- sq:stories -->

<!-- sq:story:US1 -->
### US1 — As a new agent or contributor, I want an architecture guide readable through sq, so that I understand the system's shape without spelunking through git history

<!-- sq:story:US1:head -->
**Status:** ⚪ Todo
<!-- sq:story:US1:head:end -->

<!-- sq:story:US1:body -->
**Acceptance:** a guide item covers the layering (_cli → _services → index/backends/rendering), the data model (items, sub-entities, index) and the marker mechanism; `sq search architecture` finds it.
<!-- sq:story:US1:body:end -->

#### Discussion

<!-- sq:story:US1:discussion -->
<!-- sq:story:US1:discussion:end -->
<!-- sq:story:US1:end -->

<!-- sq:story:US2 -->
### US2 — As an architect, I want the standing design decisions on record as ADRs, so that future work can cite, build on, or formally revisit them

<!-- sq:story:US2:head -->
**Status:** ⚪ Todo
<!-- sq:story:US2:head:end -->

<!-- sq:story:US2:body -->
**Acceptance:** each standing call (frontmatter as source of truth, global counter, forward-only refs, marker-safe edits, pluggable backends, schema-version scheme) has its own ADR item written as a decision in force, with context and consequences.
<!-- sq:story:US2:body:end -->

#### Discussion

<!-- sq:story:US2:discussion -->
<!-- sq:story:US2:discussion:end -->
<!-- sq:story:US2:end -->

<!-- sq:story:US3 -->
### US3 — As a team member working an item, I want guides and ADRs cross-linked by refs, so that the relevant context travels with the work

<!-- sq:story:US3:head -->
**Status:** ⚪ Todo
<!-- sq:story:US3:head:end -->

<!-- sq:story:US3:body -->
**Acceptance:** guides ref the ADRs they explain and vice versa (`--kind related`); the schema_version and Python-floor ADRs called for by FEAT-000013 / FEAT-000017 can join the same record.
<!-- sq:story:US3:body:end -->

#### Discussion

<!-- sq:story:US3:discussion -->
<!-- sq:story:US3:discussion:end -->
<!-- sq:story:US3:end -->
<!-- sq:stories:end -->

## Discussion

<!-- sq:discussion -->
<!-- sq:discussion:end -->
