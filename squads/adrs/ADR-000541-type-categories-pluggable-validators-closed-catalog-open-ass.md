---
id: ADR-541
sequence_id: 541
type: decision
title: 'Type categories + pluggable validators: closed catalog, open assignment'
status: Proposed
author: architect
refs:
- EPIC-538
- EPIC-540
created_at: '2026-07-21T16:26:15Z'
updated_at: '2026-07-21T18:18:41Z'
---
<!-- sq:body -->
## Context

The generic-vocabulary rewrite freed the *models* — every work-item type can be dropped, renamed,
or re-prefixed — but two structural questions were left open and are now blocking two sibling epics
(EPIC-538 spec-driven customization, EPIC-540 pluggable validators):

1. The single boolean `is_meta` conflates two distinct meanings of "not roster": *creatable and
   trackable* (work items **and** durable records) versus *burn-down work only*. ~15 consumer sites
   (TUI/extension tree grouping, `sq create`, retype/rename, roster service, playbook coverage,
   backend pointer generation) overload `not is_meta` for both meanings, so behaviour that should
   differ between records and work is smeared together — e.g. `parents = []` is declared on
   `decision`/`guide` today but silently unenforced, and 5 ADRs currently hold a parent while
   `sq check` reports clean.

2. The constraint set that `sq check` and create/update gating enforce lives as ~10 hardcoded
   `_check_*` methods in `_services/_maintenance.py`. A type cannot opt in or out of a rule, an
   adopter cannot compose a rule set for a custom type, and parent rules are only half-declarative
   (structured `parents`/`parent_required` fields read by hardcoded logic).

Both epics key off the same two design axes and the way they compose. This decision pins those axes
so the features can be cut against a stable foundation. It records design intent; it does not
implement anything.

## Decision

### Axis A — the type `category` (replaces the `is_meta` boolean)

Replace `ItemSpec.is_meta: bool` with a `category` field naming one of a **hard-coded, closed
catalog** of three categories. The category catalog is defined in code, carries fixed behaviour, and
is **not part of the override surface**: an adopter cannot create, rename, or redefine a category.
This is the project's standing boundary — vocabulary lives in the spec, behaviour lives in code, and
a category *is* behaviour. A type *declares* which category it belongs to; a custom type picks one of
the three fixed categories to inherit that category's behaviour.

The three categories and their behavioural contracts:

- `roster` — `role`, `skill`, `operator`. Registry entities: slug identity (not sequence-id
  identity), backend pointer files written on sync, their own group in both UI trees. The roster
  category is **internal-only and locked** — entirely off the customization/override surface: no
  add, no deactivate, no field-merge, no rename (see the floor below). This is today's
  `is_meta = true` set.
- `work` — `epic`, `feature`, `task`, `bug`, `review`. Burn-down items: assigned, driven to a
  terminal Done-like status, a parent constraint per type, counted in `blocked`/`mine`/velocity,
  the work group in the trees.
- `records` — `decision` (ADR), `contract` (PRD), `guide`. Durable references: their own lifecycles
  (Proposed→…→Superseded, Published→Deprecated), never a "Done" burn-down state, not assigned and
  not burned down, their own group in the trees, and they **take no parent** — a record relates to
  work through refs, never through hierarchy.

Settled assignments (operator directive): `guide` is a `records` type; `review` is a `work` type.

Rationale for a category axis over the boolean: `category` disambiguates the two meanings the boolean
conflated, so the consumer audit can reclassify each of the ~15 sites precisely (does this site care
about *roster vs not*, or *burn-down vs not*?) instead of inheriting a lossy split. Orthogonal
capability flags (`parent_required`, `subentity_kind`, `fields`) stay their own fields; `category`
replaces only the roster/work/records axis and supplies per-category behavioural defaults. The field
is named `category` deliberately — `type` would collide with the item type's own name.

#### The type-axis floor: roster is locked

The roster category is off the override surface entirely. sq structurally requires a role, a skill,
and an operator type to exist and binds them by literal name, so an override may not add a roster
type, deactivate one, field-merge one, or rename/re-prefix one — any override touching a
`category = roster` type is refused (clean `SquadsError`, never a traceback). Every non-roster type
is droppable/renamable/re-prefixable as ordinary spec vocabulary. This is the one type-axis floor;
the earlier "meta-types frozen absolutely" framing lands here exactly.

#### `meta_kind` is moot

Because roster is locked, the roster-rename problem no longer exists to solve. The engine binds the
three roster types by literal name (`META_OPERATOR == "operator"`, `META_ROLE`, `META_SKILL`,
dispatched across ~15 sites — the roster service, backends that write role/skill pointer files, the
agent lifecycle, `sq create` self-author bypass), and since no rename is ever permitted, those
literal-name bindings are correct as-is. A separate name-independent identity marker (a `meta_kind`)
would only be needed to *follow* a rename; with rename off the table there is nothing for it to
track. `meta_kind` is therefore not introduced — consistent with the earlier defer, now closed as
moot rather than deferred.

#### Category reassignment of a built-in (operator-resolved)

An override **may** reassign a built-in type to a different category — but only among the
non-roster categories (`work` ↔ `records`): an adopter may move `review` from `work` to `records`,
or `guide` from `records` to `work`. Roster membership is fixed and closed in both directions — no
type can be reassigned *into* `roster`, and roster types cannot leave it (roster is locked, per the
floor above). Reassignment is not blocked by policy; the guardrail is validation, not prohibition. A
reassignment that yields an internally inconsistent spec — e.g. a type moved to `records` while it
still declares a parent, which the records contract forbids — fails Plane 1 load validation and
hard-stops. Merely-unusual-but-valid reassignments are the adopter's call.
### Axis B — the validator model

`sq check` and create/update gating become a **declarative, pluggable validator framework** with the
same closed-catalog / open-assignment boundary as categories:

- **Closed catalog, open assignment.** Validator *logic* is hard-coded in squads. There is no
  adopter-supplied validator code and no `eval` — the same no-eval line drawn for splat-refs in
  EPIC-538 applies here. What is spec-declared is *which* validators a type runs, plus their params.
  A `validators` entry naming a validator not in the closed catalog fails closed.
- **Rule data stays structured; validators read it.** The rule *data* stays in structured spec
  fields (`parents`, `parent_required`, a title-max, the ref rules). A validator is the *check* that
  reads those fields — it does not re-encode a rule as both a typed field and a string param. One
  home per rule, no drift. Params on a validator carry only what is not already a structured field.
- **One engine, two call sites.** A single validator engine runs the catalog. `sq check` runs it in
  *report* mode (collect every issue, warn/error levels preserved); create/update runs it in *abort*
  mode (fail-closed on the first violation). This mirrors the existing workflow-lint report-vs-abort
  split — the rule logic is written once and never duplicated between the gate and the report.

#### Seed catalog

The initial named validators are exactly today's hardcoded checks, lifted verbatim (no behaviour
change for the bundled spec):

- `parent_required` / `parent_in:<types>` / `no_parent` — parent eligibility (from `_check_items`
  parent-allowed + dangling-parent logic and `parents`/`parent_required`).
- `subtask_story_mapping` — a subtask maps to one of its parent's stories (`_check_subtask_stories`).
- `subentity_status_valid` — a sub-entity's status is reachable in its kind's lifecycle
  (`_check_subentity_status`).
- `subentity_body_written` — no unwritten placeholder sub-entity bodies
  (`_check_unwritten_subentity_bodies`).
- `subentity_title_max:<n>` — no over-long finding/story titles (`_check_subentity_title_lengths`).
- `no_status_banner` — no lifecycle/status prose in item bodies (`_check_status_banners`).
- `dangling_ref` / `ref_kind_valid` — refs resolve and carry a known kind (`_check_items` ref loop).
- `agent_registered` — author/assignee resolve to a registered roster slug (`_check_items`).
- `supersedes_incoming` — a Superseded record has an incoming `supersedes` edge (`_check_decisions`).
- `backend_reconciled` — backend pointer files match the roster (`_check_backends`).
- `index_reconciled` — index and on-disk files agree (`_check_reconciliation`).

Naming these does not change what they check; it makes the set data-driven and per-type composable.

### How the two axes compose

A category supplies a **default validator bundle**; a type's own `validators` list *extends* that
bundle. Category behavioural defaults are **implemented as validator bundles, not a parallel
mechanism** — there is one way a rule attaches to a type. Concretely:

- `records` default bundle includes `no_parent` — so `decision`/`contract`/`guide` reject a parent
  at create/update *and* `sq check` flags any existing parented record. This closes the live gap
  (5 parented ADRs pass `sq check` clean today) and is EPIC-540's first customer: the
  "records take no parent" behaviour promised by EPIC-538 is *built as* the `no_parent` validator,
  not as a second hardcoded check.
- `work` default bundle includes `parent_in:<types>` (reading each type's structured `parents`
  field) and the sub-entity/status validators.
- `roster` types run the minimal registry validators and none of the work/record parent rules.

A type's effective validator set is therefore: `category default bundle + its own validators
additions`, all drawn from the one closed catalog, all sharing the one engine across both call sites.
This keeps the two axes from drifting apart — the category's *behaviour* is literally the validators
it turns on.

## Invariant: fail-closed validation across two planes

Every rule in this decision is enforced fail-closed, but on one of two distinct planes. The
distinction is deliberate: spec validity is a load-time contract, item conformance is not.

**Plane 1 — spec validity: validated at load, hard-stop.** Every *spec-level* rule introduced here
is validated when the spec loads, and an invalid spec raises `SquadsError` → exit 1 with
`sq workflow lint` as the diagnostic. These rules are:

- category-catalog membership — a type's `category` names one of the three hard-coded categories;
- roster-locked — no override adds, deactivates, field-merges, or renames a `roster` type;
- records-no-parent as a category default — the `records` bundle attaches `no_parent`;
- validator-catalog membership — every name in a type's `validators` list is a catalog validator;
- `active`-deselect referential safety — a deselected status/lifecycle is not still referenced by an
  active type, and the roster floor is not violated.

This is not new machinery: it is where `load_workflow_spec` (the `WorkflowSpec._validate`
fail-closed pass) and `validate_against_index_fail_closed` already live. The point of recording it is
that the *new* rules join Plane 1 — they are load-time spec-validity checks, not runtime surprises
discovered mid-command.

**Plane 2 — item conformance: create/update gate + `sq check` report.** Whether an individual
*item* obeys the rules (parent eligibility, title length, written sub-entity bodies, no status
banner) is enforced fail-closed at create/update and reported by `sq check` — the two call sites of
the one validator engine. This is deliberately **not** a load-time brick: a pre-existing violation
(e.g. the 5 parented ADRs that predate records-no-parent enforcement) must surface for migration, not
prevent sq from starting. The single load-time exception is the structural case
`validate_against_index_fail_closed` already covers — a live item whose type or status the spec
dropped — because there the item can no longer be represented at all.

The rule of thumb: *is the spec itself well-formed?* is Plane 1 (load, hard-stop); *does this item
obey a well-formed spec?* is Plane 2 (gate + report).

## Consequences

- The consumer audit for `is_meta` → `category` becomes a precise reclassification, not a mechanical
  rename: each of the ~15 sites is re-pointed at either "roster vs not" or "burn-down vs not".
- `records`-take-no-parent stops being aspirational and gets enforced through the same engine that
  powers `sq check`, with a migration for the 5 parented ADRs to `related` refs (tracked on
  EPIC-538, not here).
- Roster is locked off the override surface entirely, so `meta_kind` is moot rather than deferred —
  no rename means nothing for a name-independent identity marker to track.
- The validator framework is additive over today's behaviour: with the bundled spec and no override,
  `sq check` reports byte-identical issues, because the seed catalog *is* today's check set renamed.
- The new spec-level rules join the existing load-time fail-closed pass (Plane 1); item conformance
  stays on the create/update gate and `sq check` report (Plane 2), so pre-existing violations surface
  for migration instead of bricking load.
- Category reassignment of a built-in is allowed among the non-roster categories (`work` ↔
  `records`); roster membership is fixed both directions. It is guarded by Plane 1 validation — an
  inconsistent reassignment hard-stops — rather than by policy, so no operator decisions remain open.
<!-- sq:body:end -->

## Discussion

<!-- sq:discussion -->
- [2026-07-21T16:33:10Z] Pierre Chat:
  - Roster is internal-only and locked: role/skill/operator are entirely off the customization surface — no add, no deactivate, no field-merge, no rename. This resolves the roster-extensibility open question (not just capped at three — locked) and moots meta_kind (nothing to rename), consistent with the defer.
  - Validation contract: every spec rule here (category-catalog membership, roster-locked, records-no-parent, validator-catalog membership, active-deselect referential safety) MUST be validated at spec load and hard-stop sq if the spec is invalid (fail-closed, Plane 1) — with sq workflow lint for the diagnostic. Item-level conformance stays on the create/update gate + sq check (Plane 2), so a pre-existing item violation surfaces for migration rather than bricking load.
- [2026-07-21T16:50:51Z] Pierre Chat:
  - Resolve the category-reassignment open question: built-in types MAY be reassigned to a different category, but only among non-roster categories (work<->records). Roster membership is fixed and closed both directions — no type can be reassigned into roster, and roster types cannot leave (roster is locked). We do not block reassignment by policy; a reassignment producing an inconsistent spec (e.g. a type moved to records while still declaring a parent) fails Plane 1 load validation. So the guardrail is validation, not prohibition.
<!-- sq:discussion:end -->
