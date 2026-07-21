---
id: EPIC-538
sequence_id: 538
type: epic
title: Complete spec-driven customization
status: Draft
author: product-owner
priority: high
refs:
- FEAT-533
- ADR-534
- EPIC-540
description: Make the work-item vocabulary fully overridable (drop/rename/re-prefix)
  + extend overrides to the playbook, via one shared merge engine (deep-merge · active
  · splat-refs).
created_at: '2026-07-21T15:11:25Z'
updated_at: '2026-07-21T15:56:24Z'
---
<!-- sq:body -->
## Outcome

Deliver the full spec-driven customization promise: an adopter's project spec can
fully reshape the work-item vocabulary — **drop, rename, and re-prefix** the built-in
types — and layer house-specific guidance onto the **playbook**, with only the three
meta-types (`role`/`skill`/`operator`) reserved. Default behaviour (no override) stays
byte-identical to today.

## Why now

The generic rewrite freed the vocabulary in the *models* but stopped short at the
*override* layer. Two concrete gaps make customization second-class:

- **Workflow override is additive-only.** It refuses to redefine a built-in, so `task`
  can't be renamed, `FEAT` can't be re-prefixed, `guide` can't be dropped. `_models.py`
  already treats renamed/dropped/re-prefixed types as first-class — the freedom exists
  but has no expression path through `.overrides/workflow.toml`.
- **The playbook has no override at all.** `_interactions/playbook.toml` is the one
  bundled spec left out of the `.overrides/` subsystem (workflow, roles, templates all
  have one). Custom types get only a thin auto-generated skill, never rich role guidance.

Same root theme: the promise is real in the models, incomplete at the override layer.

## Foundation: type categories (replaces the `is_meta` flag)

Replace the boolean `is_meta` with a `category` axis on each item-type spec. The category
catalog is **hard-coded in squads** — a closed set with fixed, code-defined behaviour.
Adopters cannot create, rename, or redefine a category, and it is **not** part of the
override surface (consistent with the project rule: vocabulary lives in the spec, behaviour
lives in code — a category is behaviour, not vocabulary). A type declares which category it
belongs to; a custom type picks one of the fixed categories to inherit its behaviour. The
hard-coded categories:

- **roster** — `role`, `skill`, `operator`. Registry entities: can never be deactivated,
  slug identity, backend pointer files, own group in the UI trees. (Today's
  `is_meta = true` set.)
- **work** — `epic`, `feature`, `task`, `bug`, `review`. Burn-down items: assigned,
  lifecycle to Done, parent per type, counted in blocked/mine/velocity, work group in the
  trees.
- **records** — `decision` (ADR), `contract` (PRD), `guide`. Durable references: own
  lifecycles (Proposed→Superseded, Published→Deprecated), never "Done", not assigned or
  burned down, and they **take no parent** — records relate to work via refs, not
  hierarchy. Own group in the UI trees.

Why a category, not the boolean: `is_meta` conflates two different meanings of "not
roster" — *creatable/trackable* (work **and** records) vs *burn-down work only*. Consumers
(~15 sites: TUI tree grouping, `sq create`, retype/rename, roster service, playbook
coverage, backend) overload `not is_meta` for both. `category` disambiguates them, so the
consumer audit reclassifies each site precisely instead of by a lossy flag.

Scope notes:

- `category` replaces `is_meta` on this one axis and carries per-category defaults;
  orthogonal capabilities (`parent_required`, sub-entity kinds) stay their own flags.
- Name the field `category`, not `type` — which collides with the item type's own name.
- The axis does **not** by itself enable renaming a roster type: `category` says "this is
  roster", not "this is the operator one" — role/skill/operator are still dispatched by
  literal name (`META_OPERATOR == "operator"`, ~15 sites). Full roster rename needs a
  separate name-independent `meta_kind` marker + consumer de-naming (open, below).

Settled: `guide` is a **record**; `review` is **work**.

Open questions for the ADR:

- Can adopters add new roster-category types, or is roster capped to the three?
- Roster override granularity: non-identity field-merge (lifecycle/alias/label/folder)
  vs full rename/re-prefix (the latter needs `meta_kind` de-naming).
- May an override reassign a built-in type's category, or are built-in assignments fixed?

## The design (settled)

A single shared override engine, reused by the workflow, playbook, and roles loaders:

- **Deep recursive merge at leaf granularity.** An override supplies only the fields it
  changes; everything else inherits from the bundled built-in. Replaces the additive-only
  "may not redefine built-in" policy. Plain arrays merge as leaves (replace-wholesale)
  unless a splat-ref is used; tables recurse per-key.
- **Deselect via active.** An `active` = `list[str]` at each section's top level
  (`items`/`statuses`/`lifecycles`/`collections`/`subentity_kinds`) drops built-ins.
  Replace-wholesale semantics (the point is to shrink); meta-types can never be dropped
  (`is_meta` floor).
- **Splat-refs.** A safe, eval-free path-reference splice — written `$(*path)` — to
  append to a bundled list without restating it: `do = ["$(*self)", "…"]`. Resolves against the
  **bundled base only** (no cycles, order-independent). `$(self)`/`$(*self)` targets the
  key being written — the only clean idiom inside the playbook's `[[…roles]]`
  array-of-tables; dotted paths address keyed tables. Compose-only (no element removal —
  that's `active`'s job); fail-closed on a dangling path, type mismatch, or unparsed
  token; `$$(` escapes a literal.

## Outcomes grouped under this epic

- A single shared merge/override engine: deep-merge · `active` deselect · `$(*…)` splat-refs.
- Workflow built-ins fully overridable (drop/rename/re-prefix), guarded by the existing
  referential-integrity checks and the live-index guard (`validate_against_index_fail_closed`).
- Playbook wired as the 4th override kind (`.overrides/playbook.toml`) into `sq override`,
  drift-check, and base-stamps.
- The three bundled TOMLs consolidated under `squads/_specs/` and name-normalized
  (`workflow.toml` / `roles.toml` / `playbook.toml`, dropping the `default_` prefix),
  mirroring the `.overrides/` layout.
- A consumer audit so drops/renames/re-prefixes flow through generated `sq-<type>` skills,
  `sq check` invariants (parent/sub-entity rules), and prefix/folder maps — closing the
  "freed the names but left the consumers hardcoded" trap.
- **Records take no parent, actually enforced** — the `records`-category default is
  validated at create/update *and* in `sq check`. This closes a live gap: `parents = []`
  for `decision`/`guide` is declared today but silently unenforced (5 ADRs currently hold
  parents while `sq check` reports clean).
- **A `records` group in both UI clients** — enabled by exposing each type's `category` in
  the `sq workflow types --json` catalog both clients already fetch, so neither re-derives
  the taxonomy (single-sourced). Concrete work differs per client: the **TUI** switches its
  one tree's grouping from the `is_meta` boolean to `category` (a third root alongside
  work/roster); the **extension** gives records their own categorized view, mirroring how
  roster already has its own provider (`domain/metaView.ts`) separate from the work tree.
- **Migrate the 5 parented ADRs** — drop each parent, re-express as a `related` ref
  (ADR-516/527→EPIC-28, ADR-155/158→EPIC-121, ADR-129→FEAT-17).

## Invariants (hard constraints — non-negotiable)

- **No dropped item may break sq.** Deselecting a built-in either succeeds with the tool
  fully functional, or is **refused cleanly** (`SquadsError`, never a traceback). Two halves:
  - *Refuse unsafe drops:* a type with live items (existing `validate_against_index_fail_closed`),
    or a status/lifecycle still referenced by an active type (referential-integrity check).
  - *Absorb safe drops:* every consumer — generated `sq-<type>` skills, `sq check`
    parent/sub-entity rules, prefix/folder maps, backend pointer files — iterates the
    **active/merged** spec, never a hardcoded built-in name. A dropped type just doesn't
    appear; nothing orphans or crashes.
- **Roster types can never be deactivated.** sq structurally requires a role/skill/operator
  type to exist, so the `active` floor forbids dropping any `category = roster` type
  (`SquadsError`). This is the one type-axis floor; every non-roster type is droppable.
  Whether roster types may additionally be *renamed/re-prefixed* (vs only non-identity
  field-merge) is an open ADR question tied to de-naming roster identity — deliberately
  **not** "frozen absolutely", which an earlier draft over-asserted.

## Acceptance (epic-level)

- A project spec that **drops and renames** `feature`/`task` loads and runs clean; only
  `role`/`skill`/`operator` refuse.
- A built-in can be **re-prefixed** by overriding a single field, without restating the
  rest of its definition.
- **Dropping any droppable built-in** leaves sq fully functional (skills, `sq check`,
  rendering, backends) — or is refused with a clean error naming what still references it.
  No consumer traceback under any drop.
- **Deactivating any `roster`-category type fails closed** (role/skill/operator can't be
  dropped). Rename/re-prefix of roster types is gated on the ADR's `meta_kind` decision.
- **Records take no parent, enforced.** Creating or updating a `records`-category item
  (decision/PRD/guide) with a parent fails closed, and `sq check` flags any that exist —
  unlike today, where `parents = []` on decisions/guides is silently unenforced.
- **The category catalog is closed.** A type may declare only a hard-coded category; an
  override that invents a category, or attempts to redefine one, fails closed. There is no
  override path that creates or modifies a category.
- Appending one playbook bullet takes **one line** (`$(*self)` + the addition), not a
  restated list — and bundled improvements still flow through.
- With no override present, behaviour is **byte-identical** to today.

## Dependencies / relationships

- Rides the statelessness seam (per-squad resolution, no new import-time singletons) —
  the current `_PLAYBOOK_SPEC`/`_BUNDLED_SPEC` module-level singletons are exactly what
  that work removes.
- Extends the existing `.overrides/` subsystem (workflow/roles/templates).
- **Coordinates with ADR-320 / FEAT-321 (the contract/PRD type):** the PRD is born into the
  `architecture` category, so the category taxonomy must be settled alongside that type.
- **Foundational ADR (architect) required first.** The `category` axis + per-category
  behavioural contract is an architecture decision that everything else here keys off
  (the merge, the `active` floor, the consumer audit) — it should be pinned in an ADR
  before the features are built.
<!-- sq:body:end -->

## Discussion

<!-- sq:discussion -->
- [2026-07-21T15:17:30Z] Pierre Chat:
  - Two hard constraints on this epic: (1) dropping any droppable built-in must never break sq — clean refusal or full functionality, no consumer traceback; (2) meta-types (role/skill/operator) are frozen absolutely — no deactivate/rename/re-prefix/field-merge, any override touching them is rejected.
- [2026-07-21T15:40:33Z] Pierre Chat:
  - Direction: replace the is_meta boolean with a 'category' axis (roster / work / architecture) on each item-type spec. ADR/PRD become an 'architecture' category (records, not burn-down work). Deactivation floor = roster category; roster rename gated on a separate meta_kind de-naming. Robert to pin the taxonomy + per-category contract in a foundational ADR before features are cut.
- [2026-07-21T15:43:56Z] Pierre Chat:
  - Constraint: the category catalog is hard-coded in squads — closed set, fixed semantics, not part of the override surface. Adopters cannot create/rename/redefine a category; a custom type only picks one of the fixed categories to inherit its behaviour.
- [2026-07-21T15:48:49Z] Pierre Chat:
  - Category naming + rules: call the third category 'records' (not architecture); guide is a record, review is work. Records take no parent — records relate via refs, not hierarchy — and this must be enforced at create/update AND in sq check (today parents=[] on decision/guide is unenforced: 5 ADRs hold parents while sq check is clean). Both the TUI and VS Code extension trees need a Records group; migrate the 5 parented ADRs to related refs.
<!-- sq:discussion:end -->
