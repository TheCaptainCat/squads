---
id: ADR-541
sequence_id: 541
type: decision
title: 'Type categories + pluggable validators: closed catalog, open assignment'
status: Accepted
author: architect
refs:
- EPIC-538
- EPIC-540
- ADR-696
- ADR-320
- ADR-982
created_at: '2026-07-21T16:26:15Z'
updated_at: '2026-10-25T21:34:33Z'
---
<!-- sq:body -->
## Context

The generic-vocabulary engine lets every work-item type be dropped, renamed or re-prefixed, which
leaves two structural questions for spec-driven customization (EPIC-538) and pluggable validators
(EPIC-540):

1. A single "roster or not" boolean conflates two meanings of "not roster": *creatable and
   trackable* (work items **and** durable records) versus *burn-down work only*. Behaviour that
   should differ between records and work (a record takes no parent; work is driven to Done) has
   nowhere to attach.
2. The constraints `sq check` and the create/update gate enforce need a home that a type can opt
   into and an adopter can compose for a custom type, instead of hardcoded check methods reading
   half-declarative parent fields.

This decision pins the two axes and how they compose.

## Decision

### Axis A — the type `category`

`ItemSpec.category` names one of a **hard-coded, closed catalog** of three categories
(`Literal["roster", "work", "records"]`, default `work`). The catalog is defined in code, carries
fixed behaviour, and is **not part of the override surface**: an adopter cannot create, rename or
redefine a category. Vocabulary lives in the spec, behaviour lives in code, and a category *is*
behaviour. A type declares its category; a custom type picks one of the three to inherit its
behaviour.

- `roster` — `role`, `skill`, `operator`. Registry entities: slug identity, backend pointer files
  written on sync, their own group in the UI trees. Membership is closed in both directions (the
  floor below).
- `work` — `epic`, `feature`, `task`, `bug`, `review`. Burn-down items: assigned, driven to a
  Done-like status, a parent constraint per type, counted in `blocked`/`mine`/workload, the work
  group in the trees.
- `records` — `decision` (ADR), `contract` (PRD), `milestone` and `guide`. Durable references with
  their own lifecycles, never burned down to Done, not assigned, their own group in the trees, and
  they **take no parent**: a record relates to work through refs, never hierarchy.

`guide` is a `records` type and `review` a `work` type (operator directive). `contract` is a
`records` type; ADR-320 owns the type itself. Orthogonal capability fields (`parent_required`,
`subentity_kind`, `fields`) stay their own fields. The field is named `category` because `type`
would collide with the item type's own name.

#### The type-axis floor: the roster type keys are locked

sq binds the three roster types by their literal **type key** (`ROSTER_ROLE`, `ROSTER_SKILL`,
`ROSTER_OPERATOR`). The floor is drawn on key identity and category membership: an override may not
add a roster type, drop one (including through `selected`), or rename one, and `category` may not
move a type into or out of `roster`. Any breach is refused at load with a clean `SquadsError`.
Every non-roster type is ordinary, droppable, renamable, re-prefixable vocabulary.

A roster type's **other fields are ordinary, validated customisation**: its `lifecycle` above all,
and its prefix, folder, labels and order, subject to the same uniqueness, referential-integrity and
live-item checks every type faces, plus the lifecycle floor a roster-bound machine owes (ADR-696
§3–§4, the governing statement on the field axis). The engine binds the roster by key, never by a
roster type's prefix or folder, so the lock covers exactly the identity the engine depends on.

Because no roster key rename is ever permitted, the literal-key bindings are correct as they are,
and no separate name-independent identity marker for roster types exists or is needed.

#### Category reassignment of a built-in

An override **may** reassign a built-in type among the non-roster categories (`work` ↔ `records`),
for example `review` to `records` or `guide` to `work`. The guardrail is validation, not
prohibition: a reassignment that yields an inconsistent spec (a type moved to `records` while it
still declares a parent) fails load validation. Merely unusual but valid reassignments are the
adopter's call.

### Axis B — the validator model

`sq check` and the create/update gate run a **declarative, pluggable validator framework** with
the same closed-catalog / open-assignment boundary as categories:

- **Closed catalog, open assignment.** Validator logic is hard-coded in squads; there is no
  adopter-supplied validator code and no `eval`. What is spec-declared is *which* validators a type
  runs and their parameters. The name catalogs live in `_workflow/_validator_names.py`
  (`VALIDATOR_NAMES`, `SQUAD_GLOBAL_VALIDATOR_NAMES`) and the checks in
  `_services/_validators.py`, which asserts at import that the two agree. A `validators` entry
  naming a validator outside the catalog fails closed at load.
- **Rule data stays structured; validators read it.** Rule data stays in structured spec fields
  (`parents`, `parent_required`, ref rules, declared thresholds). A validator is the check that
  reads them; a parameter carries only what no structured field holds.
- **One engine, two call sites.** `sq check` runs it in *report* mode (every issue, levels
  preserved); create/update runs it in *abort* mode, refusing on an error-level issue. The rule
  logic is written once.

ADR-864 owns where each member is placed (always on, on by default for a category, or opt-in),
the level a selection carries (`name@level`, with a declared floor where the level is
load-bearing) and the declared thresholds; ADR-982 owns how a squad selects squad-global members.

#### Two validator classes: per-item and squad-global

- **Per-item validators** run once per item, given the item and the spec (parent eligibility,
  status validity, ref resolution, sub-entity rules, and so on). A type's category bundle plus its
  own `validators` additions select them. A per-item validator may read squad-wide inputs (the
  registered-slug set, every item's incoming edges) and still produces a verdict per item.
- **Squad-global validators** run once per `sq check`, because their subject is the squad as a
  whole (`index_reconciled`, `backend_reconciled`, …). No category turns them on or off. They come
  in two tiers: always on, the defects in every squad, held in code; and selectable, effective only
  when a squad names a member under `[squad].validators` (ADR-982). Neither tier runs at the
  create/update gate.

### How the two axes compose

A category supplies a **default validator bundle**; a type's own `validators` list *extends* it.
Category behaviour is implemented as validator bundles, not as a parallel mechanism. Validators
**AND-compose**: an item passes only if every validator in its effective set passes.

Every type runs a **common core** of cross-cutting item hygiene (`COMMON_CORE`:
`item_status_valid`, `dangling_ref`, `ref_kind_valid`, `agent_registered`, `parent_acyclic`,
`attribute_valid`). On top of it (`CATEGORY_BUNDLES`):

- **`records`** add `no_parent` and `supersedes_incoming` (the latter effective only for a type
  declaring a supersession ref rule, as `decision` and `contract` do). A record is refused a parent
  at create/update and `sq check` reports any parented record.
- **`work`** add the parent validator and the sub-entity validators (`subentity_status_valid`,
  `subentity_container_marker`, `subentity_body_written`, `subentity_deferral_resolved`,
  `subtask_story_mapping`), each a no-op for a type that hosts no matching kind.
- **`roster`** add only `pronouns_valid`: no parent or sub-entity rules.

Everything else in the catalog is opt-in, selected per type (for example `no_status_banner` and
`subentity_title_max:<n>`, which this repository selects in its own override).

#### Empty-`parents` semantics, and epic as the work root

- `parent_in:<types>` requires the parent to be one of a **non-empty** allowlist; a type with a
  non-empty `parents` runs it (`feature` → `epic`, `task` → `feature`).
- A type with **empty** `parents` and no `no_parent` accepts any parent or none (`bug`, `review`).
- `no_parent` is how a type declares it takes no parent. Records get it from their bundle; `epic`
  selects it explicitly, so the work root is enforced.
- An empty `parent_in` allowlist is never written: it fails load validation, pointing the author at
  `no_parent`.

#### The bundle is a floor: extend-only

A type's effective set is common core + category bundle + its own additions, all from the one
catalog. The type-level list is **extend-only**: a type may add to its bundle but never subtract
from it. An adopter who wants a records-like type without `no_parent` reassigns its category
instead. This keeps a category's behaviour equal to the validators it turns on.

## Invariant: fail-closed validation across two planes

**Plane 1 — spec validity, at load, hard-stop.** Every spec-level rule here is checked when the
spec loads, and an invalid spec raises `SquadsError` (exit 1), with `sq workflow lint` as the
diagnostic: category-catalog membership; the roster key lock; validator-catalog membership and
selection grammar; a well-formed parent validator; and referential safety of a `selected`
deselection (a dropped status or lifecycle still referenced by a selected type, or a roster key).

**Plane 2 — item conformance, at the gate and in `sq check`.** Whether an individual item obeys a
well-formed spec is enforced at create/update and reported by `sq check`, the two call sites of the
one engine. A pre-existing violation surfaces for repair rather than preventing sq from starting.
The one load-time exception is a live item whose type or status the spec dropped, which can no
longer be represented at all.

The rule of thumb: *is the spec well-formed?* is Plane 1; *does this item obey a well-formed spec?*
is Plane 2.

## Consequences

- Each consumer asks a precise question, "roster or not" or "burn-down or not", instead of
  inheriting a lossy split.
- "Records take no parent" and "epic is the work root" are enforced through the same engine that
  powers `sq check`.
- Category reassignment among the non-roster categories is guarded by Plane 1 validation, not by
  policy.

## Adopter back-compat: spec-vocab renames

Renaming or removing a spec-vocabulary key (the first instance being `is_meta` → `category` on
`ItemSpec`) is a **spec-format change, not a frontmatter-schema change**: the key is read from the
workflow spec at load and never written to item frontmatter, the index or `.squads.toml`. It carries
no `SCHEMA_VERSION` bump and no data migration; spec-format provenance is tracked by the
`squads:override-base:<version>` stamp.

The cost is confined to a project override still writing the old key. The policy for any such
rename:

- **A one-release read-compat shim in the loader** translates the deprecated key before model
  validation, so `extra="forbid"` stays intact. For `is_meta`: `false` or absent resolves to the
  `category` default (`work`); `is_meta = true` on a non-roster type is refused with a message
  naming `category` and the roster key lock.
- **The deprecation is documented** in the CHANGELOG and upgrade notes of the release that
  introduces it.
- **The shim is dropped at 1.0**; past that, a deprecated key is an unknown key and fails closed.
<!-- sq:body:end -->

## Discussion

<!-- sq:discussion -->
- [2026-07-21T16:33:10Z] `op-pierre` Pierre Chat:
  - Roster is internal-only and locked: role/skill/operator are entirely off the customization surface — no add, no deactivate, no field-merge, no rename. This resolves the roster-extensibility open question (not just capped at three — locked) and moots meta_kind (nothing to rename), consistent with the defer.
  - Validation contract: every spec rule here (category-catalog membership, roster-locked, records-no-parent, validator-catalog membership, active-deselect referential safety) MUST be validated at spec load and hard-stop sq if the spec is invalid (fail-closed, Plane 1) — with sq workflow lint for the diagnostic. Item-level conformance stays on the create/update gate + sq check (Plane 2), so a pre-existing item violation surfaces for migration rather than bricking load.
- [2026-07-21T16:50:51Z] `op-pierre` Pierre Chat:
  - Resolve the category-reassignment open question: built-in types MAY be reassigned to a different category, but only among non-roster categories (work<->records). Roster membership is fixed and closed both directions — no type can be reassigned into roster, and roster types cannot leave (roster is locked). We do not block reassignment by policy; a reassignment producing an inconsistent spec (e.g. a type moved to records while still declaring a parent) fails Plane 1 load validation. So the guardrail is validation, not prohibition.
- [2026-07-21T20:53:25Z] `architect` Robert Architect:
  - Pre-acceptance gap-review revisions (2026-07-21). Closed the 3 blockers, 3 moderates, and the nit against the tree:
  - B1: scoped the 'byte-identical sq check' claim to the renamed seed checks, explicitly excluding the new category-default no_parent (records) and epic's no_parent; stated the EPIC-538 5-ADR parent→related migration lands with-or-before the records no_parent default so sq check stays clean.
  - B2: added item_status_valid to the seed catalog (the previously-unnamed _check_items 'status invalid for type' inline check) so the catalog is genuinely 1:1 with today's checks.
  - B3: defined a second validator class — squad-global validators (index_reconciled, backend_reconciled) that run once per sq check/gate, independent of the per-type bundle set; noted agent_registered/supersedes_incoming stay per-item though they read squad-global inputs.
  - B4: added a related ref to ADR-320 and reconciled contract ∈ records, refining ADR-320's pre-category 'non-meta work-item type' phrasing and EPIC-538's 'architecture category' (both flagged for a wording fix on their owners; not edited here).
  - B5: pinned empty-parents semantics — parent_in names a non-empty allowlist; empty parents + no no_parent keeps today's lenient any/none (bug/review unchanged); no_parent spells 'takes no parent'; epic gets an explicit no_parent to enforce its work-root constraint. Empty parent_in is ill-formed (Plane-1).
  - B6: enumerated all three category bundles completely (common core + records/work/roster additions) and assigned the cross-cutting checks (no_status_banner, dangling_ref, ref_kind_valid, item_status_valid, agent_registered) to the per-item common core — distinct from the squad-global class.
  - Nit: stated the type validators list is extend-only (category bundle = floor); no active-style per-validator deselect (contrast active's deselect for whole types/statuses); category reassignment is the lever, not deselection.
  - sq check clean; status left Proposed for the operator's accept decision.
- [2026-07-21T21:17:19Z] `op-pierre` Pierre Chat:
  - Accepted as revised, including epic's explicit no_parent (epic-as-root). Rationale confirmed: category and parent-rules are orthogonal axes — category 'work' gives epic its burn-down behavior, and root-ness is a per-type no_parent validator addition composed on top (empty parents stays 'any' for byte-identical bug/review; 'no parent' is spelled explicitly). Declared now, enforced when EPIC-540/538 build the validator engine; surfaces as a Plane-2 migration warning, not a load brick. Records no_parent + the 5-ADR parent→related migration land together so sq check stays clean.
- [2026-07-22T09:26:20Z] `architect` Robert Architect:
  - [amendment — 2026-07-22] Added a body section "Adopter back-compat: spec-vocab renames" per op-pierre's authorization (relayed via the coordinator). Additive policy consistent with the accepted decision — status unchanged. Captures: a spec-vocab key rename (first instance is_meta→category) is a spec-format change, not a frontmatter-schema bump (no SCHEMA_VERSION change, no data migration); a deprecated key gets a one-release read-compat shim in the loader (is_meta false/absent → category default work; true on a non-roster type → clean SquadsError); the deprecation is documented in the CHANGELOG/upgrade notes; the shim is dropped at 1.0. Stated at the standing-policy altitude for spec-vocab renames generally, with is_meta→category as the first instance.
- [2026-07-31T13:54:28Z] `architect` Robert Architect:
  - [amendment — 2026-07-31] Narrowed the type-axis floor from 'the roster category is locked' to 'the roster type keys and their category are locked', which is the other end of the override ADR-696 §4 already declared. Edited in place: the roster category bullet, the floor section (now naming key identity + category membership, with a second paragraph stating that lifecycle/prefix/folder/labels/order are ordinary validated customisation), the Plane-1 rule list, the meta_kind consequence, and the back-compat shim's 'never adopter-declarable' wording (now scoped to membership). Also corrected the stale META_* constant names to ROSTER_*.
  - Why narrowing is right, not merely later: a lock is only justified where the engine cannot verify. The engine binds the roster by type KEY (ROSTER_ROLE/ROSTER_SKILL/ROSTER_OPERATOR in _workflow/_models.py) and by the fixed category — the reserved-vocab floor at _models.py checks exactly those two and nothing else. No roster prefix or folder literal exists in src/ outside _migrations/ (correctly frozen at their pinned schema versions). A lock over a field no call site reads is a prohibition standing in for a check. The lifecycle safety the blanket lock bought is bought instead by ADR-696 §3's floor, already implemented in _check_roster_lifecycle_floor.
  - meta_kind stays moot for an unchanged reason: a key rename is still never permitted, so there is still nothing for a name-independent identity marker to follow. Axis B, the taxonomy, the work<->records reassignment ruling and the spec-vocab back-compat policy are untouched.
  - Status stays Accepted and no supersedes edge was added: only one clause is overridden, and this decision remains the sole authority on the category taxonomy and the validator model. Retiring it wholesale for a clause-level reversal would falsely retire everything else it says. Recorded instead as a related edge to ADR-696 plus dated notes at both ends. @manager this is the precedent I would apply to the 54-decision audit — supersedes + Superseded for whole-decision replacement; both-Accepted + reciprocal in-place narrowing for a clause-level reversal. 'Nothing is marked Superseded' is only a defect where a decision has actually been replaced whole.
- [2026-07-31T14:05:18Z] `architect` Robert Architect:
  - [amendment — 2026-07-31, second] Added a paragraph to the amendment note making the narrowing's legitimacy legible on this decision itself, not only in a handoff: the lock arrived as an operator directive (on this discussion, dated) in the same breath as the ruling that the guardrail is validation not prohibition; what it was answering was the roster-extensibility question, and what it was protecting was the roster lifecycle at a point when the engine bound roster semantics to three literal status names and had no way to check a project's own lifecycle instead. The status-role object, the live flag and the lifecycle floor that make such a check expressible were all decided afterwards on ADR-696, on the same operator's direction. So membership stays closed exactly as directed and the field axis moves from prohibition to validation — the direction that operator set. A future reader can now see why this was not a reversal of a call anyone asked to keep, and re-litigate it only on new evidence.
- [2026-08-03T08:52:23Z] `architect` Robert Architect:
  - Judgement asked for on the `contract` clauses, which have no live referent since the type left the release: they STAND as forward design, and are deliberately not scoped to the types return. Recorded in the body as a note rather than a narrowing, because nothing here is wrong.
  - The reasoning, stated rather than assumed. What these clauses rule on is the taxonomy — which category the type belongs to and what that category obliges — and a taxonomy ruling is about the shape of the vocabulary, not about a shipped artifact. It costs nothing while the type is absent, it is exactly what an implementer needs the day it returns, and the operator decided it on the merits, not as a consequence of the types schedule.
  - Conditioning them on the types return would be worse in a specific way: it creates a clause whose activation nobody owns, and it re-opens a settled taxonomy question at the moment someone is busy building the type. The rule I am applying is that a decision is retired when it is wrong, not when its subject is absent.
  - What was genuinely owed is done: the two present-tense readings are marked forward, so a conformance sweep does not hunt for a referent in `src/` and report a gap. The `records` membership list now reads "and `contract` (PRD) once it exists". Applied ADR-320s rewording at that end too and added the reciprocal edge, so the pair is linked. Also flagged for the sweep, not as an amendment: the squad-global validator catalog holds four rather than the two named here — this decision says "seed members", so nothing is owed.
- [2026-10-25T21:34:33Z] `architect` Robert Architect:
  - 2026-10-25 audit: partly stale, body rewritten in the present tense; Axis A, Axis B, the composition rules and the two planes are unchanged. The seed catalog and bundles were stale: the common core is COMMON_CORE (no no_status_banner; adds parent_acyclic and attribute_valid), work adds subentity_container_marker and subentity_deferral_resolved but not subentity_title_max, roster runs pronouns_valid, and no_status_banner and subentity_title_max are opt-in per ADR-864. Replaced the seed list with the catalog modules and ADR-864/ADR-982 as owners of placement, levels and squad-global selection. Folded the 2026-07-31 floor narrowing and the 2026-10-09 ADR-982 note; contract and milestone exist, so the forward-design note is gone. Removed the 5-parented-ADRs migration sequencing.
<!-- sq:discussion:end -->
