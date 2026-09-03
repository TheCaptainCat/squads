---
id: FEAT-321
sequence_id: 321
type: feature
title: The contract (PRD) item type — a living functional source of truth
status: Done
author: product-owner
refs:
- ADR-320:implements
- MILE-836:targets
- PRD-859:implements
subentities:
- local_id: US1
  title: As a team, I can create and manage contract items (PRD prefix) like any other
    item type
  status: Done
- local_id: US2
  title: As a reader, a contract describes what the product does for a user right
    now, from the user's POV
  status: Done
- local_id: US3
  title: As a team, a feature links the contract it shapes, and stale contracts are
    surfaced when features land
  status: Done
- local_id: US4
  title: As an agent, the sq-contract skill and .claude/AGENTS.md surface teach and
    expose the new type
  status: Done
- local_id: US5
  title: sq migrate up adds the contracts folder in the shared 0.14 bump
  status: Done
created_at: '2026-07-07T08:33:54Z'
updated_at: '2026-09-01T13:49:19Z'
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
  feature updates just its slice and ownership/merge stay sane. Partitioning is the product owner's
  editorial judgement — nothing structurally enforces the capability-area boundary, and the position
  is revisited only if it goes wrong in practice.

## Shape

The architecture is settled in the accompanying decision (bundled item type on the existing
config-driven engine — declared in the shipped spec, not one of the three reserved names; lifecycle
**Draft → Active → Superseded (+ Deprecated)**; one item per capability area, no sub-entities;
features link the contract they shape by a forward `implements` ref, reused rather than a dedicated
kind and not resting on any closed-vocabulary cost, disambiguated by the target being a `contract`;
DoD currency enforced by an *advisory* `sq check` rule, not a hard gate; managed `sq-contract`
skill/pointer/playbook/template; shares the single `0.11 → 0.14` schema bump and migration runner
with the milestone type, FEAT-693 — one bump for both new types, not two). This feature builds that.

The `contract` body describes **product behaviour only** — never its own workflow state (frontmatter
`status:` is the single source of truth).

## Note

Once the type exists, features that shape a capability should carry an `implements` ref to the
relevant `contract` item(s). squads is itself a squad-managed repo, so squads gets its own contracts
— the truest test of whether the artifact earns its keep.
<!-- sq:body:end -->

## User Stories

_Add with `sq feature 321 add-story "As a <role>, I want … so that …"`; track with `sq feature 321 story <n> update --status <Status>`._

<!-- sq:stories -->

<!-- sq:story:US1 -->
### US1 — As a team, I can create and manage contract items (PRD prefix) like any other item type

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

<!-- sq:story:US2:body -->
As a reader, I want a contract to describe what the product does for a user right now, from the
user's point of view, so it is the current functional truth.

**Acceptance**
- The body convention is functional/user-facing behaviour — not architecture (that is the ADR set)
  and not workflow-state prose.
- One contract per capability / user-facing area (a collection), with ordinary markdown headings
  inside; no sub-entities. Partitioning is the product owner's judgement call, not a structural
  rule — no guard enforces "one capability per contract" either way.
- A dedicated item template steers the author toward functional-behaviour prose.
<!-- sq:story:US2:body:end -->

#### Discussion

<!-- sq:story:US2:discussion -->
<!-- sq:story:US2:discussion:end -->
<!-- sq:story:US2:end -->

<!-- sq:story:US3 -->
### US3 — As a team, a feature links the contract it shapes, and stale contracts are surfaced when features land

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

<!-- sq:story:US4:body -->
As an agent, I want the sq-contract skill and the .claude/AGENTS.md surface to teach and expose the
new type so I know how to work with contracts.

**Acceptance**
- A managed `sq-contract` skill (real body under squads/agents/skills, thin `.claude` pointer) is
  generated, driven by new playbook entries (product-owner authors/keeps current; tech-lead and devs
  update touched slices; architect watches cross-contract consistency). The pointer names the
  command that renders the definition (`sq skill sq-contract show`), never a local file path.
- The generated agent-facing files are stamped as `sq sync`-regenerated.
- On-disk `.claude`/AGENTS.md artifacts are diffed against roles/ops for BOTH fresh init AND
  migrate. `sq check` already verifies per-entry pointer presence and currency for every live
  roster entry (shipped separately); this feature's own diff confirms the `sq-contract` pointer
  passes that gate from day one.
<!-- sq:story:US4:body:end -->

#### Discussion

<!-- sq:story:US4:discussion -->
<!-- sq:story:US4:discussion:end -->
<!-- sq:story:US4:end -->

<!-- sq:story:US5 -->
### US5 — sq migrate up adds the contracts folder in the shared 0.14 bump

<!-- sq:story:US5:body -->
As an existing squad, I want `sq migrate up` to add the contracts folder and bump the schema so the
new type appears cleanly.

**Acceptance**
- Schema bumps `0.11 -> 0.14` — one shared bump and one shared migration runner carrying both the
  `contract` and the milestone type (FEAT-693) into the same release, not a bump of its own; the
  migration creates the `contracts/` folder and regenerates the managed skills/pointers/CLAUDE.md
  and AGENTS.md regions so the sq-contract surface appears.
- No existing item data is rewritten.
- A manual runbook entry tells the adopting squad the functional-contract type now exists (and may
  seed initial contracts for current capabilities).
<!-- sq:story:US5:body:end -->

#### Discussion

<!-- sq:story:US5:discussion -->
<!-- sq:story:US5:discussion:end -->
<!-- sq:story:US5:end -->
<!-- sq:stories:end -->

## Discussion

<!-- sq:discussion -->
- [2026-07-29T09:37:07Z] Pierre Chat:
  - Scheduled for 0.13.
- [2026-07-30T07:57:46Z] Pierre Chat:
  - Last in 0.13, after FEAT-691, FEAT-642 and FEAT-644 — it is the largest of the three and takes whatever runway remains.
- [2026-08-03T07:49:32Z] Pierre Chat:
  - Out of 0.13. The release is already substantial — the spec-driven customization epic grew a thirty-finding consumer sweep on top of its four features. A new item type is additive scope with no dependency forcing it into this release, so it moves out rather than extending the cut.
- [2026-08-24T18:02:26Z] Pierre Chat:
  - Scoped into 0.14, and coupled to FEAT-693: both new item types share one schema bump and one migration runner, so the two features land in the same release.
- [2026-08-26T13:20:41Z] Nina Product:
  - Refreshed against ADR-320 (now Accepted, carrying the operator's four rulings) ahead of the
    breakdown.
    
    - Schema corrected everywhere: `0.7 → 0.8` was stale (that pair never shipped as a pair) —
      now `0.11 → 0.14`, one shared bump and one shared migration runner with the milestone type
      (FEAT-693; TASK-813 already tracks the runner itself, parented under FEAT-693 with a
      depends-on ref to this feature). US5's title and acceptance, and the Shape section, all
      now say this explicitly rather than a bump "of its own".
    - Folded in the four operator rulings: enforcement advisory/warn-only (already correct, left
      as-is); ref kind is `implements` reused, disambiguated by target type, not resting on any
      closed-vocabulary argument (that argument is gone — ADR-775 made ref kinds declared
      vocabulary); no structural guard on capability-area partitioning — stated explicitly now in
      the core model and in US2, instead of silently assumed.
    - "built-in reserved type" corrected to "bundled item type, not one of the three reserved
      names" — `contract` ships in the bundled spec like any other declared type; it isn't
      role/skill/operator-class reserved.
    - US4's pointer acceptance corrected: FEAT-792 (Done) shipped presence/currency checking for
      per-entry pointers, so this is now "confirm the gate is passed" rather than "verify by
      hand" — and the pointer itself names a command per ADR-781, never a local path.
    
    No reauthor needed — the type's shape (records category, no sub-entities, Draft → Active →
    Superseded lifecycle, forward `implements` ref) was already correct and matches ADR-320 as
    accepted.
- [2026-08-26T13:40:35Z] Olivia Lead:
  - - Broke FEAT-321 into one task, TASK-832 — the type declaration, its lifecycle, the item template, the two edges, the advisory check and the generated `sq-contract` surface are one coherent surface with one owner, so they are five subtasks rather than five tasks. US5 is deliberately absent: the folder creation and schema bump on an existing squad belong to TASK-813, the release's one shared runner, and authoring a second is what was ruled against.
    - Named the validator ADR-320 §C left unnamed: `ref_rule_target_present`, selected as `validators = ["ref_rule_target_present:contract"]` on `[items.feature]`, with the param naming the target item **type** and the kind read from the declaring type's own `ref_rules`. Chosen against the catalog's convention, not invented — the fourteen existing entries name subject-plus-condition (`parent_present`, `agent_registered`, `subentity_body_written`), and where the subject is spec-resolved they name it generically (`subentity_title_max` says `subentity`, not `story`). A `contract_*` name would bake a bundled type into the closed catalog of a project whose direction is that only role/skill/operator are reserved.
    - One thing I did NOT settle, raised in ST4 rather than invented. §C says the finding fires at `InReview` **or** `Done`. Those cannot be separated through declared vocabulary: `InReview` declares `role = "active"` — the same role as `InProgress`, `ChangesRequested` and `Active` — while `Done` declares `role = "done"` (verified in the bundled spec). I specified building against the `done` role, mirroring `_supersedes_incoming`, which compares `ctx.spec.status_role(...)` against a role and never a status spelling. Binding to `active` instead would warn on every feature merely in progress. @architect either §C narrows to the settled role, or a status role distinguishing "under review" from "in progress" is introduced — nothing else in the task turns on which.
    - A consequence worth knowing before this lands, and the dev is told to measure it rather than soften it: this repo holds dozens of `Done` features with no contract edge, because the type does not exist yet. Every one of them will produce a warn finding the day the validator ships. ST4 requires the count measured on our own corpus and reported, and forbids a suppression or grandfather clause — the honest options are seeding this repo's own contracts or accepting the number, and that is @op-pierre's call with a real figure in hand.
- [2026-09-01T07:37:20Z] Catherine Manager:
  - US5 was delivered by the shared migration runner, which is parented under the derived-views feature because that is where the runner lives; the runner creates both new type folders and cannot be closed by delivering one half.
<!-- sq:discussion:end -->
