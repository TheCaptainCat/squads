---
id: FEAT-321
sequence_id: 321
type: feature
title: The contract (PRD) item type — a living functional source of truth
status: Draft
author: product-owner
refs:
- ADR-320:implements
subentities:
- local_id: US1
  title: As a team, I can create and manage contract items (PRD prefix) like any other
    item type
  status: Todo
- local_id: US2
  title: As a reader, a contract describes what the product does for a user right
    now, from the user's POV
  status: Todo
- local_id: US3
  title: As a team, a feature links the contract it shapes, and stale contracts are
    surfaced when features land
  status: Todo
- local_id: US4
  title: As an agent, the sq-contract skill and .claude/AGENTS.md surface teach and
    expose the new type
  status: Todo
- local_id: US5
  title: As an existing squad, sq migrate up adds the contracts folder and bumps the
    schema to 0.8
  status: Todo
created_at: '2026-07-07T08:33:54Z'
updated_at: '2026-07-07T08:34:43Z'
---
<!-- sq:body -->
# The contract (PRD) item type

Introduce `contract` (ID prefix `PRD`) as a first-class item type: the **living functional source of
truth** for what the product does for a user, right now. It's the functional twin of the ADR set.

## Why

squads has a living, authoritative source of truth for the *technical* view — the ADR set
(`decision` type). It has none for the *functional / user* view: to answer "what does this product
do for a user, right now?" you must replay the whole feature history and mentally apply every later
override. The `contract` fills that gap.

> **`decision` (ADR) = the technical contract · `contract` (PRD) = the functional contract with the user.**

## The core model: living vs historic

- **Features/epics are historic** — point-in-time records that later work can supersede. A feature is
  the *diff + the rationale* (the audit trail).
- **A contract is living** — the accumulated current functional state, rewritten in place as the
  product evolves, from the user's point of view (the *winner*).
- **Maintenance discipline is load-bearing:** landing a feature isn't Done until it has updated the
  `contract` slice it touches. A living source of truth that isn't kept current *lies*.
- **A collection, not a monolith:** one `contract` item per capability / user-facing area, so a
  feature updates just its slice and ownership/merge stay sane.

## Shape

The architecture is settled in the accompanying decision (built-in reserved type on the existing
config-driven engine; lifecycle **Draft → Active → Superseded (+ Deprecated)**; one item per
capability area, no sub-entities; features link the contract they shape by a forward `implements`
ref; DoD currency enforced by an *advisory* `sq check` rule, not a hard gate; managed `sq-contract`
skill/pointer/playbook/template; schema bump `0.7 → 0.8` with a folder-creating migration). This
feature builds that.

The `contract` body describes **product behaviour only** — never its own workflow state (frontmatter
`status:` is the single source of truth).

## Note

Once the type exists, features that shape a capability should carry an `implements` ref to the
relevant `contract` item(s). squads is itself a squad-managed repo, so squads gets its own contracts
— the truest test of whether the artifact earns its keep.
<!-- sq:body:end -->

## User Stories

_Add with `sq feature 321 add-story "As a <role>, I want … so that …"`; track with `sq feature 321 story <n> update --status <Status>`._

<!-- sq:summary -->
| Story | Status | Assignee | Title |
| --- | --- | --- | --- |
| US1 | Todo |  | As a team, I can create and manage contract items (PRD prefix) like any other item type |
| US2 | Todo |  | As a reader, a contract describes what the product does for a user right now, from the user's POV |
| US3 | Todo |  | As a team, a feature links the contract it shapes, and stale contracts are surfaced when features land |
| US4 | Todo |  | As an agent, the sq-contract skill and .claude/AGENTS.md surface teach and expose the new type |
| US5 | Todo |  | As an existing squad, sq migrate up adds the contracts folder and bumps the schema to 0.8 |
<!-- sq:summary:end -->

<!-- sq:stories -->

<!-- sq:story:US1 -->
### US1 — As a team, I can create and manage contract items (PRD prefix) like any other item type

<!-- sq:story:US1:head -->
**Status:** ⚪ Todo
<!-- sq:story:US1:head:end -->

<!-- sq:story:US1:body -->
As a team, I want to create and manage `contract` items (PRD prefix) like any other item type so the product's functional truth has a first-class home.

**Acceptance**
- `sq create contract` (aliases `prd`/`c`) creates a `PRD`-prefixed item under a `contracts/` folder.
- The type has an auto-generated `sq contract` CLI group, like the other work types.
- Lifecycle is Draft -> Active -> Superseded (+ Deprecated), reusing existing statuses; no required parent.
<!-- sq:story:US1:body:end -->

#### Discussion

<!-- sq:story:US1:discussion -->
<!-- sq:story:US1:discussion:end -->
<!-- sq:story:US1:end -->

<!-- sq:story:US2 -->
### US2 — As a reader, a contract describes what the product does for a user right now, from the user's POV

<!-- sq:story:US2:head -->
**Status:** ⚪ Todo
<!-- sq:story:US2:head:end -->

<!-- sq:story:US2:body -->
As a reader, I want a contract to describe what the product does for a user right now, from the user's point of view, so it is the current functional truth.

**Acceptance**
- The body convention is functional/user-facing behaviour — not architecture (that is the ADR set) and not workflow-state prose.
- One contract per capability / user-facing area (a collection), with ordinary markdown headings inside; no sub-entities.
- A dedicated item template steers the author toward functional-behaviour prose.
<!-- sq:story:US2:body:end -->

#### Discussion

<!-- sq:story:US2:discussion -->
<!-- sq:story:US2:discussion:end -->
<!-- sq:story:US2:end -->

<!-- sq:story:US3 -->
### US3 — As a team, a feature links the contract it shapes, and stale contracts are surfaced when features land

<!-- sq:story:US3:head -->
**Status:** ⚪ Todo
<!-- sq:story:US3:head:end -->

<!-- sq:story:US3:body -->
As a team, I want a feature to link the contract it shapes and stale contracts surfaced when features land, so the living truth stays current.

**Acceptance**
- A feature links the contract it delivers via a forward `implements` ref (target type `contract`); the contract's show view lists the shaping features by backref inversion.
- `contract` declares a `supersedes` rule so a replacement contract links the one it supersedes.
- An advisory (warn-level, non-blocking) `sq check` rule flags a feature reaching InReview/Done with no `implements` edge to a contract.
<!-- sq:story:US3:body:end -->

#### Discussion

<!-- sq:story:US3:discussion -->
<!-- sq:story:US3:discussion:end -->
<!-- sq:story:US3:end -->

<!-- sq:story:US4 -->
### US4 — As an agent, the sq-contract skill and .claude/AGENTS.md surface teach and expose the new type

<!-- sq:story:US4:head -->
**Status:** ⚪ Todo
<!-- sq:story:US4:head:end -->

<!-- sq:story:US4:body -->
As an agent, I want the sq-contract skill and the .claude/AGENTS.md surface to teach and expose the new type so I know how to work with contracts.

**Acceptance**
- A managed `sq-contract` skill (real body under squads/agents/skills, thin `.claude` pointer) is generated, driven by new playbook entries (product-owner authors/keeps current; tech-lead and devs update touched slices; architect watches cross-contract consistency).
- The generated agent-facing files are stamped as `sq sync`-regenerated.
- On-disk `.claude`/AGENTS.md artifacts are verified against roles/ops for BOTH fresh init AND migrate.
<!-- sq:story:US4:body:end -->

#### Discussion

<!-- sq:story:US4:discussion -->
<!-- sq:story:US4:discussion:end -->
<!-- sq:story:US4:end -->

<!-- sq:story:US5 -->
### US5 — As an existing squad, sq migrate up adds the contracts folder and bumps the schema to 0.8

<!-- sq:story:US5:head -->
**Status:** ⚪ Todo
<!-- sq:story:US5:head:end -->

<!-- sq:story:US5:body -->
As an existing squad, I want `sq migrate up` to add the contracts folder and bump the schema so the new type appears cleanly.

**Acceptance**
- Schema bumps 0.7 -> 0.8; the migration creates the `contracts/` folder and regenerates the managed skills/pointers/CLAUDE.md and AGENTS.md regions so the sq-contract surface appears.
- No existing item data is rewritten.
- A manual runbook entry tells the adopting squad the functional-contract type now exists (and may seed initial contracts for current capabilities).
<!-- sq:story:US5:body:end -->

#### Discussion

<!-- sq:story:US5:discussion -->
<!-- sq:story:US5:discussion:end -->
<!-- sq:story:US5:end -->
<!-- sq:stories:end -->

## Discussion

<!-- sq:discussion -->
<!-- sq:discussion:end -->
