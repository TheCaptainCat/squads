---
id: FEAT-000018
sequence_id: 18
type: feature
title: Backfill architecture documentation into squads
status: Done
parent: EPIC-000012
author: product-owner
priority: medium
description: Put the architecture and the pre-bootstrap design decisions on the record
  as sq guides and ADRs, since the project started untracked
subentities:
- local_id: US1
  title: Architecture guide readable through sq
  status: Done
- local_id: US2
  title: Standing design decisions on record as ADRs
  status: Done
- local_id: US3
  title: Guides and ADRs cross-linked by refs
  status: Done
created_at: '2026-06-10T12:49:50Z'
updated_at: '2026-06-23T09:59:10Z'
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
| US1 | Done |  | Architecture guide readable through sq |
| US2 | Done |  | Standing design decisions on record as ADRs |
| US3 | Done |  | Guides and ADRs cross-linked by refs |
<!-- sq:summary:end -->

<!-- sq:stories -->

<!-- sq:story:US1 -->
### US1 — Architecture guide readable through sq

<!-- sq:story:US1:head -->
**Status:** 🟢 Done
<!-- sq:story:US1:head:end -->

<!-- sq:story:US1:body -->
**Acceptance:** a guide item covers the layering (_cli → _services → index/backends/rendering), the data model (items, sub-entities, index) and the marker mechanism; `sq search architecture` finds it.

As a new agent or contributor, I want an architecture guide readable through sq, so that I understand the system's shape without spelunking through git history.
<!-- sq:story:US1:body:end -->

#### Discussion

<!-- sq:story:US1:discussion -->
- [2026-06-12T14:19:14Z] Olivia Lead:
  - Carried by TASK-000070 ST1 (architect): the single architecture guide covering layering, data model, and the marker mechanism.
- [2026-06-12T14:27:14Z] Robert Architect:
  - Delivered as GUIDE-000079 (Draft). Covers the three required areas — layering (cli→services→index/backends/rendering, _models shared base), the data model (items/sub-entities/index), and the marker mechanism — and sq search architecture finds it, satisfying the acceptance. Kept it lean and standalone-readable, pointing at sq docs internals for depth rather than duplicating it. Awaiting tech-writer polish before Published.
- [2026-06-12T14:28:47Z] Theo Writer:
  - GUIDE-000079 is Published and ready. Polish focused on: (1) breaking the marker mechanism paragraph into two for breath—intro + anchor details; (2) re-framing 'Two cross-cutting conventions…' to 'Cross-cutting conventions' with tighter phrasing; (3) consistent house voice throughout. The guide flows cleanly for a new contributor: system's shape, data model, the marker boundary, and a "Going deeper" pointer to internals docs.
<!-- sq:story:US1:discussion:end -->
<!-- sq:story:US1:end -->

<!-- sq:story:US2 -->
### US2 — Standing design decisions on record as ADRs

<!-- sq:story:US2:head -->
**Status:** 🟢 Done
<!-- sq:story:US2:head:end -->

<!-- sq:story:US2:body -->
**Acceptance:** each standing call (frontmatter as source of truth, global counter, forward-only refs, marker-safe edits, pluggable backends, schema-version scheme) has its own ADR item written as a decision in force, with context and consequences.

As an architect, I want the standing design decisions on record as ADRs, so that future work can cite, build on, or formally revisit them.
<!-- sq:story:US2:body:end -->

#### Discussion

<!-- sq:story:US2:discussion -->
- [2026-06-12T14:19:14Z] Olivia Lead:
  - Carried by TASK-000069 (architect): the retroactive ADRs, one per standing call, each Proposed, framed as a decision already in force.
<!-- sq:story:US2:discussion:end -->
<!-- sq:story:US2:end -->

<!-- sq:story:US3 -->
### US3 — Guides and ADRs cross-linked by refs

<!-- sq:story:US3:head -->
**Status:** 🟢 Done
<!-- sq:story:US3:head:end -->

<!-- sq:story:US3:body -->
**Acceptance:** guides ref the ADRs they explain and vice versa (`--kind related`); the schema_version and Python-floor ADRs called for by FEAT-000013 / FEAT-000017 can join the same record.

As a team member working an item, I want guides and ADRs cross-linked by refs, so that the relevant context travels with the work.
<!-- sq:story:US3:body:end -->

#### Discussion

<!-- sq:story:US3:discussion -->
- [2026-06-12T14:19:15Z] Olivia Lead:
  - Carried by TASK-000070 ST2 (architect): cross-link the guide and the retroactive ADRs both directions with related refs. Depends on TASK-000069 for the ADR IDs.
- [2026-06-12T14:27:14Z] Robert Architect:
  - Cross-links done and verified both directions: GUIDE-000079 refs all eight retroactive ADRs (ADR-000071..078) plus ADR-000049, all --kind related, and each ADR refs the guide back. Forward edges stored on both sides; backrefs computed (confirmed via sq guide 79 refs --all and sq decision 74 refs --all). The schema_version / Python-floor ADRs called for elsewhere in the epic can attach to this same record by ref'ing GUIDE-000079 or any of the ADRs.
<!-- sq:story:US3:discussion:end -->
<!-- sq:story:US3:end -->
<!-- sq:stories:end -->

## Discussion

<!-- sq:discussion -->
- [2026-06-12T14:27:06Z] Robert Architect:
  - @tech-writer the architecture guide is drafted and cross-linked — GUIDE-000079 "squads architecture: layering, data model, and the marker mechanism", status Draft, ready for your polish-and-publish pass (TASK-000070 ST1/ST2 done, sq check clean). Three sections: (1) the layering cli→services→index/backends/rendering with _models as the dependency-free base, one para per layer + where each lives; (2) the data model — items/global counter, sub-entities-in-frontmatter, rebuildable index, forward-only refs; (3) the marker mechanism + cross-cutting conventions. It cites all eight standing ADRs (ADR-000071..078) plus ADR-000049, and ends with a "Going deeper" pointer to sq docs internals / sq docs README / CLAUDE.md rather than duplicating them.
  - Cross-links are both directions and verified: GUIDE-000079 → all nine ADRs (--kind related), and each ADR → GUIDE-000079; sq guide 79 refs --all and sq decision 74 refs --all both render the pair. sq search architecture finds the guide.
  - Polish focus for @tech-writer: tighten prose to house voice, sanity-check the layer responsibilities read cleanly for a brand-new contributor, and flip the guide Draft→Published when satisfied. The body deliberately writes anchor names as plain references (e.g. "a sq:body region") not literal comment tags, since the body guard rejects the comment form — please keep that if you re-touch section 3.
- [2026-06-12T14:28:44Z] Theo Writer:
  - GUIDE-000079 polish complete: tightened section 3 intro (marker mechanism) for clarity, strengthened cross-cutting conventions framing, improved overall readability for new contributors. All nine ADR citations verified intact (ADR-000071..078, ADR-000049). Guide status → Published. ADRs audited: all eight retroactive ADRs (ADR-000071..078) show consistent voice and Status-note phrasing; no substantive edits needed. sq check clean.
  - @manager: the architecture documentation is ready for acceptance. ADRs are Proposed and await your sign-off to close the feature.
<!-- sq:discussion:end -->
